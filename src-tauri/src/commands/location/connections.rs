//! Location Connections Commands
//!
//! Commands for managing connections between locations.

use tauri::State;

use crate::core::location_gen::{Location, LocationConnection, ConnectionType};
use crate::commands::AppState;

// ============================================================================
// Location Connection Commands
// ============================================================================

/// Add a connection between two locations
#[tauri::command]
pub fn add_location_connection(
    source_location_id: String,
    target_location_id: String,
    connection_type: String,
    description: Option<String>,
    travel_time: Option<String>,
    bidirectional: Option<bool>,
    state: State<'_, AppState>,
) -> Result<(), String> {
    // Parse connection_type string to enum with strict validation
    let conn_type = match connection_type.to_lowercase().as_str() {
        "door" => ConnectionType::Door,
        "path" => ConnectionType::Path,
        "road" => ConnectionType::Road,
        "stairs" => ConnectionType::Stairs,
        "ladder" => ConnectionType::Ladder,
        "portal" => ConnectionType::Portal,
        "secret" => ConnectionType::Secret,
        "water" => ConnectionType::Water,
        "climb" => ConnectionType::Climb,
        "flight" => ConnectionType::Flight,
        unknown => return Err(format!(
            "Unknown connection type: '{}'. Valid types: door, path, road, stairs, ladder, portal, secret, water, climb, flight",
            unknown
        )),
    };

    let connection = LocationConnection {
        target_id: Some(target_location_id.clone()),
        target_name: "Unknown".to_string(), // Placeholder
        connection_type: conn_type,
        description,
        travel_time,
        hazards: Vec::new(),
    };

    state.location_manager.add_connection(&source_location_id, connection.clone())
        .map_err(|e| e.to_string())?;

    // If bidirectional, add reverse connection
    if bidirectional.unwrap_or(true) {
        let reverse = LocationConnection {
            target_id: Some(source_location_id),
            target_name: "Unknown".to_string(),
            connection_type: connection.connection_type.clone(),
            description: connection.description.clone(),
            travel_time: connection.travel_time.clone(),
            hazards: connection.hazards.clone(),
        };
        state.location_manager.add_connection(&target_location_id, reverse)
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}

/// Remove a connection between locations
#[tauri::command]
pub fn remove_location_connection(
    source_location_id: String,
    target_location_id: String,
    bidirectional: Option<bool>,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.remove_connection(&source_location_id, &target_location_id)
        .map_err(|e| e.to_string())?;

    if bidirectional.unwrap_or(true) {
        state.location_manager.remove_connection(&target_location_id, &source_location_id)
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}

/// Get locations connected to a specific location
#[tauri::command]
pub fn get_connected_locations(
    location_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<Location>, String> {
    Ok(state.location_manager.get_connected_locations(&location_id))
}
