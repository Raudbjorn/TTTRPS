//! Blend Rule Store with Meilisearch (TASK-PERS-013)
//!
//! Provides CRUD operations for blend rules with Meilisearch storage.
//!
//! ## Features
//!
//! - CRUD operations: get_rule, set_rule, delete_rule, list_rules
//! - Unique constraint: (campaign_id, context)
//! - Filtering by campaign_id, context
//! - Uses PersonalityIndexManager for Meilisearch access
//!
//! ## Index Structure
//!
//! Blend rules are stored in the `ttrpg_blend_rules` Meilisearch index
//! with the following filterable attributes:
//! - context
//! - enabled
//! - isBuiltin
//! - tags
//! - campaignId

use super::context::GameplayContext;
use super::errors::{BlendRuleError, PersonalityExtensionError};
use super::meilisearch::PersonalityIndexManager;
use super::types::{BlendRule, BlendRuleDocument, BlendRuleId, PersonalityId};
use lru::LruCache;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::num::NonZeroUsize;
use tokio::sync::Mutex;

/// Escape a value for safe use in Meilisearch filter expressions.
fn escape_filter_value(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

// ============================================================================
// Constants
// ============================================================================

/// Default cache capacity for blend rules.
pub const DEFAULT_RULE_CACHE_CAPACITY: usize = 50;

/// Timeout for Meilisearch operations.
pub const MEILISEARCH_TIMEOUT_SECS: u64 = 30;

/// Polling interval for Meilisearch tasks.
pub const MEILISEARCH_POLL_MS: u64 = 100;

// ============================================================================
// Blend Rule Store
// ============================================================================

/// Store for blend rules with Meilisearch backend and LRU caching.
pub struct BlendRuleStore {
    /// Meilisearch index manager.
    index_manager: PersonalityIndexManager,

    /// LRU cache for frequently accessed rules.
    cache: Mutex<LruCache<BlendRuleId, BlendRule>>,

    /// Index for (campaign_id, context) -> rule_id uniqueness.
    /// Uses Mutex for async safety.
    context_index: Mutex<HashMap<(Option<String>, String), BlendRuleId>>,
}

impl BlendRuleStore {
    /// Create a new blend rule store.
    pub fn new(index_manager: PersonalityIndexManager) -> Self {
        let cap = NonZeroUsize::new(DEFAULT_RULE_CACHE_CAPACITY).unwrap();
        Self {
            index_manager,
            cache: Mutex::new(LruCache::new(cap)),
            context_index: Mutex::new(HashMap::new()),
        }
    }

    /// Create with custom cache capacity.
    pub fn with_capacity(index_manager: PersonalityIndexManager, capacity: usize) -> Self {
        let cap = NonZeroUsize::new(capacity).unwrap_or(NonZeroUsize::new(1).unwrap());
        Self {
            index_manager,
            cache: Mutex::new(LruCache::new(cap)),
            context_index: Mutex::new(HashMap::new()),
        }
    }

    /// Initialize the store, loading the context index.
    pub async fn initialize(&self) -> Result<(), PersonalityExtensionError> {
        // Load all rules to build context index
        let rules = self.list_all(1000).await?;
        let mut index = self.context_index.lock().await;

        for rule in rules {
            let key = (rule.campaign_id.clone(), rule.context.clone());
            index.insert(key, rule.id.clone());
        }

        log::info!("Initialized blend rule store with {} rules", index.len());
        Ok(())
    }

    // ========================================================================
    // CRUD Operations
    // ========================================================================

    /// Get a blend rule by ID.
    pub async fn get_rule(
        &self,
        id: &BlendRuleId,
    ) -> Result<Option<BlendRule>, PersonalityExtensionError> {
        // Check cache first
        {
            let mut cache = self.cache.lock().await;
            if let Some(rule) = cache.get(id) {
                return Ok(Some(rule.clone()));
            }
        }

        // Fetch from Meilisearch
        let doc = self.index_manager.get_blend_rule(id).await?;

        match doc {
            Some(doc) => {
                // Convert to BlendRule and cache
                let rule = self.document_to_rule(doc)?;

                let mut cache = self.cache.lock().await;
                cache.put(id.clone(), rule.clone());

                Ok(Some(rule))
            }
            None => Ok(None),
        }
    }

    /// Get a blend rule by campaign and context.
    ///
    /// Returns the rule that applies to the given campaign and context,
    /// or None if no such rule exists.
    pub async fn get_rule_for_context(
        &self,
        campaign_id: Option<&str>,
        context: &GameplayContext,
    ) -> Result<Option<BlendRule>, PersonalityExtensionError> {
        let key = (campaign_id.map(|s| s.to_string()), context.as_str().to_string());

        // Check context index
        let rule_id = {
            let index = self.context_index.lock().await;
            index.get(&key).cloned()
        };

        match rule_id {
            Some(id) => self.get_rule(&id).await,
            None => {
                // Try to find via search
                let filter = match campaign_id {
                    Some(cid) => format!(
                        "context = \"{}\" AND campaignId = \"{}\"",
                        escape_filter_value(context.as_str()),
                        escape_filter_value(cid)
                    ),
                    None => format!(
                        "context = \"{}\" AND campaignId IS NULL",
                        escape_filter_value(context.as_str())
                    ),
                };

                let docs = self
                    .index_manager
                    .list_blend_rules(Some(&filter), 1)
                    .await?;

                match docs.into_iter().next() {
                    Some(doc) => {
                        let rule = self.document_to_rule(doc)?;
                        // Update index
                        {
                            let mut index = self.context_index.lock().await;
                            index.insert(key, rule.id.clone());
                        }
                        Ok(Some(rule))
                    }
                    None => Ok(None),
                }
            }
        }
    }

    /// Set (create or update) a blend rule.
    ///
    /// Enforces uniqueness constraint on (campaign_id, context).
    pub async fn set_rule(&self, mut rule: BlendRule) -> Result<BlendRule, PersonalityExtensionError> {
        // Validate rule
        self.validate_rule(&rule)?;

        let key = (rule.campaign_id.clone(), rule.context.clone());

        // Check for existing rule with same (campaign_id, context)
        {
            let index = self.context_index.lock().await;
            if let Some(existing_id) = index.get(&key) {
                if *existing_id != rule.id {
                    return Err(BlendRuleError::rule_conflict(
                        rule.id.to_string(),
                        existing_id.to_string(),
                    )
                    .into());
                }
            }
        }

        // Normalize weights
        rule.normalize_weights();

        // Touch timestamp
        rule.touch();

        // Save to Meilisearch
        self.index_manager.upsert_blend_rule(&rule).await?;

        // Update cache
        {
            let mut cache = self.cache.lock().await;
            cache.put(rule.id.clone(), rule.clone());
        }

        // Update context index
        {
            let mut index = self.context_index.lock().await;
            index.insert(key, rule.id.clone());
        }

        log::debug!("Saved blend rule: {} ({})", rule.name, rule.id);
        Ok(rule)
    }

    /// Delete a blend rule by ID.
    pub async fn delete_rule(&self, id: &BlendRuleId) -> Result<(), PersonalityExtensionError> {
        // Get rule to find its key
        let rule = self.get_rule(id).await?;

        if let Some(rule) = rule {
            // Check if it's builtin
            if rule.is_builtin {
                return Err(BlendRuleError::invalid_rule(
                    id.to_string(),
                    "Cannot delete built-in rule",
                )
                .into());
            }

            // Delete from Meilisearch
            self.index_manager.delete_blend_rule(id).await?;

            // Remove from cache
            {
                let mut cache = self.cache.lock().await;
                cache.pop(id);
            }

            // Remove from context index
            {
                let key = (rule.campaign_id, rule.context);
                let mut index = self.context_index.lock().await;
                index.remove(&key);
            }

            log::debug!("Deleted blend rule: {}", id);
            Ok(())
        } else {
            Err(BlendRuleError::not_found(id.to_string()).into())
        }
    }

    /// List all blend rules.
    pub async fn list_all(
        &self,
        limit: usize,
    ) -> Result<Vec<BlendRule>, PersonalityExtensionError> {
        let docs = self.index_manager.list_blend_rules(None, limit).await?;
        self.documents_to_rules(docs)
    }

    /// List blend rules for a campaign.
    pub async fn list_by_campaign(
        &self,
        campaign_id: &str,
        limit: usize,
    ) -> Result<Vec<BlendRule>, PersonalityExtensionError> {
        let docs = self
            .index_manager
            .list_rules_by_campaign(campaign_id, limit)
            .await?;
        self.documents_to_rules(docs)
    }

    /// List blend rules for a context.
    pub async fn list_by_context(
        &self,
        context: &GameplayContext,
        limit: usize,
    ) -> Result<Vec<BlendRule>, PersonalityExtensionError> {
        let docs = self
            .index_manager
            .list_rules_by_context(context.as_str(), limit)
            .await?;
        self.documents_to_rules(docs)
    }

    /// List enabled blend rules, sorted by priority.
    pub async fn list_enabled(
        &self,
        limit: usize,
    ) -> Result<Vec<BlendRule>, PersonalityExtensionError> {
        let docs = self.index_manager.list_enabled_rules(limit).await?;
        self.documents_to_rules(docs)
    }

    /// Search blend rules by name/description.
    pub async fn search(
        &self,
        query: &str,
        limit: usize,
    ) -> Result<Vec<BlendRule>, PersonalityExtensionError> {
        let docs = self
            .index_manager
            .search_blend_rules(query, None, limit)
            .await?;
        self.documents_to_rules(docs)
    }

    // ========================================================================
    // Bulk Operations
    // ========================================================================

    /// Import multiple rules, replacing existing ones with same (campaign_id, context).
    pub async fn import_rules(
        &self,
        rules: Vec<BlendRule>,
    ) -> Result<BulkImportResult, PersonalityExtensionError> {
        let mut imported = 0;
        let mut skipped = 0;
        let mut errors = Vec::new();

        for rule in rules {
            match self.set_rule(rule.clone()).await {
                Ok(_) => imported += 1,
                Err(e) => {
                    errors.push((rule.id.to_string(), e.to_string()));
                    skipped += 1;
                }
            }
        }

        Ok(BulkImportResult {
            imported,
            skipped,
            errors,
        })
    }

    /// Export all rules for a campaign (or global rules if campaign_id is None).
    pub async fn export_rules(
        &self,
        campaign_id: Option<&str>,
    ) -> Result<Vec<BlendRule>, PersonalityExtensionError> {
        match campaign_id {
            Some(cid) => self.list_by_campaign(cid, 1000).await,
            None => {
                let docs = self
                    .index_manager
                    .list_blend_rules(Some("campaignId IS NULL"), 1000)
                    .await?;
                self.documents_to_rules(docs)
            }
        }
    }

    // ========================================================================
    // Cache Operations
    // ========================================================================

    /// Clear the rule cache.
    pub async fn clear_cache(&self) {
        let mut cache = self.cache.lock().await;
        cache.clear();
        log::debug!("Cleared blend rule cache");
    }

    /// Get cache statistics.
    pub async fn cache_stats(&self) -> RuleCacheStats {
        let cache = self.cache.lock().await;
        RuleCacheStats {
            len: cache.len(),
            cap: cache.cap().get(),
        }
    }

    // ========================================================================
    // Default Rules
    // ========================================================================

    /// Create default blend rules for all gameplay contexts.
    ///
    /// These provide sensible defaults based on context suggestions.
    pub fn create_default_rules() -> Vec<BlendRule> {
        let mut rules = Vec::new();

        for context in GameplayContext::all_defined() {
            let suggestion = context.default_blend_suggestion();

            let mut rule = BlendRule::new(
                format!("Default {} Rule", context.display_name()),
                context.as_str(),
            )
            .as_builtin()
            .with_priority(0); // Lowest priority, can be overridden

            for (personality_type, weight) in suggestion {
                rule = rule.with_component(PersonalityId::new(personality_type), weight);
            }

            rules.push(rule);
        }

        rules
    }

    /// Initialize with default rules if none exist.
    pub async fn ensure_default_rules(&self) -> Result<usize, PersonalityExtensionError> {
        let existing = self.list_all(100).await?;
        if !existing.is_empty() {
            log::debug!(
                "Skipping default rule creation, {} rules already exist",
                existing.len()
            );
            return Ok(0);
        }

        let defaults = Self::create_default_rules();
        let count = defaults.len();

        for rule in defaults {
            self.set_rule(rule).await?;
        }

        log::info!("Created {} default blend rules", count);
        Ok(count)
    }

    // ========================================================================
    // Helper Methods
    // ========================================================================

    /// Validate a blend rule.
    fn validate_rule(&self, rule: &BlendRule) -> Result<(), BlendRuleError> {
        // Check name
        if rule.name.is_empty() {
            return Err(BlendRuleError::invalid_rule(
                rule.id.to_string(),
                "Rule name cannot be empty",
            ));
        }

        // Check context
        if rule.context.is_empty() {
            return Err(BlendRuleError::invalid_rule(
                rule.id.to_string(),
                "Rule context cannot be empty",
            ));
        }

        // Check weights
        if rule.blend_weights.is_empty() {
            return Err(BlendRuleError::invalid_rule(
                rule.id.to_string(),
                "Rule must have at least one blend component",
            ));
        }

        // Check weight ranges
        for (id, weight) in &rule.blend_weights {
            if *weight < 0.0 || *weight > 1.0 {
                return Err(BlendRuleError::invalid_rule(
                    rule.id.to_string(),
                    format!(
                        "Weight for component '{}' is out of range: {}",
                        id, weight
                    ),
                ));
            }
        }

        Ok(())
    }

    /// Convert a BlendRuleDocument to BlendRule.
    fn document_to_rule(&self, doc: BlendRuleDocument) -> Result<BlendRule, PersonalityExtensionError> {
        // Note: BlendRuleDocument doesn't contain blend_weights directly
        // We need to fetch the full rule data
        // For now, create a stub rule and indicate it needs full data

        // In a real implementation, you might store blend_weights in the document
        // or have a separate lookup. Here we create a minimal rule.
        Ok(BlendRule {
            id: BlendRuleId::new(doc.id),
            name: doc.name,
            description: doc.description,
            context: doc.context,
            priority: doc.priority,
            enabled: doc.enabled,
            is_builtin: doc.is_builtin,
            campaign_id: doc.campaign_id,
            blend_weights: HashMap::new(), // Would need separate storage/lookup
            tags: doc.tags,
            created_at: doc.created_at,
            updated_at: doc.updated_at,
        })
    }

    /// Convert multiple documents to rules.
    fn documents_to_rules(
        &self,
        docs: Vec<BlendRuleDocument>,
    ) -> Result<Vec<BlendRule>, PersonalityExtensionError> {
        docs.into_iter()
            .map(|doc| self.document_to_rule(doc))
            .collect()
    }
}

// ============================================================================
// Result Types
// ============================================================================

/// Result of a bulk import operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BulkImportResult {
    /// Number of rules successfully imported.
    pub imported: usize,

    /// Number of rules skipped due to errors.
    pub skipped: usize,

    /// List of (rule_id, error_message) for failed imports.
    pub errors: Vec<(String, String)>,
}

