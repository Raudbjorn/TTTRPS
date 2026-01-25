//! Personality Types Module
//!
//! Request and response types for personality commands.

use serde::{Deserialize, Serialize};
use crate::core::personality::{
    BlendRule, SessionStateSnapshot, SettingTemplate,
};

// ============================================================================
// Request Types
// ============================================================================

/// Request payload for setting active personality
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SetActivePersonalityRequest {
    pub session_id: String,
    pub personality_id: Option<String>,
    pub campaign_id: String,
}

/// Request payload for personality settings update
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PersonalitySettingsRequest {
    pub campaign_id: String,
    pub tone: Option<String>,
    pub vocabulary: Option<String>,
    pub narrative_style: Option<String>,
    pub verbosity: Option<String>,
    pub genre: Option<String>,
    pub custom_patterns: Option<Vec<String>>,
    pub use_dialect: Option<bool>,
    pub dialect: Option<String>,
}

/// Request for applying a template to a campaign
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ApplyTemplateRequest {
    /// Template ID to apply
    pub template_id: String,
    /// Campaign ID to apply the template to
    pub campaign_id: String,
    /// Optional session ID for immediate application
    #[serde(default)]
    pub session_id: Option<String>,
}

/// Request for creating a template from an existing personality
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateTemplateFromPersonalityRequest {
    /// Personality ID to create template from
    pub personality_id: String,
    /// Name for the new template
    pub name: String,
    /// Optional description
    #[serde(default)]
    pub description: Option<String>,
    /// Optional game system
    #[serde(default)]
    pub game_system: Option<String>,
    /// Optional setting name
    #[serde(default)]
    pub setting_name: Option<String>,
}

/// Request for setting a blend rule
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SetBlendRuleRequest {
    /// Rule name
    pub name: String,
    /// Context this rule applies to (e.g., "combat_encounter")
    pub context: String,
    /// Campaign ID (None for global rules)
    #[serde(default)]
    pub campaign_id: Option<String>,
    /// Blend components as [(personality_id, weight)]
    pub components: Vec<BlendComponentInput>,
    /// Priority (higher = evaluated first)
    #[serde(default)]
    pub priority: i32,
    /// Optional description
    #[serde(default)]
    pub description: Option<String>,
    /// Tags for categorization
    #[serde(default)]
    pub tags: Vec<String>,
}

/// Input for a blend component
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BlendComponentInput {
    /// Personality ID
    pub personality_id: String,
    /// Weight (0.0-1.0)
    pub weight: f32,
}

/// Request for context detection
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DetectContextRequest {
    /// User input text to analyze
    pub user_input: String,
    /// Optional session state for enhanced detection
    #[serde(default)]
    pub session_state: Option<SessionStateSnapshot>,
}

/// Request for contextual personality lookup
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GetContextualPersonalityRequest {
    /// Campaign ID
    pub campaign_id: String,
    /// User input text
    pub user_input: String,
    /// Optional session state
    #[serde(default)]
    pub session_state: Option<SessionStateSnapshot>,
}

// ============================================================================
// Response Types
// ============================================================================

/// Response for template preview
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TemplatePreviewResponse {
    /// Template ID
    pub id: String,
    /// Template name
    pub name: String,
    /// Description
    pub description: Option<String>,
    /// Base profile ID
    pub base_profile: String,
    /// Game system
    pub game_system: Option<String>,
    /// Setting name
    pub setting_name: Option<String>,
    /// Whether it's a built-in template
    pub is_builtin: bool,
    /// Tags
    pub tags: Vec<String>,
    /// Number of vocabulary entries
    pub vocabulary_count: usize,
    /// Number of common phrases
    pub phrase_count: usize,
}

impl From<SettingTemplate> for TemplatePreviewResponse {
    fn from(template: SettingTemplate) -> Self {
        Self {
            id: template.id.to_string(),
            name: template.name.clone(),
            description: template.description.clone(),
            base_profile: template.base_profile.to_string(),
            game_system: template.game_system.clone(),
            setting_name: template.setting_name.clone(),
            is_builtin: template.is_builtin,
            tags: template.tags.clone(),
            vocabulary_count: template.vocabulary.len(),
            phrase_count: template.common_phrases.len(),
        }
    }
}

/// Response for blend rule
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BlendRuleResponse {
    /// Rule ID
    pub id: String,
    /// Rule name
    pub name: String,
    /// Description
    pub description: Option<String>,
    /// Context
    pub context: String,
    /// Priority
    pub priority: i32,
    /// Whether the rule is enabled
    pub enabled: bool,
    /// Whether it's a built-in rule
    pub is_builtin: bool,
    /// Campaign ID
    pub campaign_id: Option<String>,
    /// Blend weights
    pub blend_weights: Vec<BlendComponentInput>,
    /// Tags
    pub tags: Vec<String>,
}

impl From<BlendRule> for BlendRuleResponse {
    fn from(rule: BlendRule) -> Self {
        Self {
            id: rule.id.to_string(),
            name: rule.name,
            description: rule.description,
            context: rule.context,
            priority: rule.priority,
            enabled: rule.enabled,
            is_builtin: rule.is_builtin,
            campaign_id: rule.campaign_id,
            blend_weights: rule
                .blend_weights
                .into_iter()
                .map(|(id, weight)| BlendComponentInput {
                    personality_id: id.to_string(),
                    weight,
                })
                .collect(),
            tags: rule.tags,
        }
    }
}

/// Info about a gameplay context for the frontend
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GameplayContextInfo {
    /// Context ID (e.g., "combat_encounter")
    pub id: String,
    /// Display name (e.g., "Combat Encounter")
    pub name: String,
    /// Description of when this context applies
    pub description: String,
    /// Whether this is a combat-related context
    pub is_combat_related: bool,
}
