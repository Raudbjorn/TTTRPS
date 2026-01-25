//! Personality Commands Module
//!
//! Commands for personality profiles, templates, blending, context detection,
//! and styling. Organized into focused submodules for maintainability.

pub mod types;
pub mod active;
pub mod context;
pub mod styling;
pub mod preview;
pub mod templates;
pub mod blending;
pub mod contextual;

// Re-export types
pub use types::*;

// Re-export all commands using glob to include Tauri __cmd__ macros
pub use active::*;
pub use context::*;
pub use styling::*;
pub use preview::*;
pub use templates::*;
pub use blending::*;
pub use contextual::*;
