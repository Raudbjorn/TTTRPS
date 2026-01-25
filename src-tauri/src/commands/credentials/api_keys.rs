//! API Key Commands
//!
//! Commands for storing, retrieving, and managing API keys.

use tauri::State;
use crate::commands::AppState;

/// Save an API key for a provider
///
/// Stores the API key securely in the system keyring.
#[tauri::command]
pub fn save_api_key(
    provider: String,
    api_key: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let key_name = format!("{}_api_key", provider);
    state.credentials.store_secret(&key_name, &api_key)
        .map_err(|e| e.to_string())
}

/// Get an API key for a provider
///
/// Retrieves the API key from the system keyring.
/// Returns None if no key is stored for this provider.
#[tauri::command]
pub fn get_api_key(provider: String, state: State<'_, AppState>) -> Result<Option<String>, String> {
    let key_name = format!("{}_api_key", provider);
    match state.credentials.get_secret(&key_name) {
        Ok(key) => Ok(Some(key)),
        Err(crate::core::credentials::CredentialError::NotFound(_)) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

/// Delete an API key for a provider
///
/// Removes the API key from the system keyring.
#[tauri::command]
pub fn delete_api_key(provider: String, state: State<'_, AppState>) -> Result<(), String> {
    let key_name = format!("{}_api_key", provider);
    state.credentials.delete_secret(&key_name)
        .map_err(|e| e.to_string())
}

/// List all providers that have stored API keys
#[tauri::command]
pub fn list_stored_providers(state: State<'_, AppState>) -> Vec<String> {
    state.credentials.list_llm_providers()
}
