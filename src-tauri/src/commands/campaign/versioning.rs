//! Campaign Versioning Commands
//!
//! Commands for managing campaign versions, including creation, comparison,
//! rollback, tagging, and milestone marking.

use tauri::State;

use crate::commands::AppState;
use crate::core::campaign::versioning::{
    CampaignVersion, VersionType, CampaignDiff, VersionSummary,
};
use crate::core::models::Campaign;

// ============================================================================
// Campaign Versioning Commands (TASK-006)
// ============================================================================

/// Create a new campaign version.
#[tauri::command]
pub fn create_campaign_version(
    campaign_id: String,
    description: String,
    version_type: String,
    state: State<'_, AppState>,
) -> Result<VersionSummary, String> {
    // Get current campaign data as JSON
    let campaign = state.campaign_manager.get_campaign(&campaign_id)
        .ok_or_else(|| "Campaign not found".to_string())?;

    let data_snapshot = serde_json::to_string(&campaign)
        .map_err(|e| format!("Failed to serialize campaign: {}", e))?;

    let vtype = match version_type.as_str() {
        "auto" => VersionType::Auto,
        "milestone" => VersionType::Milestone,
        "pre_rollback" => VersionType::PreRollback,
        "import" => VersionType::Import,
        _ => VersionType::Manual,
    };

    let version = state.version_manager.create_version(
        &campaign_id,
        &description,
        vtype,
        &data_snapshot,
    ).map_err(|e| e.to_string())?;

    Ok(VersionSummary::from(&version))
}

/// List all versions for a campaign.
#[tauri::command]
pub fn list_campaign_versions(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<VersionSummary>, String> {
    Ok(state.version_manager.list_versions(&campaign_id))
}

/// Get a specific version.
#[tauri::command]
pub fn get_campaign_version(
    campaign_id: String,
    version_id: String,
    state: State<'_, AppState>,
) -> Result<CampaignVersion, String> {
    state.version_manager.get_version(&campaign_id, &version_id)
        .ok_or_else(|| "Version not found".to_string())
}

/// Compare two versions.
#[tauri::command]
pub fn compare_campaign_versions(
    campaign_id: String,
    from_version_id: String,
    to_version_id: String,
    state: State<'_, AppState>,
) -> Result<CampaignDiff, String> {
    state.version_manager.compare_versions(&campaign_id, &from_version_id, &to_version_id)
        .map_err(|e| e.to_string())
}

/// Rollback a campaign to a previous version.
#[tauri::command]
pub fn rollback_campaign(
    campaign_id: String,
    version_id: String,
    state: State<'_, AppState>,
) -> Result<Campaign, String> {
    // Get current campaign data for pre-rollback snapshot
    let current = state.campaign_manager.get_campaign(&campaign_id)
        .ok_or_else(|| "Campaign not found".to_string())?;

    let current_json = serde_json::to_string(&current)
        .map_err(|e| format!("Failed to serialize current state: {}", e))?;

    // Prepare rollback (creates pre-rollback snapshot and returns target data)
    let target_data = state.version_manager.prepare_rollback(&campaign_id, &version_id, &current_json)
        .map_err(|e| e.to_string())?;

    // Deserialize and restore campaign
    let restored: Campaign = serde_json::from_str(&target_data)
        .map_err(|e| format!("Failed to deserialize version data: {}", e))?;

    state.campaign_manager.update_campaign(restored.clone(), false)
        .map_err(|e| e.to_string())?;

    Ok(restored)
}

/// Delete a version.
#[tauri::command]
pub fn delete_campaign_version(
    campaign_id: String,
    version_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.version_manager.delete_version(&campaign_id, &version_id)
        .map_err(|e| e.to_string())
}

/// Add a tag to a version.
#[tauri::command]
pub fn add_version_tag(
    campaign_id: String,
    version_id: String,
    tag: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.version_manager.add_tag(&campaign_id, &version_id, &tag)
        .map_err(|e| e.to_string())
}

/// Mark a version as a milestone.
#[tauri::command]
pub fn mark_version_milestone(
    campaign_id: String,
    version_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.version_manager.mark_as_milestone(&campaign_id, &version_id)
        .map_err(|e| e.to_string())
}
