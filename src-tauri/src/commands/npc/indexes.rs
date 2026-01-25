//! NPC Index Commands
//!
//! Commands for managing NPC Meilisearch indexes.

use tauri::State;

use crate::commands::AppState;
use crate::core::npc_gen::{NpcIndexStats, ensure_npc_indexes, get_npc_index_stats};

// ============================================================================
// NPC Index Commands
// ============================================================================

/// Initialize NPC extension indexes in Meilisearch
#[tauri::command]
pub async fn initialize_npc_indexes(
    state: State<'_, AppState>,
) -> Result<(), String> {
    ensure_npc_indexes(state.search_client.get_client())
        .await
        .map_err(|e| e.to_string())
}

/// Get NPC index statistics
#[tauri::command]
pub async fn get_npc_indexes_stats(
    state: State<'_, AppState>,
) -> Result<NpcIndexStats, String> {
    get_npc_index_stats(state.search_client.get_client())
        .await
        .map_err(|e| e.to_string())
}

/// Clear NPC indexes
#[tauri::command]
pub async fn clear_npc_indexes(
    state: State<'_, AppState>,
) -> Result<(), String> {
    crate::core::npc_gen::clear_npc_indexes(state.search_client.get_client())
        .await
        .map_err(|e| e.to_string())
}
