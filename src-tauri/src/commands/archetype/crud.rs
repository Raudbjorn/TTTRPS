//! Archetype CRUD Commands
//!
//! Commands for creating, reading, updating, and deleting archetypes.

use tauri::State;

use crate::core::archetype::{
    Archetype, ArchetypeCategory, PersonalityAffinity, NpcRoleMapping, NamingCultureWeight, StatTendencies,
};
use crate::commands::AppState;
use super::types::{
    CreateArchetypeRequest, ArchetypeResponse, ArchetypeSummaryResponse,
    parse_category, get_registry,
};

// ============================================================================
// TASK-ARCH-060: Archetype CRUD Commands
// ============================================================================

/// Build an Archetype from a CreateArchetypeRequest.
///
/// This helper reduces duplication between create_archetype and update_archetype.
fn build_archetype_from_request(request: CreateArchetypeRequest, category: ArchetypeCategory) -> Archetype {
    let mut archetype = Archetype::new(request.id, request.display_name.as_str(), category);

    if let Some(parent) = request.parent_id {
        archetype = archetype.with_parent(parent);
    }

    if let Some(desc) = request.description {
        archetype = archetype.with_description(desc);
    }

    // Add personality affinities
    let affinities: Vec<PersonalityAffinity> = request.personality_affinity
        .into_iter()
        .map(|p| PersonalityAffinity::new(p.trait_id, p.weight))
        .collect();
    if !affinities.is_empty() {
        archetype = archetype.with_personality_affinity(affinities);
    }

    // Add NPC role mappings
    let mappings: Vec<NpcRoleMapping> = request.npc_role_mapping
        .into_iter()
        .map(|m| NpcRoleMapping::new(m.role, m.weight))
        .collect();
    if !mappings.is_empty() {
        archetype = archetype.with_npc_role_mapping(mappings);
    }

    // Add naming cultures
    let cultures: Vec<NamingCultureWeight> = request.naming_cultures
        .into_iter()
        .map(|c| NamingCultureWeight::new(c.culture, c.weight))
        .collect();
    if !cultures.is_empty() {
        archetype = archetype.with_naming_cultures(cultures);
    }

    // Add vocabulary bank reference
    if let Some(vocab_id) = request.vocabulary_bank_id {
        archetype = archetype.with_vocabulary_bank(vocab_id);
    }

    // Add stat tendencies
    if let Some(stats) = request.stat_tendencies {
        let tendencies = StatTendencies {
            modifiers: stats.modifiers,
            minimums: stats.minimums,
            priority_order: stats.priority_order,
        };
        archetype = archetype.with_stat_tendencies(tendencies);
    }

    // Add tags
    archetype.with_tags(request.tags)
}

/// Create a new archetype.
///
/// # Arguments
/// * `request` - Archetype creation request with all fields
///
/// # Returns
/// The ID of the created archetype.
///
/// # Errors
/// - If archetype ID already exists
/// - If parent_id references non-existent archetype
/// - If validation fails
#[tauri::command]
pub async fn create_archetype(
    request: CreateArchetypeRequest,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let registry = get_registry(&state).await?;
    let category = parse_category(&request.category)?;
    let archetype = build_archetype_from_request(request, category);

    let id = registry.register(archetype).await
        .map_err(|e| e.to_string())?;

    log::info!("Created archetype: {}", id);
    Ok(id.to_string())
}

/// Get an archetype by ID.
///
/// # Arguments
/// * `id` - The archetype ID
///
/// # Returns
/// The full archetype data.
#[tauri::command]
pub async fn get_archetype(
    id: String,
    state: State<'_, AppState>,
) -> Result<ArchetypeResponse, String> {
    let registry = get_registry(&state).await?;

    let archetype = registry.get(&id).await
        .map_err(|e| e.to_string())?;

    Ok(ArchetypeResponse::from(archetype))
}

/// List all archetypes, optionally filtered by category.
///
/// # Arguments
/// * `category` - Optional category filter: "role", "race", "class", or "setting"
///
/// # Returns
/// List of archetype summaries.
#[tauri::command]
pub async fn list_archetypes(
    category: Option<String>,
    state: State<'_, AppState>,
) -> Result<Vec<ArchetypeSummaryResponse>, String> {
    let registry = get_registry(&state).await?;

    let filter = category
        .map(|c| parse_category(&c))
        .transpose()?;

    let summaries = registry.list(filter).await;

    Ok(summaries.into_iter().map(ArchetypeSummaryResponse::from).collect())
}

/// Update an existing archetype.
///
/// # Arguments
/// * `request` - Archetype update request (must have existing ID)
///
/// # Errors
/// - If archetype doesn't exist
/// - If validation fails
#[tauri::command]
pub async fn update_archetype(
    request: CreateArchetypeRequest,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let registry = get_registry(&state).await?;
    let category = parse_category(&request.category)?;
    let archetype_id = request.id.clone();
    let archetype = build_archetype_from_request(request, category);

    registry.update(archetype).await
        .map_err(|e| e.to_string())?;

    log::info!("Updated archetype: {}", archetype_id);
    Ok(())
}

/// Delete an archetype.
///
/// # Arguments
/// * `id` - The archetype ID to delete
/// * `force` - If true, ignore dependent children check
///
/// # Errors
/// - If archetype doesn't exist
/// - If archetype has dependent children (unless force=true)
#[tauri::command]
pub async fn delete_archetype(
    id: String,
    force: Option<bool>,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let registry = get_registry(&state).await?;

    // Note: The registry's delete method checks for children automatically.
    // For force deletion, we would need to delete children first.
    // For now, we don't support force deletion - user must delete children first.
    if force.unwrap_or(false) {
        return Err("Force deletion is not yet supported. Please delete child archetypes first.".to_string());
    }

    registry.delete(&id).await
        .map_err(|e| e.to_string())?;

    log::info!("Deleted archetype: {}", id);
    Ok(())
}

/// Check if an archetype exists.
///
/// # Arguments
/// * `id` - The archetype ID to check
///
/// # Returns
/// True if the archetype exists, false otherwise.
#[tauri::command]
pub async fn archetype_exists(
    id: String,
    state: State<'_, AppState>,
) -> Result<bool, String> {
    let registry = get_registry(&state).await?;
    Ok(registry.exists(&id).await)
}

/// Get the total count of archetypes.
#[tauri::command]
pub async fn count_archetypes(
    state: State<'_, AppState>,
) -> Result<usize, String> {
    let registry = get_registry(&state).await?;
    Ok(registry.count().await)
}
