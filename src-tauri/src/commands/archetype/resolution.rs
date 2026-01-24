//! Archetype Resolution Commands
//!
//! Commands for resolving archetypes using the hierarchical resolution system.

use tauri::State;

use crate::core::archetype::ResolutionQuery;
use crate::commands::AppState;
use super::types::{
    ResolutionQueryRequest, ResolvedArchetypeResponse, ArchetypeCacheStatsResponse,
    get_registry,
};

// ============================================================================
// TASK-ARCH-063: Resolution Query Commands
// ============================================================================

/// Resolve an archetype using the hierarchical resolution system.
///
/// Resolution applies layers in order: Role -> Race -> Class -> Setting -> Direct ID.
/// Later layers override earlier ones according to merge rules.
///
/// # Arguments
/// * `query` - The resolution query specifying which layers to apply
///
/// # Returns
/// The resolved archetype with merged data from all applicable layers.
#[tauri::command]
pub async fn resolve_archetype(
    query: ResolutionQueryRequest,
    state: State<'_, AppState>,
) -> Result<ResolvedArchetypeResponse, String> {
    let registry = get_registry(&state).await?;

    // Build the resolution query
    let mut resolution_query = if let Some(ref id) = query.archetype_id {
        ResolutionQuery::single(id)
    } else if let Some(ref role) = query.npc_role {
        ResolutionQuery::for_npc(role)
    } else {
        return Err("Either archetype_id or npc_role must be specified".to_string());
    };

    if let Some(ref race) = query.race {
        resolution_query = resolution_query.with_race(race);
    }

    if let Some(ref class) = query.class {
        resolution_query = resolution_query.with_class(class);
    }

    if let Some(ref setting) = query.setting {
        resolution_query = resolution_query.with_setting(setting);
    }

    if let Some(ref campaign) = query.campaign_id {
        resolution_query = resolution_query.with_campaign(campaign);
    }

    // Check cache first
    if let Some(cached) = registry.get_cached(&resolution_query).await {
        let mut response = ResolvedArchetypeResponse::from(cached);
        if let Some(ref mut meta) = response.resolution_metadata {
            meta.cache_hit = true;
        }
        return Ok(response);
    }

    // Create resolver and resolve
    let resolver = crate::core::archetype::ArchetypeResolver::new(
        registry.archetypes(),
        registry.setting_packs(),
        registry.active_packs(),
    );

    let resolved = resolver.resolve(&resolution_query).await
        .map_err(|e| e.to_string())?;

    // Cache the result
    registry.cache_resolved(&resolution_query, resolved.clone()).await;

    Ok(ResolvedArchetypeResponse::from(resolved))
}

/// Convenience command to resolve an archetype for NPC generation.
///
/// This is a shortcut for the common use case of resolving by role, race, and class.
///
/// # Arguments
/// * `role` - The NPC role (e.g., "merchant", "guard")
/// * `race` - Optional race (e.g., "dwarf", "elf")
/// * `class` - Optional class (e.g., "fighter", "wizard")
/// * `setting` - Optional setting pack ID
/// * `campaign_id` - Optional campaign ID for campaign-specific settings
///
/// # Returns
/// The resolved archetype with merged data.
#[tauri::command]
pub async fn resolve_for_npc(
    role: String,
    race: Option<String>,
    class: Option<String>,
    setting: Option<String>,
    campaign_id: Option<String>,
    state: State<'_, AppState>,
) -> Result<ResolvedArchetypeResponse, String> {
    let query = ResolutionQueryRequest {
        archetype_id: None,
        npc_role: Some(role),
        race,
        class,
        setting,
        campaign_id,
    };

    resolve_archetype(query, state).await
}

/// Get cache statistics for the archetype registry.
///
/// # Returns
/// Cache statistics including size and capacity.
#[tauri::command]
pub async fn get_archetype_cache_stats(
    state: State<'_, AppState>,
) -> Result<ArchetypeCacheStatsResponse, String> {
    let registry = get_registry(&state).await?;

    let stats = registry.cache_stats().await;

    Ok(ArchetypeCacheStatsResponse {
        current_size: stats.len,
        capacity: stats.cap,
    })
}

/// Clear the archetype resolution cache.
#[tauri::command]
pub async fn clear_archetype_cache(
    state: State<'_, AppState>,
) -> Result<(), String> {
    let registry = get_registry(&state).await?;

    registry.clear_cache().await;

    log::info!("Cleared archetype resolution cache");
    Ok(())
}

/// Check if the archetype registry is initialized.
///
/// # Returns
/// True if the registry is ready to use, false otherwise.
#[tauri::command]
pub async fn is_archetype_registry_ready(
    state: State<'_, AppState>,
) -> Result<bool, String> {
    Ok(state.archetype_registry.read().await.is_some())
}
