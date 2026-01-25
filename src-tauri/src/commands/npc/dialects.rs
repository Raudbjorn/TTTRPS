//! NPC Dialect Commands
//!
//! Commands for loading and applying dialect transformations.

use std::path::PathBuf;

use crate::core::npc_gen::{
    DialectDefinition, DialectTransformer, DialectTransformResult, Intensity,
    load_yaml_file, get_dialects_dir,
};

// ============================================================================
// Path Validation
// ============================================================================

/// Validate that a path is within the dialects directory (prevents path traversal)
fn validate_dialect_path(path: &str) -> Result<PathBuf, String> {
    let dialects_dir = get_dialects_dir();
    let canonical_base = dialects_dir.canonicalize()
        .map_err(|e| format!("Failed to canonicalize dialects directory: {}", e))?;

    let requested_path = PathBuf::from(path);

    // If path is relative, resolve it against the dialects directory
    let full_path = if requested_path.is_relative() {
        dialects_dir.join(&requested_path)
    } else {
        requested_path
    };

    // Canonicalize to resolve any .. or symlinks
    let canonical_path = full_path.canonicalize()
        .map_err(|e| format!("Invalid dialect path '{}': {}", path, e))?;

    // Verify the canonical path is within the dialects directory
    if !canonical_path.starts_with(&canonical_base) {
        return Err(format!(
            "Path traversal denied: '{}' is outside dialects directory",
            path
        ));
    }

    Ok(canonical_path)
}

// ============================================================================
// NPC Dialect Commands
// ============================================================================

/// Load a dialect definition from YAML file
///
/// The path must be within the dialects directory to prevent path traversal attacks.
#[tauri::command]
pub async fn load_dialect(path: String) -> Result<DialectDefinition, String> {
    let validated_path = validate_dialect_path(&path)?;
    load_yaml_file(&validated_path)
        .await
        .map_err(|e| e.to_string())
}

/// Get the dialects directory path
#[tauri::command]
pub fn get_dialects_directory() -> String {
    get_dialects_dir().to_string_lossy().to_string()
}

/// Transform text using a dialect
#[tauri::command]
pub fn apply_dialect(
    dialect: DialectDefinition,
    text: String,
    intensity: String,
) -> Result<DialectTransformResult, String> {
    let intensity = Intensity::from_str(&intensity);
    let mut rng = rand::thread_rng();
    let transformer = DialectTransformer::new(dialect).with_intensity(intensity);
    Ok(transformer.transform(&text, &mut rng))
}