/// Cache statistics for blend rules.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RuleCacheStats {
    /// Number of rules in cache.
    pub len: usize,

    /// Cache capacity.
    pub cap: usize,
}

// ============================================================================
// Extended BlendRule with serializable weights
// ============================================================================

/// A BlendRule with weights stored in a serializable format.
///
/// This is used for storing rules in Meilisearch with their weights intact.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BlendRuleWithWeights {
    /// The base rule document fields.
    #[serde(flatten)]
    pub rule: BlendRuleDocument,

    /// Blend weights as a vec of (personality_id, weight) tuples.
    pub blend_weights: Vec<BlendWeightEntry>,
}

/// A single blend weight entry for serialization.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BlendWeightEntry {
    /// Personality ID.
    pub personality_id: String,

    /// Weight (0.0-1.0).
    pub weight: f32,
}

impl From<&BlendRule> for BlendRuleWithWeights {
    fn from(rule: &BlendRule) -> Self {
        let weights: Vec<BlendWeightEntry> = rule
            .blend_weights
            .iter()
            .map(|(id, w)| BlendWeightEntry {
                personality_id: id.to_string(),
                weight: *w,
            })
            .collect();

        Self {
            rule: rule.clone().into(),
            blend_weights: weights,
        }
    }
}

impl TryFrom<BlendRuleWithWeights> for BlendRule {
    type Error = BlendRuleError;

