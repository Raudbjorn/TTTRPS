//! Voice Commands Module
//!
//! Commands for voice synthesis, provider management, voice presets,
//! voice profiles, queue management, and audio cache.

pub mod config;
pub mod providers;
pub mod synthesis;
pub mod queue;
pub mod presets;
pub mod profiles;
pub mod cache;
pub mod synthesis_queue;
pub mod speech;

// Re-export all commands using glob to include Tauri __cmd__ macros
// Note: config module name conflicts with llm::config at top-level, but
// this is handled via #[allow(ambiguous_glob_reexports)] in commands/mod.rs
pub use config::*;
pub use providers::*;
pub use synthesis::*;
pub use queue::*;
pub use presets::*;
pub use profiles::*;
pub use cache::*;
pub use synthesis_queue::*;
pub use speech::*;
