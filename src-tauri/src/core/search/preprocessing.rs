//! Meilisearch-lib Preprocessing Integration
//!
//! This module bridges meilisearch-lib's query preprocessing pipeline
//! with TTTRPS's existing search types. It provides:
//!
//! - O(1) typo correction using SymSpell (via meilisearch-lib)
//! - Meilisearch-compatible tolerance rules (5 chars = 1 typo, 9 chars = 2 typos)
//! - Comprehensive TTRPG synonym expansion
//! - Type adapters for TTTRPS's CorrectionResult and QueryExpansionResult
//!
//! # Architecture
//!
//! ```text
//! User Query
//!     │
//!     ▼
//! MeilisearchLibPreprocessor
//!     │
//!     ├── QueryPipeline::process()
//!     │       ├── Typo Correction (SymSpell)
//!     │       └── Synonym Expansion
//!     │
//!     ▼
//! ProcessedQuery (meilisearch-lib)
//!     │
//!     ▼
//! PreprocessingResult (TTTRPS-compatible)
//!     ├── CorrectionResult
//!     └── QueryExpansionResult
//! ```

use serde::{Deserialize, Serialize};

// Import meilisearch-lib preprocessing types
use meilisearch_lib::{
    CorrectionRecord, ExpandedQuery, ProcessedQuery, QueryPipeline, QueryPipelineBuilder,
};

// Import TTTRPS types for adaptation
use crate::core::search::synonyms::{ExpansionInfo, QueryExpansionResult};
use crate::core::spell_correction::{CorrectionResult, SpellingSuggestion};

// ============================================================================
// Preprocessing Result
// ============================================================================

/// Combined preprocessing result containing both correction and expansion info.
///
/// This is the primary result type for the preprocessing pipeline,
/// containing all information needed by HybridSearchEngine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreprocessingResult {
    /// Original query string
    pub original_query: String,
    /// Fully processed query (corrected + suitable for search)
    pub processed_query: String,
    /// Text suitable for embedding generation (corrected, NOT expanded)
    pub embedding_text: String,
    /// Spell correction details
    pub correction: CorrectionResult,
    /// Synonym expansion details
    pub expansion: QueryExpansionResult,
    /// Hints to display to the user
    pub hints: Vec<String>,
    /// Processing time in microseconds
    pub processing_time_us: u64,
}

impl PreprocessingResult {
    /// Check if any corrections were made
    pub fn has_corrections(&self) -> bool {
        self.correction.has_corrections
    }

    /// Check if any expansions were applied
    pub fn has_expansions(&self) -> bool {
        self.expansion.was_expanded
    }

    /// Get "Did you mean X?" suggestion if corrections were made
    pub fn did_you_mean(&self) -> Option<&str> {
        if self.correction.has_corrections {
            Some(&self.correction.corrected_query)
        } else {
            None
        }
    }
}

// ============================================================================
// Meilisearch-lib Preprocessor
// ============================================================================

/// Query preprocessor using meilisearch-lib's QueryPipeline.
///
/// This provides a bridge between meilisearch-lib's preprocessing
/// (TypoCorrector, SynonymMap) and TTTRPS's existing type system.
///
/// # Example
///
/// ```ignore
/// let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
/// let result = preprocessor.process("firball damge");
/// // result.correction.corrected_query = "fireball damage"
/// // result.expansion.expanded_query contains synonym alternatives
/// ```
pub struct MeilisearchLibPreprocessor {
    pipeline: QueryPipeline,
}

impl MeilisearchLibPreprocessor {
    /// Create a new preprocessor with a custom pipeline.
    pub fn new(pipeline: QueryPipeline) -> Self {
        Self { pipeline }
    }

