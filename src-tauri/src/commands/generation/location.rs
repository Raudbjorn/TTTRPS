//! Location Generation Commands
//!
//! Commands for procedural location generation for TTRPG campaigns.

use tauri::State;

use crate::commands::AppState;
use crate::core::location_gen::{
    LocationGenerator, LocationGenerationOptions, Location, Difficulty,
};

// ============================================================================
// Location Generation Commands
// ============================================================================

/// Generate a new location using procedural templates or AI
#[tauri::command]
pub async fn generate_location(
    location_type: String,
    campaign_id: Option<String>,
    options: Option<LocationGenerationOptions>,
    state: State<'_, AppState>,
) -> Result<Location, String> {
    let mut gen_options = options.unwrap_or_default();
    gen_options.location_type = Some(location_type);
    gen_options.campaign_id = campaign_id;

    if gen_options.use_ai {
        // Use AI-enhanced generation if LLM is configured
        let llm_config = state.llm_config.read()
            .map_err(|e| e.to_string())?
            .clone();

        if let Some(config) = llm_config {
            let generator = LocationGenerator::with_llm(config);
            generator.generate_detailed(&gen_options).await
                .map_err(|e| e.to_string())
        } else {
            // Fall back to quick generation if no LLM configured
            let generator = LocationGenerator::new();
            Ok(generator.generate_quick(&gen_options))
        }
    } else {
        // Use quick procedural generation
        let generator = LocationGenerator::new();
        Ok(generator.generate_quick(&gen_options))
    }
}

/// Generate a location quickly using procedural templates only
#[tauri::command]
pub fn generate_location_quick(
    location_type: String,
    campaign_id: Option<String>,
    name: Option<String>,
    theme: Option<String>,
    include_inhabitants: Option<bool>,
    include_secrets: Option<bool>,
    include_encounters: Option<bool>,
    include_loot: Option<bool>,
    danger_level: Option<String>,
) -> Location {
    let options = LocationGenerationOptions {
        location_type: Some(location_type),
        name,
        campaign_id,
        theme,
        include_inhabitants: include_inhabitants.unwrap_or(true),
        include_secrets: include_secrets.unwrap_or(true),
        include_encounters: include_encounters.unwrap_or(true),
        include_loot: include_loot.unwrap_or(true),
        danger_level: danger_level.map(|d| parse_difficulty(&d)),
        ..Default::default()
    };

    let generator = LocationGenerator::new();
    generator.generate_quick(&options)
}

// NOTE: get_location_types and LocationTypeInfo are already defined in
// commands/location/types.rs - no need to duplicate here

// ============================================================================
// Helper Functions
// ============================================================================

fn parse_difficulty(s: &str) -> Difficulty {
    match s.to_lowercase().as_str() {
        "easy" => Difficulty::Easy,
        "medium" => Difficulty::Medium,
        "hard" => Difficulty::Hard,
        "very_hard" | "veryhard" => Difficulty::VeryHard,
        "nearly_impossible" | "nearlyimpossible" => Difficulty::NearlyImpossible,
        _ => Difficulty::Medium,
    }
}
