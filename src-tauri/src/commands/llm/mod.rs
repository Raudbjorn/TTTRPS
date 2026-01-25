//! LLM Commands Module
//!
//! Tauri IPC commands for LLM operations including:
//! - Configuration (configure_llm, get_llm_config)
//! - Chat (chat, stream_chat)
//! - Streaming management (cancel_stream, get_active_streams)
//! - Model listing (list_ollama_models, list_claude_models, etc.)
//! - Router operations (get_router_stats, get_router_health, etc.)
//! - Model selection (get_model_selection, set_model_override)

pub mod types;
pub mod config;
pub mod chat;
pub mod streaming;
pub mod models;
pub mod router;
pub mod model_selector;

// Re-export all commands and types using glob pattern for Tauri __cmd__ macros
pub use types::*;
pub use config::*;
pub use chat::*;
pub use streaming::*;
pub use models::*;
pub use router::*;
pub use model_selector::*;
