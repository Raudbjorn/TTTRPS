//! Audio Commands
//!
//! Commands for audio volume settings and SFX categories.

use crate::core::audio::AudioVolumes;

/// Get current audio volume settings
///
/// Note: Audio playback uses rodio which requires the OutputStream to stay
/// on the same thread. For Tauri, we handle this by creating the audio player
/// on-demand in the main thread context.
#[tauri::command]
pub fn get_audio_volumes() -> AudioVolumes {
    AudioVolumes::default()
}

/// Get available SFX categories
#[tauri::command]
pub fn get_sfx_categories() -> Vec<String> {
    crate::core::audio::get_sfx_categories()
}
