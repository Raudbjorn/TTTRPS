//! NPC Naming Commands
//!
//! Commands for loading and using cultural naming rules.

use crate::core::npc_gen::{
    CulturalNamingRules, NameStructure,
    load_yaml_file, get_names_dir,
};

// ============================================================================
// NPC Naming Commands
// ============================================================================

/// Load cultural naming rules from YAML file
#[tauri::command]
pub async fn load_naming_rules(path: String) -> Result<CulturalNamingRules, String> {
    load_yaml_file(&std::path::PathBuf::from(path))
        .await
        .map_err(|e| e.to_string())
}

/// Get the names directory path
#[tauri::command]
pub fn get_names_directory() -> String {
    get_names_dir().to_string_lossy().to_string()
}

/// Get a random structure from cultural naming rules
#[tauri::command]
pub fn get_random_name_structure(
    rules: CulturalNamingRules,
) -> NameStructure {
    let mut rng = rand::thread_rng();
    rules.random_structure(&mut rng)
}

/// Validate cultural naming rules
#[tauri::command]
pub fn validate_naming_rules(
    rules: CulturalNamingRules,
) -> Result<(), String> {
    rules.validate().map_err(|e| e.to_string())
}
