//! Usage Tracking Commands
//!
//! Commands for tracking token usage, costs, and budgets across LLM providers.

use tauri::State;

use crate::core::usage::{
    UsageTracker, UsageStats, CostBreakdown, BudgetLimit, BudgetStatus,
    ProviderUsage,
};

// ============================================================================
// State Types
// ============================================================================

/// State wrapper for usage tracking
#[derive(Default)]
pub struct UsageTrackerState {
    pub tracker: UsageTracker,
}

// ============================================================================
// Usage Tracking Commands
// ============================================================================

/// Get total usage statistics
#[tauri::command]
pub fn get_usage_stats(state: State<'_, UsageTrackerState>) -> UsageStats {
    state.tracker.get_total_stats()
}

/// Get usage statistics for a time period (in hours)
#[tauri::command]
pub fn get_usage_by_period(hours: i64, state: State<'_, UsageTrackerState>) -> UsageStats {
    state.tracker.get_stats_by_period(hours)
}

/// Get detailed cost breakdown
#[tauri::command]
pub fn get_cost_breakdown(hours: Option<i64>, state: State<'_, UsageTrackerState>) -> CostBreakdown {
    state.tracker.get_cost_breakdown(hours)
}

/// Get current budget status for all configured limits
#[tauri::command]
pub fn get_budget_status(state: State<'_, UsageTrackerState>) -> Vec<BudgetStatus> {
    state.tracker.check_budget_status()
}

/// Set a budget limit
#[tauri::command]
pub fn set_budget_limit(limit: BudgetLimit, state: State<'_, UsageTrackerState>) -> Result<(), String> {
    state.tracker.set_budget_limit(limit);
    Ok(())
}

/// Get usage for a specific provider
#[tauri::command]
pub fn get_provider_usage(provider: String, state: State<'_, UsageTrackerState>) -> ProviderUsage {
    state.tracker.get_provider_stats(&provider)
}

/// Reset usage tracking session
#[tauri::command]
pub fn reset_usage_session(state: State<'_, UsageTrackerState>) {
    state.tracker.reset_session();
}
