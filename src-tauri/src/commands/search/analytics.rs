//! Search Analytics Commands
//!
//! Commands for recording and querying search analytics data.

use std::sync::Arc;
use tauri::State;

use crate::commands::AppState;
use crate::core::search_analytics::{
    SearchAnalytics, AnalyticsSummary, PopularQuery, CacheStats,
    ResultSelection, SearchRecord, DbSearchAnalytics,
};

// ============================================================================
// Search Analytics State
// ============================================================================

/// State wrapper for search analytics
#[derive(Default)]
pub struct SearchAnalyticsState {
    pub analytics: SearchAnalytics,
}

// ============================================================================
// In-Memory Analytics (Fast, Session-Only)
// ============================================================================

/// Get search analytics summary for a time period (in-memory)
#[tauri::command]
pub fn get_search_analytics(hours: i64, state: State<'_, SearchAnalyticsState>) -> AnalyticsSummary {
    state.analytics.get_summary(hours)
}

/// Get popular queries with detailed stats (in-memory)
#[tauri::command]
pub fn get_popular_queries(limit: usize, state: State<'_, SearchAnalyticsState>) -> Vec<PopularQuery> {
    state.analytics.get_popular_queries_detailed(limit)
}

/// Get cache statistics (in-memory)
#[tauri::command]
pub fn get_cache_stats(state: State<'_, SearchAnalyticsState>) -> CacheStats {
    state.analytics.get_cache_stats()
}

/// Get trending queries (in-memory)
#[tauri::command]
pub fn get_trending_queries(limit: usize, state: State<'_, SearchAnalyticsState>) -> Vec<String> {
    state.analytics.get_trending_queries(limit)
}

/// Get queries with zero results (in-memory)
#[tauri::command]
pub fn get_zero_result_queries(hours: i64, state: State<'_, SearchAnalyticsState>) -> Vec<String> {
    state.analytics.get_zero_result_queries(hours)
}

/// Get click position distribution
#[tauri::command]
pub fn get_click_distribution(state: State<'_, SearchAnalyticsState>) -> std::collections::HashMap<usize, u32> {
    state.analytics.get_click_position_distribution()
}

/// Record a search result selection (in-memory)
#[tauri::command]
pub fn record_search_selection(
    search_id: String,
    query: String,
    result_index: usize,
    source: String,
    selection_delay_ms: u64,
    state: State<'_, SearchAnalyticsState>,
) {
    state.analytics.record_selection(ResultSelection {
        search_id,
        query,
        result_index,
        source,
        was_helpful: None,
        selection_delay_ms,
        timestamp: chrono::Utc::now(),
    });
}

// ============================================================================
// Database-Backed Analytics (Persistent, Full History)
// ============================================================================

/// Get search analytics summary from database
#[tauri::command]
pub async fn get_search_analytics_db(
    hours: i64,
    app_state: State<'_, AppState>,
) -> Result<AnalyticsSummary, String> {
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.get_summary(hours).await
}

/// Get popular queries from database
#[tauri::command]
pub async fn get_popular_queries_db(
    limit: usize,
    app_state: State<'_, AppState>,
) -> Result<Vec<PopularQuery>, String> {
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.get_popular_queries_detailed(limit).await
}

/// Get cache statistics from database
#[tauri::command]
pub async fn get_cache_stats_db(
    app_state: State<'_, AppState>,
) -> Result<CacheStats, String> {
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.get_cache_stats().await
}

/// Get trending queries from database
#[tauri::command]
pub async fn get_trending_queries_db(
    limit: usize,
    app_state: State<'_, AppState>,
) -> Result<Vec<String>, String> {
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.get_trending_queries(limit).await
}

/// Get queries with zero results from database
#[tauri::command]
pub async fn get_zero_result_queries_db(
    hours: i64,
    app_state: State<'_, AppState>,
) -> Result<Vec<String>, String> {
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.get_zero_result_queries(hours).await
}

/// Get click position distribution from database
#[tauri::command]
pub async fn get_click_distribution_db(
    app_state: State<'_, AppState>,
) -> Result<std::collections::HashMap<usize, u32>, String> {
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.get_click_position_distribution().await
}

/// Record a search event (to both in-memory and database)
#[tauri::command]
pub async fn record_search_event(
    query: String,
    result_count: usize,
    execution_time_ms: u64,
    search_type: String,
    from_cache: bool,
    source_filter: Option<String>,
    campaign_id: Option<String>,
    state: State<'_, SearchAnalyticsState>,
    app_state: State<'_, AppState>,
) -> Result<String, String> {
    // Create search record
    let mut record = SearchRecord::new(query, result_count, execution_time_ms, search_type);
    record.from_cache = from_cache;
    record.source_filter = source_filter;
    record.campaign_id = campaign_id;
    let search_id = record.id.clone();

    // Record to in-memory analytics
    state.analytics.record(record.clone());

    // Record to database
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.record(record).await?;

    Ok(search_id)
}

/// Record a result selection (to both in-memory and database)
#[tauri::command]
pub async fn record_search_selection_db(
    search_id: String,
    query: String,
    result_index: usize,
    source: String,
    selection_delay_ms: u64,
    was_helpful: Option<bool>,
    state: State<'_, SearchAnalyticsState>,
    app_state: State<'_, AppState>,
) -> Result<(), String> {
    // Create selection record
    let selection = ResultSelection {
        search_id: search_id.clone(),
        query: query.clone(),
        result_index,
        source: source.clone(),
        was_helpful,
        selection_delay_ms,
        timestamp: chrono::Utc::now(),
    };

    // Record to in-memory analytics
    state.analytics.record_selection(selection.clone());

    // Record to database
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.record_selection(selection).await
}

/// Clean up old search analytics records
#[tauri::command]
pub async fn cleanup_search_analytics(
    days: i64,
    app_state: State<'_, AppState>,
) -> Result<u64, String> {
    let db = Arc::new(app_state.database.clone());
    let db_analytics = DbSearchAnalytics::new(db);
    db_analytics.cleanup(days).await
}
