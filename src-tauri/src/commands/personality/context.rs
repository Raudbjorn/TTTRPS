//! Personality Context Commands
//!
//! Commands for managing personality context in campaigns and sessions.

use tauri::State;

use crate::commands::AppState;
use crate::core::personality::ActivePersonalityContext;

// ============================================================================
// Personality Context Commands
// ============================================================================

/// Get personality context for a campaign
#[tauri::command]
pub fn get_personality_context(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<ActivePersonalityContext, String> {
    Ok(state.personality_manager.get_context(&campaign_id))
}

/// Get personality context for a session
#[tauri::command]
pub fn get_session_personality_context(
    session_id: String,
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<ActivePersonalityContext, String> {
    Ok(state.personality_manager.get_session_context(&session_id, &campaign_id))
}

/// Update personality context for a campaign
#[tauri::command]
pub fn set_personality_context(
    context: ActivePersonalityContext,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.set_context(context);
    Ok(())
}

/// Clear session-specific personality context
#[tauri::command]
pub fn clear_session_personality_context(
    session_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.clear_session_context(&session_id);
    Ok(())
}
