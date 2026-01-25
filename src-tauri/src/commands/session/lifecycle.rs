//! Session Lifecycle Commands
//!
//! Commands for managing session lifecycle: start, get, list, end,
//! planned sessions, and session reordering.

use tauri::State;

use crate::commands::AppState;
use crate::core::session_manager::{GameSession, SessionSummary};

// ============================================================================
// Session CRUD Commands
// ============================================================================

/// Start a new game session for a campaign.
///
/// # Arguments
/// * `campaign_id` - The campaign to start the session for
/// * `session_number` - The session number within the campaign
///
/// # Returns
/// The newly created GameSession.
#[tauri::command]
pub fn start_session(
    campaign_id: String,
    session_number: u32,
    state: State<'_, AppState>,
) -> Result<GameSession, String> {
    Ok(state.session_manager.start_session(&campaign_id, session_number))
}

/// Get a session by ID.
///
/// # Arguments
/// * `session_id` - The session ID to retrieve
///
/// # Returns
/// The session if found, None otherwise.
#[tauri::command]
pub fn get_session(session_id: String, state: State<'_, AppState>) -> Result<Option<GameSession>, String> {
    Ok(state.session_manager.get_session(&session_id))
}

/// Get the active session for a campaign.
///
/// # Arguments
/// * `campaign_id` - The campaign to get the active session for
///
/// # Returns
/// The active session if one exists, None otherwise.
#[tauri::command]
pub fn get_active_session(campaign_id: String, state: State<'_, AppState>) -> Result<Option<GameSession>, String> {
    Ok(state.session_manager.get_active_session(&campaign_id))
}

/// List all sessions for a campaign.
///
/// # Arguments
/// * `campaign_id` - The campaign to list sessions for
///
/// # Returns
/// List of session summaries for the campaign.
#[tauri::command]
pub fn list_sessions(campaign_id: String, state: State<'_, AppState>) -> Result<Vec<SessionSummary>, String> {
    Ok(state.session_manager.list_sessions(&campaign_id))
}

/// End an active session.
///
/// # Arguments
/// * `session_id` - The session ID to end
///
/// # Returns
/// Summary of the ended session.
///
/// # Errors
/// If the session is not found or already ended.
#[tauri::command]
pub fn end_session(session_id: String, state: State<'_, AppState>) -> Result<SessionSummary, String> {
    state.session_manager.end_session(&session_id)
        .map_err(|e| e.to_string())
}

/// Create a planned session for a campaign.
///
/// Planned sessions can be prepared in advance and later started.
///
/// # Arguments
/// * `campaign_id` - The campaign to create the session for
/// * `title` - Optional title for the planned session
///
/// # Returns
/// The newly created planned session.
#[tauri::command]
pub fn create_planned_session(
    campaign_id: String,
    title: Option<String>,
    state: State<'_, AppState>,
) -> Result<GameSession, String> {
    Ok(state.session_manager.create_planned_session(&campaign_id, title))
}

/// Start a previously planned session.
///
/// Transitions a planned session to active status.
///
/// # Arguments
/// * `session_id` - The planned session ID to start
///
/// # Returns
/// The now-active session.
///
/// # Errors
/// If the session is not found or not in planned status.
#[tauri::command]
pub fn start_planned_session(
    session_id: String,
    state: State<'_, AppState>,
) -> Result<GameSession, String> {
    state.session_manager.start_planned_session(&session_id)
        .map_err(|e| e.to_string())
}

/// Reorder a session within its campaign's session list.
///
/// # Arguments
/// * `session_id` - The session to reorder
/// * `new_order` - The new order position
///
/// # Errors
/// If the session is not found.
#[tauri::command]
pub fn reorder_session(
    session_id: String,
    new_order: i32,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.session_manager.reorder_session(&session_id, new_order)
        .map_err(|e| e.to_string())
}
