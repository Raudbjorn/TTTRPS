//! Entity Relationship CRUD Commands
//!
//! Commands for creating, reading, updating, and deleting entity relationships.

use tauri::State;

use crate::core::campaign::relationships::{
    EntityRelationship, RelationshipType, EntityType, RelationshipStrength,
    RelationshipSummary,
};
use crate::commands::AppState;

// ============================================================================
// Entity Relationship CRUD Commands
// ============================================================================

/// Create an entity relationship
#[tauri::command]
pub fn create_entity_relationship(
    campaign_id: String,
    source_id: String,
    source_type: String,
    source_name: String,
    target_id: String,
    target_type: String,
    target_name: String,
    relationship_type: String,
    strength: Option<String>,
    description: Option<String>,
    state: State<'_, AppState>,
) -> Result<EntityRelationship, String> {
    let src_type = parse_entity_type(&source_type);
    let tgt_type = parse_entity_type(&target_type);
    let rel_type = parse_relationship_type(&relationship_type);
    let str_level = strength.map(|s| parse_relationship_strength(&s)).unwrap_or_default();

    let mut relationship = EntityRelationship::new(
        &campaign_id,
        &source_id,
        src_type,
        &source_name,
        &target_id,
        tgt_type,
        &target_name,
        rel_type,
    ).with_strength(str_level);

    if let Some(desc) = description {
        relationship = relationship.with_description(&desc);
    }

    state.relationship_manager.create_relationship(relationship)
        .map_err(|e| e.to_string())
}

/// Get a relationship by ID
#[tauri::command]
pub fn get_entity_relationship(
    campaign_id: String,
    relationship_id: String,
    state: State<'_, AppState>,
) -> Result<Option<EntityRelationship>, String> {
    Ok(state.relationship_manager.get_relationship(&campaign_id, &relationship_id))
}

/// Update a relationship
#[tauri::command]
pub fn update_entity_relationship(
    relationship: EntityRelationship,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.relationship_manager.update_relationship(relationship)
        .map_err(|e| e.to_string())
}

/// Delete a relationship
#[tauri::command]
pub fn delete_entity_relationship(
    campaign_id: String,
    relationship_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.relationship_manager.delete_relationship(&campaign_id, &relationship_id)
        .map_err(|e| e.to_string())
}

/// List all relationships for a campaign
#[tauri::command]
pub fn list_entity_relationships(
    campaign_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<RelationshipSummary>, String> {
    Ok(state.relationship_manager.list_relationships(&campaign_id))
}

// ============================================================================
// Helper Functions
// ============================================================================

fn parse_entity_type(s: &str) -> EntityType {
    match s.to_lowercase().as_str() {
        "pc" | "player" => EntityType::PC,
        "npc" => EntityType::NPC,
        "location" => EntityType::Location,
        "faction" => EntityType::Faction,
        "item" => EntityType::Item,
        "event" => EntityType::Event,
        "quest" => EntityType::Quest,
        "deity" => EntityType::Deity,
        "creature" => EntityType::Creature,
        _ => EntityType::Custom(s.to_string()),
    }
}

fn parse_relationship_type(s: &str) -> RelationshipType {
    match s.to_lowercase().as_str() {
        "ally" => RelationshipType::Ally,
        "enemy" => RelationshipType::Enemy,
        "romantic" => RelationshipType::Romantic,
        "family" => RelationshipType::Family,
        "mentor" => RelationshipType::Mentor,
        "acquaintance" => RelationshipType::Acquaintance,
        "employee" => RelationshipType::Employee,
        "business_partner" => RelationshipType::BusinessPartner,
        "patron" => RelationshipType::Patron,
        "teacher" => RelationshipType::Teacher,
        "protector" => RelationshipType::Protector,
        "member_of" => RelationshipType::MemberOf,
        "leader_of" => RelationshipType::LeaderOf,
        "allied_with" => RelationshipType::AlliedWith,
        "at_war_with" => RelationshipType::AtWarWith,
        "vassal_of" => RelationshipType::VassalOf,
        "located_at" => RelationshipType::LocatedAt,
        "connected_to" => RelationshipType::ConnectedTo,
        "part_of" => RelationshipType::PartOf,
        "controls" => RelationshipType::Controls,
        "owns" => RelationshipType::Owns,
        "seeks" => RelationshipType::Seeks,
        "created" => RelationshipType::Created,
        "destroyed" => RelationshipType::Destroyed,
        "quest_giver" => RelationshipType::QuestGiver,
        "quest_target" => RelationshipType::QuestTarget,
        "related_to" => RelationshipType::RelatedTo,
        "worships" => RelationshipType::Worships,
        "blessed_by" => RelationshipType::BlessedBy,
        "cursed_by" => RelationshipType::CursedBy,
        _ => RelationshipType::Custom(s.to_string()),
    }
}

fn parse_relationship_strength(s: &str) -> RelationshipStrength {
    match s.to_lowercase().as_str() {
        "weak" => RelationshipStrength::Weak,
        "moderate" => RelationshipStrength::Moderate,
        "strong" => RelationshipStrength::Strong,
        "unbreakable" => RelationshipStrength::Unbreakable,
        _ => {
            if let Ok(v) = s.parse::<u8>() {
                RelationshipStrength::Custom(v.min(100))
            } else {
                RelationshipStrength::Moderate
            }
        }
    }
}