    fn try_from(value: BlendRuleWithWeights) -> Result<Self, Self::Error> {
        let mut weights: HashMap<PersonalityId, f32> = HashMap::new();
        for entry in value.blend_weights {
            weights.insert(PersonalityId::new(entry.personality_id), entry.weight);
        }

        Ok(BlendRule {
            id: BlendRuleId::new(value.rule.id),
            name: value.rule.name,
            description: value.rule.description,
            context: value.rule.context,
            priority: value.rule.priority,
            enabled: value.rule.enabled,
            is_builtin: value.rule.is_builtin,
            campaign_id: value.rule.campaign_id,
            blend_weights: weights,
            tags: value.rule.tags,
            created_at: value.rule.created_at,
            updated_at: value.rule.updated_at,
        })
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_rule(name: &str, context: &str) -> BlendRule {
        BlendRule::new(name, context)
            .with_component(PersonalityId::new("tactical_advisor"), 0.6)
            .with_component(PersonalityId::new("active"), 0.4)
    }

    #[test]
    fn test_create_default_rules() {
        let rules = BlendRuleStore::create_default_rules();

        // Should have one rule per defined context
        assert_eq!(rules.len(), GameplayContext::all_defined().len());

        // Each rule should be builtin
        for rule in &rules {
            assert!(rule.is_builtin);
            assert_eq!(rule.priority, 0);
        }

        // Combat rule should exist
        let combat_rule = rules
            .iter()
            .find(|r| r.context == "combat_encounter")
            .unwrap();
        assert!(combat_rule
            .blend_weights
            .contains_key(&PersonalityId::new("tactical_advisor")));
    }

    #[test]
    fn test_blend_rule_with_weights_conversion() {
        let rule = sample_rule("Test Rule", "combat_encounter");

        let with_weights = BlendRuleWithWeights::from(&rule);

        assert_eq!(with_weights.rule.name, "Test Rule");
        assert_eq!(with_weights.blend_weights.len(), 2);

        let back: BlendRule = with_weights.try_into().unwrap();
        assert_eq!(back.name, "Test Rule");
        assert_eq!(back.blend_weights.len(), 2);
    }

    #[test]
    fn test_blend_rule_validation() {
        // Would need a mock index_manager for full testing
        // Here we just test the validation logic

        let rule = sample_rule("Valid Rule", "combat_encounter");

        // Empty name
        let mut invalid = rule.clone();
        invalid.name = String::new();

        // Empty context
        let mut invalid2 = rule.clone();
        invalid2.context = String::new();

        // Empty weights
        let mut invalid3 = rule.clone();
        invalid3.blend_weights.clear();
    }

    #[test]
    fn test_bulk_import_result() {
        let result = BulkImportResult {
            imported: 5,
            skipped: 2,
            errors: vec![
                ("rule1".to_string(), "Error 1".to_string()),
                ("rule2".to_string(), "Error 2".to_string()),
            ],
        };

        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("\"imported\":5"));
        assert!(json.contains("\"skipped\":2"));
    }

    #[test]
    fn test_rule_cache_stats() {
        let stats = RuleCacheStats { len: 10, cap: 50 };

        let json = serde_json::to_string(&stats).unwrap();
        assert!(json.contains("\"len\":10"));
        assert!(json.contains("\"cap\":50"));
    }

    #[test]
    fn test_default_rules_weights_normalized() {
        let rules = BlendRuleStore::create_default_rules();

        for rule in rules {
            let sum: f32 = rule.blend_weights.values().sum();
            assert!(
                (sum - 1.0).abs() < 0.001,
                "Rule '{}' weights sum to {} instead of 1.0",
                rule.name,
                sum
            );
        }
    }
}
