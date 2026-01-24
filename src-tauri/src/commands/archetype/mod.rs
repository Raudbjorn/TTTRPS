//! Archetype Registry Commands
//!
//! Commands for managing character archetypes, vocabulary banks,
//! setting packs, and archetype resolution.

pub mod types;
pub mod crud;
pub mod vocabulary;
pub mod setting_packs;
pub mod resolution;

// Re-export types
pub use types::*;

// Re-export commands
pub use crud::*;
pub use vocabulary::*;
pub use setting_packs::*;
pub use resolution::*;
