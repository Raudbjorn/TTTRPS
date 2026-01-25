//! Session Notes Commands
//!
//! Commands for managing session notes including CRUD operations,
//! search, categorization, and entity linking.

use tauri::State;

use crate::commands::AppState;
use crate::core::session::notes::{
    NoteCategory, EntityType as NoteEntityType,
    SessionNote as NoteSessionNote, CategorizationRequest, CategorizationResponse,
    build_categorization_prompt, parse_categorization_response,
};

// ============================================================================
// Session Notes Commands
// ============================================================================

/// Parse a category string into a NoteCategory.
fn parse_note_category(category: &str) -> NoteCategory {
    match category {
        "general" => NoteCategory::General,
        "combat" => NoteCategory::Combat,
        "character" => NoteCategory::Character,
        "location" => NoteCategory::Location,
        "plot" => NoteCategory::Plot,
        "quest" => NoteCategory::Quest,
        "loot" => NoteCategory::Loot,
        "rules" => NoteCategory::Rules,
        "meta" => NoteCategory::Meta,
        "worldbuilding" => NoteCategory::Worldbuilding,
        "dialogue" => NoteCategory::Dialogue,
        "secret" => NoteCategory::Secret,
        _ => NoteCategory::Custom(category.to_string()),
    }
}

/// Parse an entity type string into a NoteEntityType.
fn parse_entity_type(entity_type: &str) -> NoteEntityType {
    match entity_type {
        "npc" => NoteEntityType::NPC,
        "player" => NoteEntityType::Player,
        "location" => NoteEntityType::Location,
        "item" => NoteEntityType::Item,
        "quest" => NoteEntityType::Quest,
        "session" => NoteEntityType::Session,
        "campaign" => NoteEntityType::Campaign,
        "combat" => NoteEntityType::Combat,
        _ => NoteEntityType::Custom(entity_type.to_string()),
    }
}

/// Create a new session note.
///
/// # Arguments
/// * `session_id` - The session this note belongs to
/// * `campaign_id` - The campaign this note belongs to
/// * `title` - Note title
/// * `content` - Note content
/// * `category` - Optional category (defaults to "general")
/// * `tags` - Optional list of tags
/// * `is_pinned` - Whether the note is pinned
/// * `is_private` - Whether the note is private
///
/// # Returns
/// The created note.
#[tauri::command]
pub fn create_session_note(
    session_id: String,
    campaign_id: String,
    title: String,
    content: String,
    category: Option<String>,
    tags: Option<Vec<String>>,
    is_pinned: Option<bool>,
    is_private: Option<bool>,
    state: State<'_, AppState>,
) -> Result<NoteSessionNote, String> {
    let note_category = category
        .map(|c| parse_note_category(&c))
        .unwrap_or(NoteCategory::General);

    let mut note = NoteSessionNote::new(&session_id, &campaign_id, &title, &content)
        .with_category(note_category);

    if let Some(t) = tags {
        note = note.with_tags(t);
    }

    if is_pinned.unwrap_or(false) {
        note = note.pinned();
    }

    if is_private.unwrap_or(false) {
        note = note.private();
    }

    state.session_manager.create_note(note.clone())
        .map_err(|e| e.to_string())?;

    Ok(note)
}

/// Get a session note by ID.
///
/// # Arguments
/// * `note_id` - The note ID
///
/// # Returns
/// The note if found, None otherwise.
#[tauri::command]
pub fn get_session_note(
    note_id: String,
    state: State<'_, AppState>,
) -> Result<Option<NoteSessionNote>, String> {
    Ok(state.session_manager.get_note(&note_id))
}

/// Update a session note.
///
/// # Arguments
/// * `note` - The note with updated values
///
/// # Returns
/// The updated note.
///
/// # Errors
/// If the note is not found.
#[tauri::command]
pub fn update_session_note(
    note: NoteSessionNote,
    state: State<'_, AppState>,
) -> Result<NoteSessionNote, String> {
    state.session_manager.update_note(note)
        .map_err(|e| e.to_string())
}

/// Delete a session note.
///
/// # Arguments
/// * `note_id` - The note ID to delete
///
/// # Errors
/// If the note is not found.
#[tauri::command]
pub fn delete_session_note(
    note_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.session_manager.delete_note(&note_id)
        .map_err(|e| e.to_string())
}

