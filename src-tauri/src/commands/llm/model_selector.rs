//! Model Selection Commands
//!
//! Commands for intelligent model selection based on task complexity.

use crate::core::llm::{model_selector, ModelSelection, TaskComplexity};

// ============================================================================
// Commands
// ============================================================================

/// Get the recommended model selection for the current plan configuration.
///
/// Returns a ModelSelection with the recommended model, plan info, and selection reason.
/// Uses medium task complexity as the default.
#[tauri::command]
pub async fn get_model_selection() -> Result<ModelSelection, String> {
    let selector = model_selector();
    selector.get_selection(TaskComplexity::Medium).await
}

/// Get the recommended model selection with complexity auto-detected from the prompt.
///
/// Analyzes the prompt for keywords that indicate task complexity (light/medium/heavy)
/// and returns the appropriate model recommendation.
#[tauri::command]
pub async fn get_model_selection_for_prompt(prompt: String) -> Result<ModelSelection, String> {
    let selector = model_selector();
    selector.get_selection_for_prompt(&prompt).await
}

/// Set a manual model override that bypasses automatic selection.
///
/// Pass `None` to clear the override and return to automatic selection.
/// Pass `Some("claude-opus-4-20250514")` or similar to force a specific model.
#[tauri::command]
pub async fn set_model_override(model: Option<String>) -> Result<(), String> {
    let selector = model_selector();
    selector.set_override(model).await;
    Ok(())
}
