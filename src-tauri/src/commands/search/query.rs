//! Search Query Commands
//!
//! Core search functionality including basic search and hybrid search.

use tauri::State;

use crate::commands::AppState;
use crate::core::search::{
    HybridSearchEngine, HybridConfig,
    hybrid::HybridSearchOptions as CoreHybridSearchOptions,
};
use super::types::{
    SearchOptions, SearchResultPayload,
    HybridSearchOptions, HybridSearchResultPayload, HybridSearchResponsePayload,
};

// ============================================================================
// Basic Search
// ============================================================================

#[tauri::command]
pub async fn search(
    query: String,
    options: Option<SearchOptions>,
    state: State<'_, AppState>,
) -> Result<Vec<SearchResultPayload>, String> {
    let opts = options.unwrap_or_default();

    // Helper to escape Meilisearch filter values (prevent injection)
    fn escape_filter_value(s: &str) -> String {
        s.replace('\\', "\\\\").replace('\'', "\\'")
    }

    // Build filter if needed (with proper escaping)
    let filter = match (&opts.source_type, &opts.campaign_id) {
        (Some(st), Some(cid)) => Some(format!(
            "source_type = '{}' AND campaign_id = '{}'",
            escape_filter_value(st),
            escape_filter_value(cid)
        )),
        (Some(st), None) => Some(format!("source_type = '{}'", escape_filter_value(st))),
        (None, Some(cid)) => Some(format!("campaign_id = '{}'", escape_filter_value(cid))),
        (None, None) => None,
    };

    let results = if let Some(index_name) = &opts.index {
        // Search specific index
        state.search_client
            .search(index_name, &query, opts.limit, filter.as_deref())
            .await
            .map_err(|e| format!("Search failed: {}", e))?
    } else {
        // Federated search across all content indexes
        let federated = state.search_client
            .search_all(&query, opts.limit)
            .await
            .map_err(|e| format!("Search failed: {}", e))?;
        federated.results
    };

    // Format results
    let formatted: Vec<SearchResultPayload> = results
        .into_iter()
        .map(|r| SearchResultPayload {
            content: r.document.content,
            source: r.document.source,
            source_type: r.document.source_type,
            page_number: r.document.page_number,
            score: r.score,
            index: r.index,
        })
        .collect();

    Ok(formatted)
}

// ============================================================================
// Hybrid Search
// ============================================================================

/// Perform hybrid search with RRF fusion
///
/// Combines keyword (Meilisearch BM25) and semantic (vector similarity) search
/// using Reciprocal Rank Fusion (RRF) for optimal ranking.
///
/// # Arguments
/// * `query` - The search query string
/// * `options` - Optional search configuration
/// * `state` - Application state containing search client
///
/// # Returns
/// Search results with RRF-fused scores, timing, and query enhancement info
#[tauri::command]
pub async fn hybrid_search(
    query: String,
    options: Option<HybridSearchOptions>,
    state: State<'_, AppState>,
) -> Result<HybridSearchResponsePayload, String> {
    let opts = options.unwrap_or_default();

    // Build hybrid config from options
    let mut config = HybridConfig::default();

    // Apply fusion strategy if specified
    if let Some(strategy) = &opts.fusion_strategy {
        config.fusion_strategy = Some(strategy.clone());
    }

    // Apply query expansion setting
    if let Some(expand) = opts.query_expansion {
        config.query_expansion = expand;
    }

    // Apply spell correction setting
    if let Some(correct) = opts.spell_correction {
        config.spell_correction = correct;
    }

    // Create hybrid search engine with configured options
    let engine = HybridSearchEngine::new(
        state.search_client.clone(),
        None, // Embedding provider - use Meilisearch's built-in for now
        config,
    );

    // Convert options to core search options
    let search_options = CoreHybridSearchOptions {
        limit: opts.limit,
        source_type: opts.source_type,
        campaign_id: opts.campaign_id,
        index: opts.index,
        semantic_weight: opts.semantic_weight,
        keyword_weight: opts.keyword_weight,
    };

    // Perform search
    let response = engine
        .search(&query, search_options)
        .await
        .map_err(|e| format!("Hybrid search failed: {}", e))?;

    // Determine overlap count for each result
    let results: Vec<HybridSearchResultPayload> = response
        .results
        .into_iter()
        .map(|r| {
            let overlap_count = match (r.keyword_rank.is_some(), r.semantic_rank.is_some()) {
                (true, true) => Some(2),
                (true, false) | (false, true) => Some(1),
                (false, false) => None,
            };

            HybridSearchResultPayload {
                content: r.document.content,
                source: r.document.source,
                source_type: r.document.source_type,
                page_number: r.document.page_number,
                score: r.score,
                index: r.index,
                keyword_rank: r.keyword_rank,
                semantic_rank: r.semantic_rank,
                overlap_count,
            }
        })
        .collect();

    // Check if within performance target
    let within_target = response.processing_time_ms < 500;

    Ok(HybridSearchResponsePayload {
        results,
        total_hits: response.total_hits,
        original_query: response.original_query,
        expanded_query: response.expanded_query,
        corrected_query: response.corrected_query,
        processing_time_ms: response.processing_time_ms,
        hints: response.hints,
        within_target,
    })
}
