//! Personality Styling Commands
//!
//! Commands for applying personality styling to text, NPC dialogue, and narration.

use std::sync::Arc;
use tauri::State;

use crate::commands::AppState;
use crate::core::llm::LLMClient;
use crate::core::personality::{
    ContentType, NarrationType, NPCDialogueStyler, NarrationStyleManager,
    PersonalitySettings, SceneMood, StyledContent,
    NarrativeTone, VocabularyLevel, NarrativeStyle, VerbosityLevel, GenreConvention,
};

use super::types::PersonalitySettingsRequest;

// ============================================================================
// Personality Styling Commands
// ============================================================================

/// Apply personality styling to text using LLM transformation
#[tauri::command]
pub async fn apply_personality_to_text(
    text: String,
    personality_id: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let config = state.llm_config.read()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .clone()
        .ok_or("LLM not configured")?;
    let client = LLMClient::new(config);

    state.personality_manager.apply_personality_to_text(&text, &personality_id, &client)
        .await
        .map_err(|e| e.to_string())
}

/// Set the narrator personality for a campaign
#[tauri::command]
pub fn set_narrator_personality(
    campaign_id: String,
    personality_id: Option<String>,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.set_narrator_personality(&campaign_id, personality_id);
    Ok(())
}

/// Assign a personality to an NPC
#[tauri::command]
pub fn assign_npc_personality(
    campaign_id: String,
    npc_id: String,
    personality_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.assign_npc_personality(&campaign_id, &npc_id, &personality_id);
    Ok(())
}

/// Unassign personality from an NPC
#[tauri::command]
pub fn unassign_npc_personality(
    campaign_id: String,
    npc_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.unassign_npc_personality(&campaign_id, &npc_id);
    Ok(())
}

/// Set scene mood for a campaign
#[tauri::command]
pub fn set_scene_mood(
    campaign_id: String,
    mood: Option<SceneMood>,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.personality_manager.set_scene_mood(&campaign_id, mood);
    Ok(())
}

/// Update personality settings for a campaign
#[tauri::command]
pub fn set_personality_settings(
    request: PersonalitySettingsRequest,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let settings = PersonalitySettings {
        tone: request.tone.map(|t| NarrativeTone::from_str(&t)).unwrap_or_default(),
        vocabulary: request.vocabulary.map(|v| VocabularyLevel::from_str(&v)).unwrap_or_default(),
        narrative_style: request.narrative_style.map(|n| NarrativeStyle::from_str(&n)).unwrap_or_default(),
        verbosity: request.verbosity.map(|v| VerbosityLevel::from_str(&v)).unwrap_or_default(),
        genre: request.genre.map(|g| GenreConvention::from_str(&g)).unwrap_or_default(),
        custom_patterns: request.custom_patterns.unwrap_or_default(),
        use_dialect: request.use_dialect.unwrap_or(false),
        dialect: request.dialect,
    };

    state.personality_manager.set_personality_settings(&request.campaign_id, settings);
    Ok(())
}

/// Style NPC dialogue with personality
#[tauri::command]
pub fn style_npc_dialogue(
    npc_id: String,
    campaign_id: String,
    raw_dialogue: String,
    state: State<'_, AppState>,
) -> Result<StyledContent, String> {
    let styler = NPCDialogueStyler::new(state.personality_manager.clone());
    styler.style_npc_dialogue(&npc_id, &campaign_id, &raw_dialogue)
        .map_err(|e| e.to_string())
}

/// Build NPC system prompt with personality
#[tauri::command]
pub fn build_npc_system_prompt(
    npc_id: String,
    campaign_id: String,
    additional_context: Option<String>,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let styler = NPCDialogueStyler::new(state.personality_manager.clone());
    styler.build_npc_system_prompt(&npc_id, &campaign_id, additional_context.as_deref())
        .map_err(|e| e.to_string())
}

/// Build NPC system prompt with personality - stub for compatibility
/// (Actual implementation provided by personality_manager commands below)
#[tauri::command]
pub fn build_npc_system_prompt_stub(
    npc_id: String,
    campaign_id: String,
    additional_context: Option<String>,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let manager = Arc::new(crate::core::personality::PersonalityApplicationManager::new(state.personality_store.clone()));
    let styler = crate::core::personality::NPCDialogueStyler::new(manager);
    styler.build_npc_system_prompt(&npc_id, &campaign_id, additional_context.as_deref())
        .map_err(|e| e.to_string())
}

/// Build narration prompt with personality
#[tauri::command]
pub fn build_narration_prompt(
    campaign_id: String,
    narration_type: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let nt = match narration_type.as_str() {
        "scene_description" => NarrationType::SceneDescription,
        "action" => NarrationType::Action,
        "transition" => NarrationType::Transition,
        "atmosphere" => NarrationType::Atmosphere,
        _ => NarrationType::SceneDescription,
    };

    let manager = NarrationStyleManager::new(state.personality_manager.clone());
    manager.build_narration_prompt(&campaign_id, nt)
        .map_err(|e| e.to_string())
}

/// Get the session system prompt with personality applied
#[tauri::command]
pub fn get_session_system_prompt(
    session_id: String,
    campaign_id: String,
    content_type: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let ct = match content_type.as_str() {
        "dialogue" => ContentType::Dialogue,
        "narration" => ContentType::Narration,
        "internal_thought" => ContentType::InternalThought,
        "description" => ContentType::Description,
        "action" => ContentType::Action,
        _ => ContentType::Narration,
    };

    state.personality_manager.get_session_system_prompt(&session_id, &campaign_id, ct)
        .map_err(|e| e.to_string())
}
