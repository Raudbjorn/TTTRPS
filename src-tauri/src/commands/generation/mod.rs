//! Generation Commands Module
//!
//! Commands for procedural generation of characters, locations, and other
//! TTRPG content.

pub mod character;
pub mod location;

// Re-export all commands using glob to include Tauri __cmd__ macros
pub use character::*;
pub use location::*;
