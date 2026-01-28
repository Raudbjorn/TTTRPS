//! Location Details Commands
//!
//! Commands for managing location inhabitants, secrets, encounters, and map references.

use tauri::State;

use crate::core::location_gen::{Inhabitant, Secret, Encounter, MapReference};
use crate::commands::AppState;

// ============================================================================
// Location Details Commands
// ============================================================================

/// Add an inhabitant to a location
#[tauri::command]
pub fn add_location_inhabitant(
    location_id: String,
    inhabitant: Inhabitant,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.add_inhabitant(&location_id, inhabitant)
        .map_err(|e| e.to_string())
}

/// Remove an inhabitant from a location
#[tauri::command]
pub fn remove_location_inhabitant(
    location_id: String,
    inhabitant_name: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.remove_inhabitant(&location_id, &inhabitant_name)
        .map_err(|e| e.to_string())
}

/// Add a secret to a location
#[tauri::command]
pub fn add_location_secret(
    location_id: String,
    secret: Secret,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.add_secret(&location_id, secret)
        .map_err(|e| e.to_string())
}

/// Add an encounter to a location
#[tauri::command]
pub fn add_location_encounter(
    location_id: String,
    encounter: Encounter,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.add_encounter(&location_id, encounter)
        .map_err(|e| e.to_string())
}

/// Set map reference for a location
#[tauri::command]
pub fn set_location_map_reference(
    location_id: String,
    map_reference: MapReference,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.location_manager.set_map_reference(&location_id, map_reference)
        .map_err(|e| e.to_string())
}