    /// Create a preprocessor with TTRPG-optimized defaults.
    ///
    /// This uses meilisearch-lib's `build_default_ttrpg_synonyms()` and
    /// configures typo correction with Meilisearch-compatible tolerance.
    pub fn with_ttrpg_defaults() -> Self {
        let synonym_map = meilisearch_lib::preprocessing::build_default_ttrpg_synonyms();

        let pipeline = QueryPipelineBuilder::new()
            .min_word_size_one_typo(5)  // Meilisearch default
            .min_word_size_two_typos(9) // Meilisearch default
            .synonym_map(synonym_map)
            .max_expansions(5)
            .build();

        Self { pipeline }
    }

    /// Create a preprocessor with only synonym expansion (no typo correction).
    pub fn synonyms_only() -> Self {
        let synonym_map = meilisearch_lib::preprocessing::build_default_ttrpg_synonyms();

        let pipeline = QueryPipelineBuilder::new()
            .disable_typo_correction()
            .synonym_map(synonym_map)
            .build();

        Self { pipeline }
    }

    /// Create a preprocessor with only typo correction (no synonyms).
    pub fn typo_only() -> Self {
        let pipeline = QueryPipelineBuilder::new()
            .min_word_size_one_typo(5)
            .min_word_size_two_typos(9)
            .disable_synonym_expansion()
            .build();

        Self { pipeline }
    }

    /// Create a passthrough preprocessor that doesn't modify queries.
    pub fn passthrough() -> Self {
        Self {
            pipeline: QueryPipeline::passthrough(),
        }
    }

    /// Process a query through the full preprocessing pipeline.
    ///
    /// Returns a `PreprocessingResult` containing TTTRPS-compatible types.
    pub fn process(&self, query: &str) -> PreprocessingResult {
        let start = std::time::Instant::now();

        // Process through meilisearch-lib pipeline
        let processed = self.pipeline.process(query);

        let processing_time = start.elapsed().as_micros() as u64;

        // Convert to TTTRPS types
        let correction = self.to_correction_result(&processed);
        let expansion = self.to_query_expansion_result(&processed);

        // Build hints
        let mut hints = Vec::new();
        if correction.has_corrections {
            hints.push(format!("Showing results for: \"{}\"", processed.corrected));
        }
        if expansion.was_expanded {
            hints.extend(expansion.hints.clone());
        }

        PreprocessingResult {
            original_query: processed.original.clone(),
            processed_query: processed.corrected.clone(),
            embedding_text: processed.text_for_embedding.clone(),
            correction,
            expansion,
            hints,
            processing_time_us: processing_time,
        }
    }

    /// Process query and return only the corrected string.
    ///
    /// Useful when you only need typo correction without full result details.
    pub fn correct(&self, query: &str) -> String {
        let (corrected, _) = self.pipeline.correct(query);
        corrected
    }

    /// Process query and return only the expanded query.
    ///
    /// Useful when you only need synonym expansion.
    pub fn expand(&self, query: &str) -> ExpandedQuery {
        self.pipeline.expand(query)
    }

    /// Get a reference to the underlying QueryPipeline.
    pub fn pipeline(&self) -> &QueryPipeline {
        &self.pipeline
    }

    /// Get a mutable reference to the underlying QueryPipeline.
    pub fn pipeline_mut(&mut self) -> &mut QueryPipeline {
        &mut self.pipeline
    }

