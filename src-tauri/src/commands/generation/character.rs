//! Character Generation Commands
//!
//! Commands for procedural character generation across different TTRPG systems.

use crate::core::character_gen::{CharacterGenerator, GenerationOptions, Character, SystemInfo};

// ============================================================================
// Character Generation Commands
// ============================================================================

/// Generate a character for a specific game system and level
#[tauri::command]
pub fn generate_character(
    system: String,
    level: u32,
    genre: Option<String>,
) -> Result<Character, String> {
    let options = GenerationOptions {
        system: Some(system),
        level: Some(level),
        theme: genre,
        ..Default::default()
    };
    let character = CharacterGenerator::generate(&options).map_err(|e| e.to_string())?;
    Ok(character)
}

/// Get list of supported game systems
#[tauri::command]
pub fn get_supported_systems() -> Vec<String> {
    CharacterGenerator::supported_systems()
}

/// List detailed information about all supported systems
#[tauri::command]
pub fn list_system_info() -> Vec<SystemInfo> {
    CharacterGenerator::list_system_info()
}

/// Get detailed information about a specific game system
#[tauri::command]
pub fn get_system_info(system: String) -> Option<SystemInfo> {
    CharacterGenerator::get_system_info(&system)
}

/// Generate a character with advanced options
#[tauri::command]
pub fn generate_character_advanced(options: GenerationOptions) -> Result<Character, String> {
    CharacterGenerator::generate(&options).map_err(|e| e.to_string())
}
