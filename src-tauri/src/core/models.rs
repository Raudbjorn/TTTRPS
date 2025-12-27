use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// Re-export ContentChunk from chunker module
pub use crate::ingestion::chunker::ContentChunk;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceDocument {
    pub id: String,
    pub title: String,
    pub system: String,
    pub source_type: String, // "rulebook", "flavor"
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Campaign {
    pub id: String,
    pub name: String,
    pub system: String,
    pub description: Option<String>,
    pub current_date: String,
    pub notes: Vec<String>, // Or specific Note struct if serializable
    pub created_at: String,
    pub updated_at: String,
}
