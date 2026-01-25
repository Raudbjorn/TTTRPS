//! Entity Relationship Graph Commands
//!
//! Commands for querying and visualizing entity relationship graphs.

use tauri::State;

use crate::core::campaign::relationships::{EntityRelationship, EntityGraph};
use crate::commands::AppState;

// ============================================================================
// Relationship Query Commands
// ============================================================================

/// Get relationships for a specific entity
#[tauri::command]
pub fn get_relationships_for_entity(
    campaign_id: String,
    entity_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<EntityRelationship>, String> {
    Ok(state.relationship_manager.get_entity_relationships(&campaign_id, &entity_id))
}

/// Get relationships between two entities
#[tauri::command]
pub fn get_relationships_between_entities(
    campaign_id: String,
    entity_a: String,
    entity_b: String,
    state: State<'_, AppState>,
) -> Result<Vec<EntityRelationship>, String> {
    Ok(state.relationship_manager.get_relationships_between(&campaign_id, &entity_a, &entity_b))
}

// ============================================================================
// Graph Operations
// ============================================================================

/// Get the full entity graph for visualization
#[tauri::command]
pub fn get_entity_graph(
    campaign_id: String,
    include_inactive: Option<bool>,
    state: State<'_, AppState>,
) -> Result<EntityGraph, String> {
    Ok(state.relationship_manager.get_entity_graph(&campaign_id, include_inactive.unwrap_or(false)))
}

/// Get ego graph centered on an entity
#[tauri::command]
pub fn get_ego_graph(
    campaign_id: String,
    entity_id: String,
    depth: Option<usize>,
    state: State<'_, AppState>,
) -> Result<EntityGraph, String> {
    Ok(state.relationship_manager.get_ego_graph(&campaign_id, &entity_id, depth.unwrap_or(2)))
}
