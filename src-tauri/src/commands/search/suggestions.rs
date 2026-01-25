//! Search Suggestions Commands
//!
//! Commands for autocomplete, query hints, query expansion, and spell correction.

use tauri::State;

use crate::commands::AppState;
use crate::core::search::HybridSearchEngine;

// ============================================================================
// Search Suggestions and Hints
// ============================================================================

/// Get search suggestions for autocomplete
#[tauri::command]
pub fn get_search_suggestions(
    partial: String,
    state: State<'_, AppState>,
) -> Vec<String> {
    let engine = HybridSearchEngine::with_defaults(state.search_client.clone());
    engine.suggest(&partial)
}

/// Get search hints for a query
#[tauri::command]
pub fn get_search_hints(
    query: String,
    state: State<'_, AppState>,
) -> Vec<String> {
    let engine = HybridSearchEngine::with_defaults(state.search_client.clone());
    engine.get_hints(&query)
}

/// Expand a query with TTRPG synonyms
#[tauri::command]
pub fn expand_query(query: String) -> crate::core::search::synonyms::QueryExpansionResult {
    let synonyms = crate::core::search::TTRPGSynonyms::new();
    synonyms.expand_query(&query)
}

/// Correct spelling in a query
#[tauri::command]
pub fn correct_query(query: String) -> crate::core::spell_correction::CorrectionResult {
    let corrector = crate::core::spell_correction::SpellCorrector::new();
    corrector.correct(&query)
}
