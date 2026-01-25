//! World Events Commands
//!
//! Commands for managing world events that track significant occurrences
//! in the campaign world.

use tauri::State;

use crate::core::campaign::world_state::{
    WorldEvent, WorldEventType, EventImpact, InGameDate,
};
use crate::commands::AppState;

// ============================================================================
// World Event Commands
// ============================================================================

/// Add a world event
#[tauri::command]
pub fn add_world_event(
    campaign_id: String,
    title: String,
    description: String,
    date: InGameDate,
    event_type: String,
    impact: String,
    state: State<'_, AppState>,
) -> Result<WorldEvent, String> {
    let etype = parse_world_event_type(&event_type);
    let eimpact = parse_event_impact(&impact);

    let event = WorldEvent::new(&campaign_id, &title, &description, date)
        .with_type(etype)
        .with_impact(eimpact);

    state.world_state_manager.add_event(&campaign_id, event)
        .map_err(|e| e.to_string())
}

/// List world events (alias for get_world_events)
#[tauri::command]
pub fn list_world_events(
    campaign_id: String,
    event_type: Option<String>,
    limit: Option<usize>,
    state: State<'_, AppState>,
) -> Result<Vec<WorldEvent>, String> {
    let etype = event_type.map(|et| parse_world_event_type(&et));
    Ok(state.world_state_manager.list_events(&campaign_id, etype, limit))
}

/// Get world events with optional filtering
#[tauri::command]
pub fn get_world_events(
    campaign_id: String,
    event_type: Option<String>,
    limit: Option<usize>,
    state: State<'_, AppState>,
) -> Result<Vec<WorldEvent>, String> {
    let etype = event_type.map(|et| parse_world_event_type(&et));
    Ok(state.world_state_manager.list_events(&campaign_id, etype, limit))
}

/// Get recent world events (convenience method with default limit)
#[tauri::command]
pub fn get_recent_world_events(
    campaign_id: String,
    limit: Option<usize>,
    state: State<'_, AppState>,
) -> Result<Vec<WorldEvent>, String> {
    let default_limit = limit.unwrap_or(10);
    Ok(state.world_state_manager.list_events(&campaign_id, None, Some(default_limit)))
}

/// Delete a world event
#[tauri::command]
pub fn delete_world_event(
    campaign_id: String,
    event_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.world_state_manager.delete_event(&campaign_id, &event_id)
        .map_err(|e| e.to_string())
}

// ============================================================================
// Helper Functions
// ============================================================================

fn parse_world_event_type(s: &str) -> WorldEventType {
    match s.to_lowercase().as_str() {
        "combat" => WorldEventType::Combat,
        "political" => WorldEventType::Political,
        "natural" => WorldEventType::Natural,
        "economic" => WorldEventType::Economic,
        "religious" => WorldEventType::Religious,
        "magical" => WorldEventType::Magical,
        "social" => WorldEventType::Social,
        "personal" => WorldEventType::Personal,
        "discovery" => WorldEventType::Discovery,
        "session" => WorldEventType::Session,
        _ => WorldEventType::Custom(s.to_string()),
    }
}

fn parse_event_impact(s: &str) -> EventImpact {
    match s.to_lowercase().as_str() {
        "personal" => EventImpact::Personal,
        "local" => EventImpact::Local,
        "regional" => EventImpact::Regional,
        "national" => EventImpact::National,
        "global" => EventImpact::Global,
        "cosmic" => EventImpact::Cosmic,
        _ => EventImpact::Local,
    }
}
