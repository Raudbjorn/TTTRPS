//! NPC Naming Commands
//!
//! Commands for loading and using cultural naming rules.

use std::path::PathBuf;

use crate::core::npc_gen::{
    CulturalNamingRules, NameStructure,
    load_yaml_file, get_names_dir,
};

// ============================================================================
// Path Validation
// ============================================================================

/// Validate that a path is within the names directory (prevents path traversal)
fn validate_names_path(path: &str) -> Result<PathBuf, String> {
    let names_dir = get_names_dir();
    let canonical_base = names_dir.canonicalize()
        .map_err(|e| format!("Failed to canonicalize names directory: {}", e))?;

    let requested_path = PathBuf::from(path);

    // If path is relative, resolve it against the names directory
    let full_path = if requested_path.is_relative() {
        names_dir.join(&requested_path)
    } else {
        requested_path
    };

    // Canonicalize to resolve any .. or symlinks
    let canonical_path = full_path.canonicalize()
        .map_err(|e| format!("Invalid naming rules path '{}': {}", path, e))?;

    // Verify the canonical path is within the names directory
    if !canonical_path.starts_with(&canonical_base) {
        return Err(format!(
            "Path traversal denied: '{}' is outside names directory",
            path
        ));
    }

    Ok(canonical_path)
}

// ============================================================================
// NPC Naming Commands
// ============================================================================

/// Load cultural naming rules from YAML file
///
/// The path must be within the names directory to prevent path traversal attacks.
#[tauri::command]
pub async fn load_naming_rules(path: String) -> Result<CulturalNamingRules, String> {
    let validated_path = validate_names_path(&path)?;
    load_yaml_file(&validated_path)
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
