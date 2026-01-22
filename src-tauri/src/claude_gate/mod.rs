//! # Claude Gate
//!
//! **DEPRECATED**: This module is deprecated and will be removed in a future release.
//! Please migrate to the unified [`crate::gate`] module which provides:
//! - Unified `OAuthProvider` trait for Claude and Gemini
//! - `ClaudeProvider` implementation in [`crate::gate::providers::ClaudeProvider`]
//! - Shared `TokenStorage` trait with multiple backends
//! - `OAuthFlow` orchestrator for complete OAuth lifecycle
//!
//! ## Migration Guide
//!
//! Old:
//! ```rust,ignore
//! use crate::claude_gate::{ClaudeClient, FileTokenStorage};
//! let storage = FileTokenStorage::default_path()?;
//! let client = ClaudeClient::builder().with_storage(storage).build()?;
//! ```
//!
//! New:
//! ```rust,ignore
//! use crate::gate::providers::ClaudeProvider;
//! use crate::gate::storage::FileTokenStorage;
//! use crate::gate::auth::OAuthFlow;
//!
//! let provider = ClaudeProvider::new();
//! let storage = FileTokenStorage::new("~/.config/cld/auth.json")?;
//! let flow = OAuthFlow::new(provider, storage);
//! ```
//!
//! ---
//!
//! OAuth-based Anthropic API client for Rust with flexible token storage.
//!
//! This module provides:
//! - OAuth 2.0 PKCE flow for Anthropic's Claude API
//! - Flexible callback-based token storage (lazy loading)
//! - Direct programmatic API access (no HTTP server/IPC)
//! - Automatic token refresh
//! - Streaming support for real-time responses
//!
//! ## Quick Start
//!
//! ```rust,no_run
//! use crate::claude_gate::{ClaudeClient, FileTokenStorage};
//!
//! #[tokio::main]
//! async fn main() -> crate::claude_gate::Result<()> {
//!     // Use default storage (~/.config/cld/auth.json)
//!     let storage = FileTokenStorage::default_path()?;
//!     let client = ClaudeClient::builder()
//!         .with_storage(storage)
//!         .build()?;
//!
//!     // Check authentication and make a request
//!     if client.is_authenticated().await? {
//!         let response = client.messages()
//!             .model("claude-sonnet-4-20250514")
//!             .max_tokens(1024)
//!             .user_message("Hello, Claude!")
//!             .send()
//!             .await?;
//!         println!("{}", response.text());
//!     }
//!
//!     Ok(())
//! }
//! ```

#![allow(clippy::module_name_repetitions)]
#![deprecated(
    since = "0.1.0",
    note = "Use the unified `crate::gate` module instead. See module docs for migration guide."
)]

pub mod auth;
pub mod client;
pub mod error;
pub mod models;
pub mod storage;
pub mod transform;

pub use auth::{OAuthConfig, OAuthFlow, OAuthFlowState, Pkce};
pub use client::{ClaudeClient, ClaudeClientBuilder, MessagesRequest, MessagesRequestBuilder};
pub use error::{Error, Result};
pub use models::{
    ApiModel, ContentBlock, DocumentSource, ImageSource, Message, MessagesResponse, ModelsResponse,
    Role, StopReason, StreamEvent, Tool, ToolChoice, TokenInfo, Usage,
};
pub use storage::{callbacks, CallbackStorage, FileTokenStorage, MemoryTokenStorage, TokenStorage};

#[cfg(feature = "keyring")]
pub use storage::KeyringTokenStorage;
