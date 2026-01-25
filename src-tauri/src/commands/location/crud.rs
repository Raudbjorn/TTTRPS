//! Location CRUD Commands
//!
//! Commands for creating, reading, updating, and deleting locations.

use tauri::State;

use crate::core::location_gen::Location;
use crate::commands::AppState;

// ============================================================================
// Location CRUD Commands
// ============================================================================

/// Save a generated location to the location manager
#[tauri::command]
pub async fn save_location(
    location: Location,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let location_id = location.id.clone();

    // Save to location manager
    state.location_manager.save_location(location)
        .map_err(|e| e.to_string())?;

    Ok(location_id)
}

/// Get a location by ID
#[tauri::command]
pub fn get_location(
    location_id: String,
    state: State<'_, AppState>,
) -> Result<Option<Location>, String> {
    Ok(state.location_manager.get_location(&location_id))
}

/// List all locations for a campaign
#[tauri::command]
pub fn list_campaign_locations(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<Location>, String> {
    Ok(state.location_manager.list_locations_for_campaign(&campaign_id))
}

/// Delete a location
#[tauri::command]
pub fn delete_location(
    location_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.delete_location(&location_id)
        .map_err(|e| e.to_string())
}

/// Update a location
#[tauri::command]
pub fn update_location(
    location: Location,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.update_location(location)
        .map_err(|e| e.to_string())
}

/// Search locations by criteria
#[tauri::command]
pub fn search_locations(
    campaign_id: Option<String>,
    location_type: Option<String>,
    tags: Option<Vec<String>>,
    query: Option<String>,
    state: State<'_, AppState>,
) -> Result<Vec<Location>, String> {
    Ok(state.location_manager.search_locations(campaign_id, location_type, tags, query))
}
