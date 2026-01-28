//! NPC Commands Module
//!
//! Commands for NPC management, conversations, vocabulary, naming, dialects, and indexing.

pub mod generation;
pub mod crud;
pub mod conversations;
pub mod vocabulary;
pub mod naming;
pub mod dialects;
pub mod indexes;

// Re-export all commands using glob to include Tauri __cmd__ macros
pub use generation::*;
pub use crud::*;
pub use conversations::*;
pub use vocabulary::*;
pub use naming::*;
pub use dialects::*;
pub use indexes::*;
