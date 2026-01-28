//! Active Personality Commands
//!
//! Commands for managing active personality state in sessions.

use tauri::State;

use crate::commands::AppState;
use crate::core::personality::PersonalityPreview;

use super::types::SetActivePersonalityRequest;

// ============================================================================
// Active Personality Commands
// ============================================================================

/// Set the active personality for a session
#[tauri::command]
pub fn set_active_personality(
    request: SetActivePersonalityRequest,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.set_active_personality(
        &request.session_id,
        request.personality_id,
        &request.campaign_id,
    );
    Ok(())
}

/// Get the active personality ID for a session
#[tauri::command]
pub fn get_active_personality(
    session_id: String,
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Option<String>, String> {
    Ok(state.personality_manager.get_active_personality_id(&session_id, &campaign_id))
}

/// Get the system prompt for a personality
#[tauri::command]
pub fn get_personality_prompt(
    personality_id: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    state.personality_manager.get_personality_prompt(&personality_id)
        .map_err(|e| e.to_string())
}

/// Toggle personality application on/off
#[tauri::command]
pub fn set_personality_active(
    campaign_id: String,
    active: bool,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.set_personality_active(&campaign_id, active);
    Ok(())
}

/// List all available personalities from the store
#[tauri::command]
pub fn list_personalities(
    state: State<'_, AppState>,
) -> Result<Vec<PersonalityPreview>, String> {
    let personalities = state.personality_store.list();
    let previews: Vec<PersonalityPreview> = personalities
        .iter()
        .filter_map(|p| state.personality_manager.preview_personality(&p.id).ok())
        .collect();
    Ok(previews)
}
