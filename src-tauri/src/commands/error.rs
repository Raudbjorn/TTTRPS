//! Unified Error Types for Tauri Commands
//!
//! Provides a single error type for all command operations, reducing
//! the need for repetitive `.map_err(|e| e.to_string())` patterns.

use thiserror::Error;

/// Unified error type for Tauri commands.
///
/// All command errors implement `Into<String>` for Tauri IPC compatibility.
#[derive(Debug, Error)]
pub enum CommandError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("LLM error: {0}")]
    Llm(String),

    #[error("Voice error: {0}")]
    Voice(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Authentication error: {0}")]
    Auth(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Search error: {0}")]
    Search(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("{0}")]
    Other(String),
}

// Tauri commands require Result<T, String>, so we implement Into<String>
impl From<CommandError> for String {
    fn from(e: CommandError) -> String {
        e.to_string()
    }
}

// Allow converting any error to CommandError::Other
impl From<&str> for CommandError {
    fn from(s: &str) -> Self {
        CommandError::Other(s.to_string())
    }
}

/// Result type alias for command operations
pub type CommandResult<T> = Result<T, CommandError>;
