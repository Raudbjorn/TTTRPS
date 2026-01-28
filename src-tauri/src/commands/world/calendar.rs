//! Calendar Commands
//!
//! Commands for managing in-game calendar and date tracking.

use tauri::State;

use crate::core::campaign::world_state::{InGameDate, CalendarConfig};
use crate::commands::AppState;

// ============================================================================
// In-Game Calendar Commands
// ============================================================================

/// Set current in-game date
#[tauri::command]
pub fn set_in_game_date(
    campaign_id: String,
    date: InGameDate,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.world_state_manager.set_current_date(&campaign_id, date)
        .map_err(|e| e.to_string())
}

/// Advance in-game date by days
#[tauri::command]
pub fn advance_in_game_date(
    campaign_id: String,
    days: i32,
    state: State<'_, AppState>,
) -> Result<InGameDate, String> {
    state.world_state_manager.advance_date(&campaign_id, days)
        .map_err(|e| e.to_string())
}

/// Get current in-game date
#[tauri::command]
pub fn get_in_game_date(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<InGameDate, String> {
    state.world_state_manager.get_current_date(&campaign_id)
        .map_err(|e| e.to_string())
}

/// Set calendar configuration
#[tauri::command]
pub fn set_calendar_config(
    campaign_id: String,
    config: CalendarConfig,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.world_state_manager.set_calendar_config(&campaign_id, config)
        .map_err(|e| e.to_string())
}

/// Get calendar configuration
#[tauri::command]
pub fn get_calendar_config(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Option<CalendarConfig>, String> {
    Ok(state.world_state_manager.get_calendar_config(&campaign_id))
}
