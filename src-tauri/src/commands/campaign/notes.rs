//! Campaign Notes Commands
//!
//! Commands for managing campaign notes and generating campaign cover images.

use tauri::State;

use crate::commands::AppState;
use crate::core::campaign_manager::SessionNote;

// ============================================================================
// Campaign Notes Commands
// ============================================================================

/// Add a note to a campaign.
#[tauri::command]
pub fn add_campaign_note(
    campaign_id: String,
    content: String,
    tags: Vec<String>,
    session_number: Option<u32>,
    state: State<'_, AppState>,
) -> Result<SessionNote, String> {
    Ok(state.campaign_manager.add_note(&campaign_id, &content, tags, session_number))
}

/// Get all notes for a campaign.
#[tauri::command]
pub fn get_campaign_notes(campaign_id: String, state: State<'_, AppState>) -> Result<Vec<SessionNote>, String> {
    Ok(state.campaign_manager.get_notes(&campaign_id))
}

/// Search campaign notes with optional tag filtering.
#[tauri::command]
pub fn search_campaign_notes(
    campaign_id: String,
    query: String,
    tags: Option<Vec<String>>,
    state: State<'_, AppState>,
) -> Result<Vec<SessionNote>, String> {
    let tags_ref = tags.as_deref();
    Ok(state.campaign_manager.search_notes(&campaign_id, &query, tags_ref))
}

/// Delete a campaign note by ID.
#[tauri::command]
pub fn delete_campaign_note(
    campaign_id: String,
    note_id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.campaign_manager.delete_note(&campaign_id, &note_id)
        .map_err(|e| e.to_string())
}

/// Generate an SVG cover image for a campaign.
///
/// Returns a base64-encoded data URI of the generated SVG.
#[tauri::command]
pub fn generate_campaign_cover(
    campaign_id: String,
    title: String,
) -> String {
    use base64::Engine;

    // Deterministic colors based on ID using FNV-1a hash (stable across Rust versions)
    // FNV-1a is simple, fast, and has good distribution for short strings
    fn fnv1a_hash(data: &[u8]) -> u64 {
        const FNV_OFFSET_BASIS: u64 = 0xcbf29ce484222325;
        const FNV_PRIME: u64 = 0x100000001b3;
        let mut hash = FNV_OFFSET_BASIS;
        for byte in data {
            hash ^= *byte as u64;
            hash = hash.wrapping_mul(FNV_PRIME);
        }
        hash
    }

    let h1 = fnv1a_hash(campaign_id.as_bytes());
    let h2 = !h1;

    let c1 = format!("#{:06x}", h1 & 0xFFFFFF);
    let c2 = format!("#{:06x}", h2 & 0xFFFFFF);

    // Initials
    let initials: String = title.split_whitespace()
        .take(2)
        .filter_map(|w| w.chars().next())
        .collect::<String>()
        .to_uppercase();

    // SVG
    let svg = format!(
        r#"<svg width="400" height="200" viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:{};stop-opacity:1" />
                    <stop offset="100%" style="stop-color:{};stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect width="100%" height="100%" fill="url(#g)" />
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-size="80" fill="rgba(255,255,255,0.8)" font-weight="bold">{}</text>
        </svg>"#,
        c1, c2, initials
    );

    let b64 = base64::engine::general_purpose::STANDARD.encode(svg);
    format!("data:image/svg+xml;base64,{}", b64)
}
