//! Timeline Event Commands
//!
//! Commands for managing session timeline events, tracking notable
//! occurrences during gameplay sessions.

use std::collections::HashMap;
use tauri::State;

use crate::commands::AppState;
use crate::core::session::timeline::{
    TimelineEvent, TimelineEventType, EventSeverity, EntityRef, TimelineSummary,
};

// ============================================================================
// Session Timeline Commands
// ============================================================================

/// Add a timeline event to a session
#[tauri::command]
pub fn add_timeline_event(
    session_id: String,
    event_type: String,
    title: String,
    description: String,
    severity: Option<String>,
    entity_refs: Option<Vec<EntityRef>>,
    tags: Option<Vec<String>>,
    metadata: Option<HashMap<String, serde_json::Value>>,
    state: State<'_, AppState>,
) -> Result<TimelineEvent, String> {
    let etype = match event_type.as_str() {
        "session_start" => TimelineEventType::SessionStart,
        "session_end" => TimelineEventType::SessionEnd,
        "combat_start" => TimelineEventType::CombatStart,
        "combat_end" => TimelineEventType::CombatEnd,
        "combat_round_start" => TimelineEventType::CombatRoundStart,
        "combat_turn_start" => TimelineEventType::CombatTurnStart,
        "combat_damage" => TimelineEventType::CombatDamage,
        "combat_healing" => TimelineEventType::CombatHealing,
        "combat_death" => TimelineEventType::CombatDeath,
        "note_added" => TimelineEventType::NoteAdded,
        "npc_interaction" => TimelineEventType::NPCInteraction,
        "location_change" => TimelineEventType::LocationChange,
        "player_action" => TimelineEventType::PlayerAction,
        "condition_applied" => TimelineEventType::ConditionApplied,
        "condition_removed" => TimelineEventType::ConditionRemoved,
        "item_acquired" => TimelineEventType::ItemAcquired,
        _ => TimelineEventType::Custom(event_type),
    };

    let eseverity = severity.map(|s| match s.as_str() {
        "trace" => EventSeverity::Trace,
        "info" => EventSeverity::Info,
        "notable" => EventSeverity::Notable,
        "important" => EventSeverity::Important,
        "critical" => EventSeverity::Critical,
        _ => EventSeverity::Info,
    }).unwrap_or(EventSeverity::Info);

    let mut event = TimelineEvent::new(&session_id, etype, &title, &description)
        .with_severity(eseverity);

    if let Some(refs) = entity_refs {
        for r in refs {
            event.entity_refs.push(r);
        }
    }

    if let Some(t) = tags {
        event.tags = t;
    }

    if let Some(m) = metadata {
        event.metadata = m;
    }

    // Store in session manager's timeline
    state.session_manager.add_timeline_event(&session_id, event.clone())
        .map_err(|e| e.to_string())?;

    Ok(event)
}

/// Get the timeline for a session
#[tauri::command]
pub fn get_session_timeline(
    session_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<TimelineEvent>, String> {
    Ok(state.session_manager.get_timeline_events(&session_id))
}

/// Get timeline summary for a session
#[tauri::command]
pub fn get_timeline_summary(
    session_id: String,
    state: State<'_, AppState>,
) -> Result<TimelineSummary, String> {
    state.session_manager.get_timeline_summary(&session_id)
        .map_err(|e| e.to_string())
}

/// Get timeline events by type
#[tauri::command]
pub fn get_timeline_events_by_type(
    session_id: String,
    event_type: String,
    state: State<'_, AppState>,
) -> Result<Vec<TimelineEvent>, String> {
    let etype = match event_type.as_str() {
        "session_start" => TimelineEventType::SessionStart,
        "session_end" => TimelineEventType::SessionEnd,
        "combat_start" => TimelineEventType::CombatStart,
        "combat_end" => TimelineEventType::CombatEnd,
        "note_added" => TimelineEventType::NoteAdded,
        "npc_interaction" => TimelineEventType::NPCInteraction,
        "location_change" => TimelineEventType::LocationChange,
        _ => TimelineEventType::Custom(event_type),
    };

    Ok(state.session_manager.get_timeline_events_by_type(&session_id, &etype))
}
