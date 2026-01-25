//! LLM Router Commands
//!
//! Commands for managing the LLM router: health checks, costs, routing strategies.

use std::collections::HashMap;
use tauri::State;

use crate::commands::state::AppState;
use crate::core::llm::router::ProviderStats;
use crate::core::llm::{CostSummary, ProviderHealth, RoutingStrategy};

// ============================================================================
// Commands
// ============================================================================

/// Get router statistics for all providers
#[tauri::command]
pub async fn get_router_stats(state: State<'_, AppState>) -> Result<HashMap<String, ProviderStats>, String> {
    Ok(state.llm_router.read().await.get_all_stats().await)
}

/// Get health status of all providers
#[tauri::command]
pub async fn get_router_health(
    state: State<'_, AppState>,
) -> Result<HashMap<String, ProviderHealth>, String> {
    let router = state.llm_router.read().await.clone();
    Ok(router.get_all_health().await)
}

/// Get cost summary for the router
#[tauri::command]
pub async fn get_router_costs(
    state: State<'_, AppState>,
) -> Result<CostSummary, String> {
    let router = state.llm_router.read().await.clone();
    Ok(router.get_cost_summary().await)
}

/// Estimate cost for a request
#[tauri::command]
pub async fn estimate_request_cost(
    provider: String,
    model: String,
    input_tokens: u32,
    output_tokens: u32,
    state: State<'_, AppState>,
) -> Result<f64, String> {
    let router = state.llm_router.read().await.clone();
    Ok(router.estimate_cost(&provider, &model, input_tokens, output_tokens).await)
}

/// Get list of healthy providers
#[tauri::command]
pub async fn get_healthy_providers(
    state: State<'_, AppState>,
) -> Result<Vec<String>, String> {
    let router = state.llm_router.read().await.clone();
    Ok(router.healthy_providers().await)
}

/// Set the routing strategy
#[tauri::command]
pub async fn set_routing_strategy(
    strategy: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let strategy = match strategy.to_lowercase().as_str() {
        "priority" => RoutingStrategy::Priority,
        "cost" | "cost_optimized" | "costoptimized" => RoutingStrategy::CostOptimized,
        "latency" | "latency_optimized" | "latencyoptimized" => RoutingStrategy::LatencyOptimized,
        "round_robin" | "roundrobin" => RoutingStrategy::RoundRobin,
        _ => return Err(format!("Unknown routing strategy: {}", strategy)),
    };

    let mut router = state.llm_router.write().await;
    router.set_routing_strategy(strategy);
    Ok(())
}

/// Run health checks on all providers
#[tauri::command]
pub async fn run_provider_health_checks(
    state: State<'_, AppState>,
) -> Result<HashMap<String, bool>, String> {
    let router = state.llm_router.read().await;
    let router_clone = router.clone();
    drop(router); // Release the lock before async operation

    Ok(router_clone.health_check_all().await)
}
