//! System Commands Module
//!
//! Commands for system information, audio volumes, and browser operations.

pub mod info;
pub mod audio;
pub mod browser;

// Re-export all commands using glob to include Tauri __cmd__ macros
pub use info::*;
pub use audio::*;
pub use browser::*;
