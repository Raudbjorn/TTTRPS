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

/// LLM Settings for configuration.
/// Note: Custom Debug impl to avoid exposing api_key in logs.
#[derive(Serialize, Deserialize)]
pub struct LLMSettings {
    pub provider: String,
    pub api_key: Option<String>,
    pub host: Option<String>,
    pub model: String,
    pub embedding_model: Option<String>,
}

impl std::fmt::Debug for LLMSettings {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("LLMSettings")
            .field("provider", &self.provider)
            .field("api_key", &self.api_key.as_ref().map(|_| "<REDACTED>"))
            .field("host", &self.host)
            .field("model", &self.model)
            .field("embedding_model", &self.embedding_model)
            .finish()
    }
}

impl From<&crate::core::llm::LLMConfig> for LLMSettings {
    fn from(config: &crate::core::llm::LLMConfig) -> Self {
        use crate::core::llm::LLMConfig;

        match config {
            LLMConfig::Ollama { host, model } => LLMSettings {
                provider: "ollama".to_string(),
                api_key: None,
                host: Some(host.clone()),
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Claude { model, .. } => LLMSettings {
                provider: "claude".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Google { model, .. } => LLMSettings {
                provider: "google".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::OpenAI { model, .. } => LLMSettings {
                provider: "openai".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::OpenRouter { model, .. } => LLMSettings {
                provider: "openrouter".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Mistral { model, .. } => LLMSettings {
                provider: "mistral".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Groq { model, .. } => LLMSettings {
                provider: "groq".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Together { model, .. } => LLMSettings {
                provider: "together".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Cohere { model, .. } => LLMSettings {
                provider: "cohere".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::DeepSeek { model, .. } => LLMSettings {
                provider: "deepseek".to_string(),
                api_key: Some("********".to_string()),
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Gemini { model, .. } => LLMSettings {
                provider: "gemini".to_string(),
                api_key: None, // No API key needed - uses OAuth
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Meilisearch { host, model, .. } => LLMSettings {
                provider: "meilisearch".to_string(),
                api_key: None,
                host: Some(host.clone()),
                model: model.clone(),
                embedding_model: None,
            },
            LLMConfig::Copilot { model, .. } => LLMSettings {
                provider: "copilot".to_string(),
                api_key: None, // No API key needed - uses OAuth Device Code flow
                host: None,
                model: model.clone(),
                embedding_model: None,
            },
        }
    }
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