    /// Add protected words that should never be corrected.
    pub fn add_protected_words<I, S>(&mut self, words: I)
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        self.pipeline.typo_corrector_mut().add_protected_words(words);
    }

    /// Add a multi-way synonym group.
    pub fn add_synonyms<I, S>(&mut self, terms: I)
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        self.pipeline.synonym_map_mut().add_multi_way(terms);
    }

    /// Add a one-way synonym mapping.
    pub fn add_one_way_synonyms<S, I, T>(&mut self, source: S, targets: I)
    where
        S: AsRef<str>,
        I: IntoIterator<Item = T>,
        T: AsRef<str>,
    {
        self.pipeline.synonym_map_mut().add_one_way(source, targets);
    }

    // ========================================================================
    // Type Conversion Helpers
    // ========================================================================

    /// Convert meilisearch-lib ProcessedQuery to TTTRPS CorrectionResult.
    fn to_correction_result(&self, processed: &ProcessedQuery) -> CorrectionResult {
        let corrections: Vec<SpellingSuggestion> = processed
            .corrections
            .iter()
            .map(|cr| self.to_spelling_suggestion(cr))
            .collect();

        let has_corrections = !corrections.is_empty();

        CorrectionResult {
            original_query: processed.original.clone(),
            corrected_query: processed.corrected.clone(),
            corrections,
            has_corrections,
        }
    }

    /// Convert meilisearch-lib CorrectionRecord to TTTRPS SpellingSuggestion.
    fn to_spelling_suggestion(&self, record: &CorrectionRecord) -> SpellingSuggestion {
        // Calculate confidence based on edit distance and word length
        let word_len = record.original.len().max(1) as f64;
        let confidence = 1.0 - (record.edit_distance as f64 / word_len).min(1.0);

        SpellingSuggestion {
            original: record.original.clone(),
            suggestion: record.corrected.clone(),
            distance: record.edit_distance as usize,
            confidence,
        }
    }

    /// Convert meilisearch-lib ExpandedQuery to TTTRPS QueryExpansionResult.
    fn to_query_expansion_result(&self, processed: &ProcessedQuery) -> QueryExpansionResult {
        let expanded = &processed.expanded;

        let expansions: Vec<ExpansionInfo> = expanded
            .term_groups
            .iter()
            .filter(|group| group.has_expansions())
            .map(|group| {
                let original = group.original().unwrap_or_default().to_string();
                let expanded_to: Vec<String> = group
                    .alternatives
                    .iter()
                    .filter(|t| !t.is_original)
                    .map(|t| t.term.clone())
                    .collect();

                ExpansionInfo {
                    original,
                    expanded_to,
                    category: "synonym".to_string(),
                }
            })
            .collect();

        let was_expanded = !expansions.is_empty();

        // Build hints from expansions
        let hints: Vec<String> = expansions
            .iter()
            .map(|exp| {
                format!(
                    "\"{}\" also matches: {}",
                    exp.original,
                    exp.expanded_to.join(", ")
                )
            })
            .collect();

        QueryExpansionResult {
            original: processed.original.clone(),
            expanded_query: expanded.to_simple_string(),
            was_expanded,
            expansions,
            hints,
        }
    }
}

impl Default for MeilisearchLibPreprocessor {
    fn default() -> Self {
        Self::with_ttrpg_defaults()
    }
}

impl std::fmt::Debug for MeilisearchLibPreprocessor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MeilisearchLibPreprocessor")
            .field("pipeline", &"QueryPipeline { ... }")
            .finish()
    }
}

// ============================================================================
// Builder Pattern
// ============================================================================

/// Builder for constructing a MeilisearchLibPreprocessor with custom settings.
#[derive(Debug, Default)]
pub struct PreprocessorBuilder {
    typo_enabled: bool,
    synonyms_enabled: bool,
    min_word_size_one_typo: usize,
    min_word_size_two_typos: usize,
    max_expansions: usize,
    protected_words: Vec<String>,
    multi_way_synonyms: Vec<Vec<String>>,
    one_way_synonyms: Vec<(String, Vec<String>)>,
    use_ttrpg_defaults: bool,
}

impl PreprocessorBuilder {
    /// Create a new builder with default settings.
    pub fn new() -> Self {
        Self {
            typo_enabled: true,
            synonyms_enabled: true,
            min_word_size_one_typo: 5,
            min_word_size_two_typos: 9,
            max_expansions: 5,
            protected_words: Vec::new(),
            multi_way_synonyms: Vec::new(),
            one_way_synonyms: Vec::new(),
            use_ttrpg_defaults: false,
        }
    }

    /// Start with TTRPG default synonyms.
    pub fn with_ttrpg_defaults(mut self) -> Self {
        self.use_ttrpg_defaults = true;
        self
    }

