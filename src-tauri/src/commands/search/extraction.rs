//! Extraction Settings Commands
//!
//! Commands for managing document extraction settings and checking OCR availability.

use tauri::State;

use crate::commands::AppState;
use crate::ingestion::{ExtractionSettings, SupportedFormats};
use super::types::{ExtractionPreset, OcrAvailability};

// ============================================================================
// Extraction Settings Commands
// ============================================================================

/// Get current extraction settings
#[tauri::command]
pub async fn get_extraction_settings(
    state: State<'_, AppState>,
) -> Result<ExtractionSettings, String> {
    // Try to load from state or return defaults
    let settings_guard = state.extraction_settings.read().await;
    Ok(settings_guard.clone())
}

/// Save extraction settings
#[tauri::command]
pub async fn save_extraction_settings(
    settings: ExtractionSettings,
    state: State<'_, AppState>,
) -> Result<(), String> {
    // Validate settings
    settings.validate()?;

    // Save to state
    let mut settings_guard = state.extraction_settings.write().await;
    *settings_guard = settings;

    log::info!("Extraction settings saved");
    Ok(())
}

/// Get supported file formats for extraction
#[tauri::command]
pub fn get_supported_formats() -> SupportedFormats {
    SupportedFormats::get_all()
}

/// Get extraction settings presets
#[tauri::command]
pub fn get_extraction_presets() -> Vec<ExtractionPreset> {
    vec![
        ExtractionPreset {
            name: "Default".to_string(),
            description: "Balanced settings for most documents".to_string(),
            settings: ExtractionSettings::default(),
        },
        ExtractionPreset {
            name: "TTRPG Rulebooks".to_string(),
            description: "Optimized for tabletop RPG rulebooks and sourcebooks".to_string(),
            settings: ExtractionSettings::for_rulebooks(),
        },
        ExtractionPreset {
            name: "Scanned Documents".to_string(),
            description: "For scanned PDFs requiring OCR processing".to_string(),
            settings: ExtractionSettings::for_scanned_documents(),
        },
        ExtractionPreset {
            name: "Quick Extract".to_string(),
            description: "Fast extraction with minimal processing".to_string(),
            settings: ExtractionSettings::quick(),
        },
    ]
}

/// Check if OCR is available on the system
#[tauri::command]
pub async fn check_ocr_availability() -> OcrAvailability {
    use tokio::process::Command;

    let tesseract_available = Command::new("tesseract")
        .arg("--version")
        .output()
        .await
        .map(|o| o.status.success())
        .unwrap_or(false);

    let pdftoppm_available = Command::new("pdftoppm")
        .arg("-v")
        .output()
        .await
        .map(|o| o.status.success())
        .unwrap_or(false);

    // Get installed tesseract languages
    let languages = if tesseract_available {
        Command::new("tesseract")
            .arg("--list-langs")
            .output()
            .await
            .ok()
            .map(|o| {
                String::from_utf8_lossy(&o.stdout)
                    .lines()
                    .skip(1) // Skip header line
                    .map(|s| s.to_string())
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default()
    } else {
        Vec::new()
    };

    OcrAvailability {
        tesseract_installed: tesseract_available,
        pdftoppm_installed: pdftoppm_available,
        available_languages: languages,
        external_ocr_ready: tesseract_available && pdftoppm_available,
    }
}
