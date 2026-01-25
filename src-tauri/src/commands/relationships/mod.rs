//! Entity Relationship Commands Module
//!
//! Commands for managing relationships between entities in a campaign,
//! including NPCs, PCs, locations, factions, items, and other entities.

pub mod crud;
pub mod graph;

// Re-export all commands using glob to include Tauri __cmd__ macros
pub use crud::*;
pub use graph::*;