    /// Enable or disable typo correction.
    pub fn typo_correction(mut self, enabled: bool) -> Self {
        self.typo_enabled = enabled;
        self
    }

    /// Enable or disable synonym expansion.
    pub fn synonym_expansion(mut self, enabled: bool) -> Self {
        self.synonyms_enabled = enabled;
        self
    }

    /// Set minimum word size for single-typo tolerance.
    pub fn min_word_size_one_typo(mut self, size: usize) -> Self {
        self.min_word_size_one_typo = size;
        self
    }

    /// Set minimum word size for two-typo tolerance.
    pub fn min_word_size_two_typos(mut self, size: usize) -> Self {
        self.min_word_size_two_typos = size;
        self
    }

    /// Set maximum synonym expansions per term.
    pub fn max_expansions(mut self, max: usize) -> Self {
        self.max_expansions = max;
        self
    }

    /// Add words that should never be corrected.
    pub fn protected_words<I, S>(mut self, words: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.protected_words.extend(words.into_iter().map(Into::into));
        self
    }

    /// Add a multi-way synonym group.
    pub fn synonyms<I, S>(mut self, terms: I) -> Self
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.multi_way_synonyms.push(terms.into_iter().map(Into::into).collect());
        self
    }

    /// Add a one-way synonym mapping.
    pub fn one_way<S, I, T>(mut self, source: S, targets: I) -> Self
    where
        S: Into<String>,
        I: IntoIterator<Item = T>,
        T: Into<String>,
    {
        self.one_way_synonyms.push((
            source.into(),
            targets.into_iter().map(Into::into).collect(),
        ));
        self
    }

    /// Build the preprocessor.
    pub fn build(self) -> MeilisearchLibPreprocessor {
        let mut builder = QueryPipelineBuilder::new()
            .min_word_size_one_typo(self.min_word_size_one_typo)
            .min_word_size_two_typos(self.min_word_size_two_typos)
            .max_expansions(self.max_expansions);

        if !self.typo_enabled {
            builder = builder.disable_typo_correction();
        }

        if !self.synonyms_enabled {
            builder = builder.disable_synonym_expansion();
        }

        // Start with TTRPG defaults if requested
        if self.use_ttrpg_defaults {
            builder = builder.synonym_map(meilisearch_lib::preprocessing::build_default_ttrpg_synonyms());
        }

        // Add custom synonyms
        for group in self.multi_way_synonyms {
            builder = builder.multi_way_synonyms(group.iter().map(|s| s.as_str()));
        }

        for (source, targets) in self.one_way_synonyms {
            builder = builder.one_way_synonyms(&source, targets.iter().map(|s| s.as_str()));
        }

        // Add protected words
        if !self.protected_words.is_empty() {
            builder = builder.protected_words(self.protected_words.iter().map(|s| s.as_str()));
        }

        MeilisearchLibPreprocessor::new(builder.build())
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_with_ttrpg_defaults() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        let result = preprocessor.process("hp recovery");

        // HP should expand to hit points, health, etc.
        assert!(result.expansion.was_expanded);

        // Check that we have HP-related expansions
        let hp_expansion = result.expansion.expansions.iter()
            .find(|e| e.original.to_lowercase() == "hp");
        assert!(hp_expansion.is_some());
    }

    #[test]
    fn test_typo_correction_integration() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();

        // Note: Typo correction requires dictionary loading
        // This test verifies the pipeline structure works
        let result = preprocessor.process("test query");

        assert_eq!(result.original_query, "test query");
        assert!(!result.processed_query.is_empty());
    }

    #[test]
    fn test_passthrough() {
        let preprocessor = MeilisearchLibPreprocessor::passthrough();
        let result = preprocessor.process("firball");

        // Passthrough should not correct or expand
        assert_eq!(result.processed_query, "firball");
        assert!(!result.has_corrections());
        assert!(!result.has_expansions());
    }

    #[test]
    fn test_synonyms_only() {
        let preprocessor = MeilisearchLibPreprocessor::synonyms_only();
        let result = preprocessor.process("hp");

        // Should have expansions but no corrections
        assert!(result.has_expansions());
    }

    #[test]
    fn test_builder_pattern() {
        let preprocessor = PreprocessorBuilder::new()
            .with_ttrpg_defaults()
            .max_expansions(3)
            .protected_words(["API", "HTTP"])
            .synonyms(["custom", "term", "alias"])
            .build();

        let result = preprocessor.process("custom");
        // Custom synonym should be expanded
        assert!(result.expansion.was_expanded);
    }

    #[test]
    fn test_preprocessing_result_helpers() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        let result = preprocessor.process("hp recovery");

        // Test helper methods
        assert!(result.has_expansions());
        assert!(!result.embedding_text.is_empty());
    }

    #[test]
    fn test_processing_time_tracked() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        let result = preprocessor.process("test query");

        // Processing time should be recorded
        assert!(result.processing_time_us > 0);
    }

    #[test]
    fn test_add_protected_words() {
        let mut preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        preprocessor.add_protected_words(["TTRPG", "D&D", "5e"]);

        // Protected words should not be corrected
        // (would need dictionary loaded to fully test correction bypass)
        let result = preprocessor.process("TTRPG");
        assert_eq!(result.processed_query, "TTRPG");
    }

    #[test]
    fn test_add_custom_synonyms() {
        let mut preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        preprocessor.add_synonyms(["custom1", "custom2", "custom3"]);

        let result = preprocessor.process("custom1");
        assert!(result.expansion.was_expanded);

        let expansion = result.expansion.expansions.iter()
            .find(|e| e.original == "custom1");
        assert!(expansion.is_some());
        assert!(expansion.unwrap().expanded_to.contains(&"custom2".to_string()));
    }

    #[test]
    fn test_one_way_synonyms() {
        let mut preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        preprocessor.add_one_way_synonyms("monster", ["creature", "beast"]);

        // "monster" should expand
        let result = preprocessor.process("monster");
        assert!(result.expansion.was_expanded);

        // "creature" should NOT expand to "monster" (one-way)
        let result2 = preprocessor.process("creature");
        let monster_expansion = result2.expansion.expansions.iter()
            .find(|e| e.expanded_to.contains(&"monster".to_string()));
        assert!(monster_expansion.is_none());
    }

    #[test]
    fn test_hints_generation() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        let result = preprocessor.process("hp");

        // Should have hints about synonym expansion
        assert!(!result.hints.is_empty());
    }

    #[test]
    fn test_stat_abbreviations() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();

        // Test all ability score abbreviations
        for abbr in ["str", "dex", "con", "int", "wis", "cha"] {
            let result = preprocessor.process(abbr);
            assert!(result.expansion.was_expanded, "Expected {} to expand", abbr);
        }
    }

    #[test]
    fn test_dm_gm_synonyms() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        let result = preprocessor.process("dm");

        assert!(result.expansion.was_expanded);

        let dm_expansion = result.expansion.expansions.iter()
            .find(|e| e.original.to_lowercase() == "dm");
        assert!(dm_expansion.is_some());

        let expanded_terms = &dm_expansion.unwrap().expanded_to;
        // Should expand to game master, dungeon master, gm
        assert!(
            expanded_terms.iter().any(|t| t.contains("master") || t == "gm"),
            "DM should expand to dungeon master or gm"
        );
    }

    #[test]
    fn test_condition_synonyms() {
        let preprocessor = MeilisearchLibPreprocessor::with_ttrpg_defaults();
        let result = preprocessor.process("frightened");

        assert!(result.expansion.was_expanded);

        let expansion = result.expansion.expansions.iter()
            .find(|e| e.original.to_lowercase() == "frightened");
        assert!(expansion.is_some());

        let expanded_terms = &expansion.unwrap().expanded_to;
        assert!(
            expanded_terms.iter().any(|t| t == "scared" || t == "afraid" || t == "fear"),
            "frightened should expand to scared/afraid/fear"
        );
    }
}
