//! Voice Commands Module
//!
//! Commands for voice synthesis, provider management, voice presets,
//! voice profiles, queue management, and audio cache.
//!
//! NOTE: This module is partially extracted. Some commands remain in commands_legacy.rs
//! and will be migrated in subsequent iterations.

pub mod config;
pub mod providers;
pub mod synthesis;
pub mod queue;

// Placeholder modules for future extraction
mod presets;
mod profiles;
mod cache;

// Re-export extracted commands
pub use config::{configure_voice, get_voice_config, detect_voice_providers, list_all_voices};
pub use providers::{
    check_voice_provider_installations, check_voice_provider_status,
    install_voice_provider, list_downloadable_piper_voices,
    get_popular_piper_voices, download_piper_voice,
};
pub use synthesis::{
    play_tts, list_openai_voices, list_openai_tts_models,
    list_elevenlabs_voices, list_available_voices,
};
pub use queue::{queue_voice, get_voice_queue, cancel_voice};
