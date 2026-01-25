//! Personality Preview Commands
//!
//! Commands for previewing and testing personality configurations.

use tauri::State;

use crate::commands::AppState;
use crate::core::llm::LLMClient;
use crate::core::personality::{ExtendedPersonalityPreview, PersonalityPreview, PreviewResponse};

// ============================================================================
// Personality Preview Commands
// ============================================================================

/// Preview a personality
#[tauri::command]
pub fn preview_personality(
    personality_id: String,
    state: State<'_, AppState>,
) -> Result<PersonalityPreview, String> {
    state.personality_manager.preview_personality(&personality_id)
        .map_err(|e| e.to_string())
}

/// Get extended personality preview with full details
#[tauri::command]
pub fn preview_personality_extended(
    personality_id: String,
    state: State<'_, AppState>,
) -> Result<ExtendedPersonalityPreview, String> {
    state.personality_manager.preview_personality_extended(&personality_id)
        .map_err(|e| e.to_string())
}

/// Generate a preview response for personality selection UI
#[tauri::command]
pub async fn generate_personality_preview(
    personality_id: String,
    state: State<'_, AppState>,
) -> Result<PreviewResponse, String> {
    let config = state.llm_config.read().unwrap()
        .clone()
        .ok_or("LLM not configured")?;
    let client = LLMClient::new(config);

    state.personality_manager.generate_preview_response(&personality_id, &client)
        .await
        .map_err(|e| e.to_string())
}

/// Test a personality by generating a response
#[tauri::command]
pub async fn test_personality(
    personality_id: String,
    test_prompt: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let config = state.llm_config.read().unwrap()
        .clone()
        .ok_or("LLM not configured")?;
    let client = LLMClient::new(config);

    state.personality_manager.test_personality(&personality_id, &test_prompt, &client)
        .await
        .map_err(|e| e.to_string())
}
