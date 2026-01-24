//! Shared Request/Response Types for Tauri Commands
//!
//! Common DTOs used across multiple command modules.

use serde::{Deserialize, Serialize};

// ============================================================================
// Chat Types
// ============================================================================

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequestPayload {
    pub message: String,
    pub system_prompt: Option<String>,
    pub personality_id: Option<String>,
    pub context: Option<Vec<String>>,
    /// Enable RAG mode to route through Meilisearch Chat
    #[serde(default)]
    pub use_rag: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponsePayload {
    pub content: String,
    pub model: String,
    pub input_tokens: Option<u32>,
    pub output_tokens: Option<u32>,
}

// ============================================================================
// LLM Settings Types
// ============================================================================

#[derive(Debug, Serialize, Deserialize)]
pub struct LLMSettings {
    pub provider: String,
    pub api_key: Option<String>,
    pub host: Option<String>,
    pub model: String,
    pub embedding_model: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthStatus {
    pub provider: String,
    pub healthy: bool,
    pub message: String,
}

// ============================================================================
// Utility Functions
// ============================================================================

/// Helper to serialize an enum value to its string representation
pub fn serialize_enum_to_string<T: serde::Serialize>(value: &T) -> String {
    serde_json::to_string(value)
        .map(|s| s.trim_matches('"').to_string())
        .unwrap_or_default()
}
