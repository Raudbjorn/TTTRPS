//! Location Commands Module
//!
//! Commands for location management including CRUD operations,
//! connections, inhabitants, secrets, encounters, and map references.

pub mod types;
pub mod crud;
pub mod connections;
pub mod details;

// Re-export all commands using glob to include Tauri __cmd__ macros
pub use types::*;
pub use crud::*;
pub use connections::*;
pub use details::*;
