//! Campaign Theme Commands
//!
//! Commands for managing campaign theme weights and presets.

use tauri::State;

use crate::commands::AppState;
use crate::core::campaign_manager::ThemeWeights;
use crate::core::theme;

// ============================================================================
// Campaign Theme Commands
// ============================================================================

/// Get the theme weights for a campaign.
#[tauri::command]
pub async fn get_campaign_theme(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<ThemeWeights, String> {
    state.campaign_manager
        .get_campaign(&campaign_id)
        .map(|c| c.settings.theme_weights)
        .ok_or_else(|| "Campaign not found".to_string())
}

/// Set the theme weights for a campaign.
#[tauri::command]
pub async fn set_campaign_theme(
    campaign_id: String,
    weights: ThemeWeights,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let mut campaign = state.campaign_manager
        .get_campaign(&campaign_id)
        .ok_or_else(|| "Campaign not found".to_string())?;

    campaign.settings.theme_weights = weights;
    state.campaign_manager.update_campaign(campaign, false)
        .map_err(|e| e.to_string())
}

/// Get the theme preset for a given game system.
#[tauri::command]
pub async fn get_theme_preset(system: String) -> Result<ThemeWeights, String> {
    Ok(theme::get_theme_preset(&system))
}
