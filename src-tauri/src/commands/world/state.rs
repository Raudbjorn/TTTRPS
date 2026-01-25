//! World State Commands
//!
//! Commands for retrieving and updating campaign world state.

use std::collections::HashMap;
use tauri::State;

use crate::core::campaign::world_state::{WorldState, LocationState, LocationCondition};
use crate::commands::AppState;

// ============================================================================
// World State Commands
// ============================================================================

/// Get world state for a campaign
#[tauri::command]
pub fn get_world_state(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<WorldState, String> {
    Ok(state.world_state_manager.get_or_create(&campaign_id))
}

/// Update world state
#[tauri::command]
pub fn update_world_state(
    world_state: WorldState,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.world_state_manager.update_state(world_state)
        .map_err(|e| e.to_string())
}

// ============================================================================
// Location State Commands
// ============================================================================

/// Set location state
#[tauri::command]
pub fn set_location_state(
    campaign_id: String,
    location: LocationState,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.world_state_manager.set_location_state(&campaign_id, location)
        .map_err(|e| e.to_string())
}

/// Get location state
#[tauri::command]
pub fn get_location_state(
    campaign_id: String,
    location_id: String,
    state: State<'_, AppState>,
) -> Result<Option<LocationState>, String> {
    Ok(state.world_state_manager.get_location_state(&campaign_id, &location_id))
}

/// List all locations
#[tauri::command]
pub fn list_locations(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<LocationState>, String> {
    Ok(state.world_state_manager.list_locations(&campaign_id))
}

/// Update location condition
#[tauri::command]
pub fn update_location_condition(
    campaign_id: String,
    location_id: String,
    condition: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let cond = match condition.as_str() {
        "pristine" => LocationCondition::Pristine,
        "normal" => LocationCondition::Normal,
        "damaged" => LocationCondition::Damaged,
        "ruined" => LocationCondition::Ruined,
        "destroyed" => LocationCondition::Destroyed,
        "occupied" => LocationCondition::Occupied,
        "abandoned" => LocationCondition::Abandoned,
        "under_siege" => LocationCondition::UnderSiege,
        "cursed" => LocationCondition::Cursed,
        "blessed" => LocationCondition::Blessed,
        _ => LocationCondition::Custom(condition),
    };

    state.world_state_manager.update_location_condition(&campaign_id, &location_id, cond)
        .map_err(|e| e.to_string())
}

// ============================================================================
// Custom Fields Commands
// ============================================================================

/// Set a custom field on world state
#[tauri::command]
pub fn set_world_custom_field(
    campaign_id: String,
    key: String,
    value: serde_json::Value,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.world_state_manager.set_custom_field(&campaign_id, &key, value)
        .map_err(|e| e.to_string())
}

/// Get a custom field from world state
#[tauri::command]
pub fn get_world_custom_field(
    campaign_id: String,
    key: String,
    state: State<'_, AppState>,
) -> Result<Option<serde_json::Value>, String> {
    Ok(state.world_state_manager.get_custom_field(&campaign_id, &key))
}

/// Get all custom fields
#[tauri::command]
pub fn list_world_custom_fields(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<HashMap<String, serde_json::Value>, String> {
    Ok(state.world_state_manager.list_custom_fields(&campaign_id))
}
