//! Search and Library Commands Module
//!
//! Commands for search, document ingestion, library management,
//! TTRPG document queries, search analytics, embeddings configuration,
//! and extraction settings.

pub mod query;
pub mod suggestions;
pub mod library;
pub mod ingestion;
pub mod extraction;
pub mod ttrpg_docs;
pub mod embeddings;
pub mod analytics;
pub mod meilisearch;
pub mod types;

// Re-export all commands using glob to include Tauri __cmd__ macros
pub use query::*;
pub use suggestions::*;
pub use library::*;
pub use ingestion::*;
pub use extraction::*;
pub use ttrpg_docs::*;
pub use embeddings::*;
pub use analytics::*;
pub use meilisearch::*;
pub use types::*;
