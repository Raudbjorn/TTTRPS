//! Setting Pack Commands
//!
//! Commands for loading and managing campaign setting packs.

use tauri::State;
use std::collections::HashSet;

use crate::core::archetype::SettingPackSummary;
use crate::commands::AppState;
use super::types::{SettingPackSummaryResponse, get_registry};

// ============================================================================
// TASK-ARCH-062: Setting Pack Commands
// ============================================================================

/// Load a setting pack from a file path.
///
/// # Arguments
/// * `path` - Path to the YAML or JSON setting pack file
///
/// # Returns
/// The version key of the loaded pack (format: "pack_id@version").
#[tauri::command]
pub async fn load_setting_pack(
    path: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let loader = &state.setting_pack_loader;

    let vkey = loader.load_from_file(&path).await
        .map_err(|e| e.to_string())?;

    log::info!("Loaded setting pack from {}: {}", path, vkey);
    Ok(vkey)
}

/// List all loaded setting packs.
///
/// # Returns
/// List of setting pack summaries (latest version of each).
#[tauri::command]
pub async fn list_setting_packs(
    state: State<'_, AppState>,
) -> Result<Vec<SettingPackSummaryResponse>, String> {
    let loader = &state.setting_pack_loader;

    let summaries = loader.list_packs().await;

    Ok(summaries.into_iter().map(SettingPackSummaryResponse::from).collect())
}

/// Get a setting pack by ID.
///
/// # Arguments
/// * `pack_id` - The setting pack ID
/// * `version` - Optional specific version (uses latest if not specified)
///
/// # Returns
/// The setting pack data.
#[tauri::command]
pub async fn get_setting_pack(
    pack_id: String,
    version: Option<String>,
    state: State<'_, AppState>,
) -> Result<SettingPackSummaryResponse, String> {
    let loader = &state.setting_pack_loader;

    let pack = if let Some(ver) = version {
        loader.get_version(&pack_id, &ver).await
    } else {
        loader.get_latest(&pack_id).await
    }.map_err(|e| e.to_string())?;

    Ok(SettingPackSummaryResponse::from(SettingPackSummary::from(&pack)))
}

/// Activate a setting pack for a campaign.
///
/// # Arguments
/// * `pack_id` - The setting pack ID to activate
/// * `campaign_id` - The campaign ID to activate for
///
/// # Errors
/// - If pack is not loaded
/// - If pack references missing archetypes
#[tauri::command]
pub async fn activate_setting_pack(
    pack_id: String,
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let loader = &state.setting_pack_loader;
    let registry = get_registry(&state).await?;

    // Get existing archetype IDs for validation
    let existing: HashSet<String> = registry.list(None).await
        .into_iter()
        .map(|s| s.id.to_string())
        .collect();

    loader.activate(&pack_id, &campaign_id, &existing).await
        .map_err(|e| e.to_string())?;

    log::info!("Activated setting pack '{}' for campaign '{}'", pack_id, campaign_id);
    Ok(())
}

/// Deactivate the setting pack for a campaign.
///
/// # Arguments
/// * `campaign_id` - The campaign ID to deactivate pack for
#[tauri::command]
pub async fn deactivate_setting_pack(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let loader = &state.setting_pack_loader;

    loader.deactivate(&campaign_id).await
        .map_err(|e| e.to_string())?;

    log::info!("Deactivated setting pack for campaign '{}'", campaign_id);
    Ok(())
}

/// Get the active setting pack for a campaign.
///
/// # Arguments
/// * `campaign_id` - The campaign ID
///
/// # Returns
/// The active setting pack summary, or null if none active.
#[tauri::command]
pub async fn get_active_setting_pack(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Option<SettingPackSummaryResponse>, String> {
    let loader = &state.setting_pack_loader;

    let pack = loader.get_active_pack(&campaign_id).await;

    Ok(pack.map(|p| SettingPackSummaryResponse::from(SettingPackSummary::from(&p))))
}

/// Get all versions of a setting pack.
///
/// # Arguments
/// * `pack_id` - The setting pack ID
///
/// # Returns
/// List of version strings sorted by semver.
#[tauri::command]
pub async fn get_setting_pack_versions(
    pack_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<String>, String> {
    let loader = &state.setting_pack_loader;

    Ok(loader.get_versions(&pack_id).await)
}
