//! Campaign Snapshot Commands
//!
//! Commands for creating, listing, and restoring campaign snapshots,
//! as well as import/export functionality.

use tauri::State;

use crate::commands::AppState;
use crate::core::campaign_manager::SnapshotSummary;

// ============================================================================
// Campaign Snapshot Commands
// ============================================================================

/// Create a manual snapshot of a campaign.
#[tauri::command]
pub fn create_snapshot(
    campaign_id: String,
    description: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    state.campaign_manager.create_snapshot(&campaign_id, &description)
        .map_err(|e| e.to_string())
}

/// List all snapshots for a campaign.
#[tauri::command]
pub fn list_snapshots(campaign_id: String, state: State<'_, AppState>) -> Result<Vec<SnapshotSummary>, String> {
    Ok(state.campaign_manager.list_snapshots(&campaign_id))
}

/// Restore a campaign from a snapshot.
#[tauri::command]
pub fn restore_snapshot(
    campaign_id: String,
    snapshot_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.campaign_manager.restore_snapshot(&campaign_id, &snapshot_id)
        .map_err(|e| e.to_string())
}

/// Export a campaign to JSON.
#[tauri::command]
pub fn export_campaign(campaign_id: String, state: State<'_, AppState>) -> Result<String, String> {
    state.campaign_manager.export_to_json(&campaign_id)
        .map_err(|e| e.to_string())
}

/// Import a campaign from JSON.
#[tauri::command]
pub fn import_campaign(
    json: String,
    new_id: bool,
    state: State<'_, AppState>,
) -> Result<String, String> {
    state.campaign_manager.import_from_json(&json, new_id)
        .map_err(|e| e.to_string())
}
