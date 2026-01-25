//! NPC Dialect Commands
//!
//! Commands for loading and applying dialect transformations.

use crate::core::npc_gen::{
    DialectDefinition, DialectTransformer, DialectTransformResult, Intensity,
    load_yaml_file, get_dialects_dir,
};

// ============================================================================
// NPC Dialect Commands
// ============================================================================

/// Load a dialect definition from YAML file
#[tauri::command]
pub async fn load_dialect(path: String) -> Result<DialectDefinition, String> {
    load_yaml_file(&std::path::PathBuf::from(path))
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
