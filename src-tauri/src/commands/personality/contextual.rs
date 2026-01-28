//! Contextual Personality Commands
//!
//! Commands for context detection and contextual personality management.

use tauri::State;

use crate::commands::AppState;
use crate::core::personality::{
    ContextDetectionResult, ContextualConfig, ContextualPersonalityResult, GameplayContext,
};

use super::types::{DetectContextRequest, GameplayContextInfo, GetContextualPersonalityRequest};

// ============================================================================
// Context Detection Commands
// ============================================================================

/// Detect gameplay context from input
#[tauri::command]
pub async fn detect_gameplay_context(
    request: DetectContextRequest,
    state: State<'_, AppState>,
) -> Result<ContextDetectionResult, String> {
    let result = state.contextual_personality_manager
        .detect_context(&request.user_input, request.session_state.as_ref())
        .await
        .map_err(|e| e.to_string())?;

    Ok(result)
}

// ============================================================================
// Contextual Personality Commands
// ============================================================================

/// Get contextual personality for a session
///
/// Combines context detection, blend rule lookup, and personality blending
/// to return the appropriate personality for the current conversation context.
#[tauri::command]
pub async fn get_contextual_personality(
    request: GetContextualPersonalityRequest,
    state: State<'_, AppState>,
) -> Result<ContextualPersonalityResult, String> {
    let result = state.contextual_personality_manager
        .get_contextual_personality(
            &request.campaign_id,
            request.session_state.as_ref(),
            &request.user_input,
        )
        .await
        .map_err(|e| e.to_string())?;

    Ok(result)
}

/// Get the current smoothed context without applying blend rules
#[tauri::command]
pub async fn get_current_context(
    state: State<'_, AppState>,
) -> Result<Option<String>, String> {
    let context = state.contextual_personality_manager.current_context().await;
    Ok(context.map(|c| c.as_str().to_string()))
}

/// Clear context detection history for a fresh start
#[tauri::command]
pub async fn clear_context_history(
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.contextual_personality_manager.clear_context_history().await;
    log::info!("Cleared context detection history");
    Ok(())
}

/// Get contextual personality configuration
#[tauri::command]
pub async fn get_contextual_personality_config(
    state: State<'_, AppState>,
) -> Result<ContextualConfig, String> {
    Ok(state.contextual_personality_manager.config().await)
}

/// Update contextual personality configuration
#[tauri::command]
pub async fn set_contextual_personality_config(
    config: ContextualConfig,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.contextual_personality_manager.set_config(config).await;
    log::info!("Updated contextual personality configuration");
    Ok(())
}

/// List all gameplay context types
#[tauri::command]
pub fn list_gameplay_contexts() -> Vec<GameplayContextInfo> {
    GameplayContext::all_defined()
        .iter()
        .map(|ctx| GameplayContextInfo {
            id: ctx.as_str().to_string(),
            name: ctx.display_name().to_string(),
            description: ctx.description().to_string(),
            is_combat_related: ctx.is_combat_related(),
        })
        .collect()
}
