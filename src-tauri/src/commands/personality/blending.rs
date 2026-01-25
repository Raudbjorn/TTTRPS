//! Personality Blending Commands
//!
//! Commands for managing blend rules that control personality mixing.

use tauri::State;

use crate::commands::AppState;
use crate::core::personality::{
    BlendRule, BlendRuleId, BlenderCacheStats, GameplayContext, PersonalityId, RuleCacheStats,
};

use super::types::{BlendRuleResponse, SetBlendRuleRequest};

// ============================================================================
// Blend Rule Commands
// ============================================================================

/// Set (create or update) a blend rule
#[tauri::command]
pub async fn set_blend_rule(
    request: SetBlendRuleRequest,
    state: State<'_, AppState>,
) -> Result<BlendRuleResponse, String> {
    // Build the blend rule
    let mut rule = BlendRule::new(&request.name, &request.context);
    rule.campaign_id = request.campaign_id;
    rule.priority = request.priority;
    rule.description = request.description;
    rule.tags = request.tags;

    // Add components
    for comp in request.components {
        rule = rule.with_component(PersonalityId::new(comp.personality_id), comp.weight);
    }

    // Normalize weights
    rule.normalize_weights();

    // Save rule
    let saved = state.blend_rule_store.set_rule(rule).await.map_err(|e| e.to_string())?;

    log::info!("Set blend rule '{}' for context '{}'", saved.name, saved.context);

    Ok(BlendRuleResponse::from(saved))
}

/// Get a blend rule by campaign and context
#[tauri::command]
pub async fn get_blend_rule(
    campaign_id: Option<String>,
    context: String,
    state: State<'_, AppState>,
) -> Result<Option<BlendRuleResponse>, String> {
    let ctx: GameplayContext = match context.parse() {
        Ok(c) => c,
        Err(e) => {
            log::warn!("Failed to parse gameplay context '{}': {}. Defaulting to Unknown.", context, e);
            GameplayContext::Unknown
        }
    };
    let rule = state.blend_rule_store
        .get_rule_for_context(campaign_id.as_deref(), &ctx)
        .await
        .map_err(|e| e.to_string())?;

    Ok(rule.map(BlendRuleResponse::from))
}

/// List blend rules for a campaign
#[tauri::command]
pub async fn list_blend_rules(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<BlendRuleResponse>, String> {
    let rules = state.blend_rule_store
        .list_by_campaign(&campaign_id, 1000)
        .await
        .map_err(|e| e.to_string())?;

    Ok(rules.into_iter().map(BlendRuleResponse::from).collect())
}

/// Delete a blend rule
#[tauri::command]
pub async fn delete_blend_rule(
    rule_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let id = BlendRuleId::new(rule_id);
    state.blend_rule_store.delete_rule(&id).await.map_err(|e| e.to_string())?;

    log::info!("Deleted blend rule '{}'", id);

    Ok(())
}

/// Get personality blender cache statistics
#[tauri::command]
pub async fn get_blender_cache_stats(
    state: State<'_, AppState>,
) -> Result<BlenderCacheStats, String> {
    Ok(state.personality_blender.cache_stats().await)
}

/// Get blend rule cache statistics
#[tauri::command]
pub async fn get_blend_rule_cache_stats(
    state: State<'_, AppState>,
) -> Result<RuleCacheStats, String> {
    Ok(state.blend_rule_store.cache_stats().await)
}