/// List notes for a session.
///
/// # Arguments
/// * `session_id` - The session ID
///
/// # Returns
/// List of notes for the session.
#[tauri::command]
pub fn list_session_notes(
    session_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<NoteSessionNote>, String> {
    Ok(state.session_manager.list_notes_for_session(&session_id))
}

/// Search notes by query.
///
/// # Arguments
/// * `query` - Search query
/// * `session_id` - Optional session ID to filter by
///
/// # Returns
/// List of matching notes.
#[tauri::command]
pub fn search_session_notes(
    query: String,
    session_id: Option<String>,
    state: State<'_, AppState>,
) -> Result<Vec<NoteSessionNote>, String> {
    Ok(state.session_manager.search_notes(&query, session_id.as_deref()))
}

/// Get notes by category.
///
/// # Arguments
/// * `category` - The category to filter by
/// * `session_id` - Optional session ID to filter by
///
/// # Returns
/// List of notes in the category.
#[tauri::command]
pub fn get_notes_by_category(
    category: String,
    session_id: Option<String>,
    state: State<'_, AppState>,
) -> Result<Vec<NoteSessionNote>, String> {
    let note_category = parse_note_category(&category);
    Ok(state.session_manager.get_notes_by_category(&note_category, session_id.as_deref()))
}

/// Get notes with a specific tag.
///
/// # Arguments
/// * `tag` - The tag to filter by
///
/// # Returns
/// List of notes with the tag.
#[tauri::command]
pub fn get_notes_by_tag(
    tag: String,
    state: State<'_, AppState>,
) -> Result<Vec<NoteSessionNote>, String> {
    Ok(state.session_manager.get_notes_by_tag(&tag))
}

/// AI categorize a note.
///
/// Uses the LLM to suggest an appropriate category for a note
/// based on its title and content.
///
/// # Arguments
/// * `title` - Note title
/// * `content` - Note content
///
/// # Returns
/// Categorization response with suggested category and confidence.
///
/// # Errors
/// If LLM is not configured or categorization fails.
#[tauri::command]
pub async fn categorize_note_ai(
    title: String,
    content: String,
    state: State<'_, AppState>,
) -> Result<CategorizationResponse, String> {
    // Build the categorization prompt
    let request = CategorizationRequest {
        title,
        content,
        available_categories: vec![
            "General".to_string(),
            "Combat".to_string(),
            "Character".to_string(),
            "Location".to_string(),
            "Plot".to_string(),
            "Quest".to_string(),
            "Loot".to_string(),
            "Rules".to_string(),
            "Worldbuilding".to_string(),
            "Dialogue".to_string(),
            "Secret".to_string(),
        ],
    };

    let prompt = build_categorization_prompt(&request);

    // Call LLM
    let config = state.llm_config.read().unwrap().clone()
        .ok_or("LLM not configured")?;
    let client = crate::core::llm::LLMClient::new(config);

    let llm_request = crate::core::llm::ChatRequest {
        messages: vec![crate::core::llm::ChatMessage {
            role: crate::core::llm::MessageRole::User,
            content: prompt,
            images: None,
            name: None,
            tool_calls: None,
            tool_call_id: None,
        }],
        system_prompt: Some("You are a TTRPG session note analyzer. Respond only with valid JSON.".to_string()),
        temperature: Some(0.3),
        max_tokens: Some(500),
        provider: None,
        tools: None,
        tool_choice: None,
    };

    let response = client.chat(llm_request).await
        .map_err(|e| e.to_string())?;

    // Parse the response
    parse_categorization_response(&response.content)
}

/// Link an entity to a note.
///
/// # Arguments
/// * `note_id` - The note ID
/// * `entity_type` - Type of entity (npc, player, location, item, quest, session, campaign, combat)
/// * `entity_id` - The entity ID
/// * `entity_name` - Display name of the entity
///
/// # Errors
/// If the note is not found.
#[tauri::command]
pub fn link_entity_to_note(
    note_id: String,
    entity_type: String,
    entity_id: String,
    entity_name: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let etype = parse_entity_type(&entity_type);
    state.session_manager.link_entity_to_note(&note_id, etype, &entity_id, &entity_name)
        .map_err(|e| e.to_string())
}

/// Unlink an entity from a note.
///
/// # Arguments
/// * `note_id` - The note ID
/// * `entity_id` - The entity ID to unlink
///
/// # Errors
/// If the note is not found.
#[tauri::command]
pub fn unlink_entity_from_note(
    note_id: String,
    entity_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.session_manager.unlink_entity_from_note(&note_id, &entity_id)
        .map_err(|e| e.to_string())
}
