//! # Gate - Unified OAuth Token Management
//!
//! This module provides a unified interface for OAuth token storage and management
//! across multiple LLM providers (Claude, Gemini, etc.).
//!
//! ## Core Types
//!
//! - [`TokenInfo`] - OAuth token data with expiry and composite project ID support
//! - [`Error`] / [`AuthError`] - Comprehensive error taxonomy
//!
//! ## Storage Backends
//!
//! - [`FileTokenStorage`] - File-based storage with secure permissions
//! - [`MemoryTokenStorage`] - In-memory storage for testing
//! - [`CallbackStorage`] - Custom storage via callbacks
//! - [`KeyringTokenStorage`] - System keyring storage (feature-gated)
//!
//! ## Authentication Utilities
//!
//! - [`auth::Pkce`] - PKCE generation for OAuth flows
//! - [`auth::OAuthConfig`] - Provider-specific OAuth configuration
//! - [`auth::OAuthFlowState`] - OAuth flow state management
//!
//! ## OAuth Providers
//!
//! Provider-specific OAuth implementations:
//!
//! - [`providers::ClaudeProvider`] - Anthropic OAuth (JSON-encoded, PKCE-only)
//! - [`providers::GeminiProvider`] - Google Cloud Code OAuth (form-encoded)
//!
//! ## Security
//!
//! - File storage uses 0600 permissions on Unix
//! - Tokens are never logged
//! - All implementations are thread-safe (`Send + Sync`)
//!
//! ## Example
//!
//! ```rust,ignore
//! use ttrpg_assistant::gate::{
//!     TokenInfo, TokenStorage, FileTokenStorage,
//!     auth::{OAuthConfig, OAuthFlowState},
//! };
//!
//! // Create storage
//! let storage = FileTokenStorage::default_path()?;
//!
//! // Get provider configuration
//! let config = OAuthConfig::claude();
//!
//! // Start OAuth flow
//! let flow_state = OAuthFlowState::new();
//!
//! // After successful OAuth, create and save token
//! let token = TokenInfo::new(access_token, refresh_token, expires_in);
//! storage.save("anthropic", &token).await?;
//!
//! // Later, load and check token
//! if let Some(token) = storage.load("anthropic").await? {
//!     if token.needs_refresh() {
//!         // Refresh the token...
//!     }
//! }
//! ```
//!
//! ## Using Providers
//!
//! ```rust,ignore
//! use ttrpg_assistant::gate::providers::{OAuthProvider, ClaudeProvider, GeminiProvider};
//! use ttrpg_assistant::gate::auth::Pkce;
//!
//! // Create provider-specific implementations
//! let claude = ClaudeProvider::new();
//! let gemini = GeminiProvider::new();
//!
//! // Build authorization URLs with provider-specific parameters
//! let pkce = Pkce::generate();
//! let claude_url = claude.build_auth_url(&pkce, "state");  // Includes code=true
//! let gemini_url = gemini.build_auth_url(&pkce, "state");  // Includes access_type=offline
//!
//! // Exchange codes for tokens
//! let token = claude.exchange_code("code", &pkce.verifier).await?;
//! ```

pub mod auth;
pub mod error;
pub mod providers;
pub mod storage;
pub mod token;

// Re-export core error types
pub use error::{AuthError, Error, Result};

// Re-export storage types
pub use storage::{
    CallbackStorage, EnvSource, FileSource, FileTokenStorage, MemoryTokenStorage, TokenStorage,
};

// Re-export token type
pub use token::TokenInfo;

// Re-export auth types at module root for convenience
pub use auth::{generate_state, OAuthConfig, OAuthConfigBuilder, OAuthFlow, OAuthFlowState, Pkce};

// Re-export provider trait and implementations
pub use providers::{ClaudeProvider, GeminiProvider, OAuthProvider};

// Re-export keyring storage when feature is enabled
#[cfg(feature = "keyring")]
pub use storage::KeyringTokenStorage;

// ============================================================================
// Convenience Type Aliases
// ============================================================================

/// Claude Gate client using file-based token storage.
///
/// This type alias provides a convenient way to create a Claude OAuth flow
/// with the commonly used file storage backend.
///
/// # Example
///
/// ```rust,ignore
/// use ttrpg_assistant::gate::{ClaudeFileGate, FileTokenStorage};
///
/// let storage = FileTokenStorage::default_path()?;
/// let gate = ClaudeFileGate::new(storage);
/// ```
pub type ClaudeFileGate = OAuthFlow<FileTokenStorage>;

/// Claude Gate client using memory-based token storage.
///
/// Useful for testing and ephemeral sessions.
///
/// # Example
///
/// ```rust,ignore
/// use ttrpg_assistant::gate::{ClaudeMemoryGate, MemoryTokenStorage};
///
/// let storage = MemoryTokenStorage::new();
/// let gate = ClaudeMemoryGate::new(storage);
/// ```
pub type ClaudeMemoryGate = OAuthFlow<MemoryTokenStorage>;

/// Gemini Gate client using file-based token storage.
///
/// This type alias provides a convenient way to create a Gemini OAuth flow
/// with the commonly used file storage backend.
///
/// # Example
///
/// ```rust,ignore
/// use ttrpg_assistant::gate::{GeminiFileGate, FileTokenStorage};
///
/// let storage = FileTokenStorage::default_path()?;
/// let gate = GeminiFileGate::new(storage);
/// ```
pub type GeminiFileGate = OAuthFlow<FileTokenStorage>;

/// Gemini Gate client using memory-based token storage.
///
/// Useful for testing and ephemeral sessions.
///
/// # Example
///
/// ```rust,ignore
/// use ttrpg_assistant::gate::{GeminiMemoryGate, MemoryTokenStorage};
///
/// let storage = MemoryTokenStorage::new();
/// let gate = GeminiMemoryGate::new(storage);
/// ```
pub type GeminiMemoryGate = OAuthFlow<MemoryTokenStorage>;

/// Keyring-backed Claude Gate client.
///
/// Uses the system keyring for secure token storage.
/// Only available when the `keyring` feature is enabled.
#[cfg(feature = "keyring")]
pub type ClaudeKeyringGate = OAuthFlow<KeyringTokenStorage>;

/// Keyring-backed Gemini Gate client.
///
/// Uses the system keyring for secure token storage.
/// Only available when the `keyring` feature is enabled.
#[cfg(feature = "keyring")]
pub type GeminiKeyringGate = OAuthFlow<KeyringTokenStorage>;

// ============================================================================
// Backward Compatibility - Type Conversions
// ============================================================================

/// Convert from claude_gate::TokenInfo to unified gate::TokenInfo.
impl From<crate::claude_gate::TokenInfo> for TokenInfo {
    fn from(token: crate::claude_gate::TokenInfo) -> Self {
        Self {
            token_type: token.token_type,
            access_token: token.access_token,
            refresh_token: token.refresh_token,
            expires_at: token.expires_at,
            provider: Some("anthropic".to_string()),
        }
    }
}

/// Convert from unified gate::TokenInfo to claude_gate::TokenInfo.
impl From<TokenInfo> for crate::claude_gate::TokenInfo {
    fn from(token: TokenInfo) -> Self {
        Self {
            token_type: token.token_type,
            access_token: token.access_token,
            refresh_token: token.refresh_token,
            expires_at: token.expires_at,
        }
    }
}

/// Convert from gemini_gate::TokenInfo to unified gate::TokenInfo.
#[allow(deprecated)]
impl From<crate::gemini_gate::TokenInfo> for TokenInfo {
    fn from(token: crate::gemini_gate::TokenInfo) -> Self {
        Self {
            token_type: token.token_type,
            access_token: token.access_token,
            refresh_token: token.refresh_token,
            expires_at: token.expires_at,
            provider: Some("gemini".to_string()),
        }
    }
}

/// Convert from unified gate::TokenInfo to gemini_gate::TokenInfo.
#[allow(deprecated)]
impl From<TokenInfo> for crate::gemini_gate::TokenInfo {
    fn from(token: TokenInfo) -> Self {
        Self {
            token_type: token.token_type,
            access_token: token.access_token,
            refresh_token: token.refresh_token,
            expires_at: token.expires_at,
        }
    }
}

/// Convert from claude_gate::OAuthFlowState to unified gate::OAuthFlowState.
impl From<crate::claude_gate::OAuthFlowState> for OAuthFlowState {
    fn from(state: crate::claude_gate::OAuthFlowState) -> Self {
        Self {
            code_verifier: state.pkce.verifier,
            code_challenge: state.pkce.challenge,
            state: state.state,
        }
    }
}

/// Convert from unified gate::OAuthFlowState to claude_gate::OAuthFlowState.
impl From<OAuthFlowState> for crate::claude_gate::OAuthFlowState {
    fn from(state: OAuthFlowState) -> Self {
        Self {
            pkce: crate::claude_gate::Pkce {
                verifier: state.code_verifier,
                challenge: state.code_challenge,
                method: "S256",
            },
            state: state.state,
        }
    }
}

/// Convert from gemini_gate::OAuthFlowState to unified gate::OAuthFlowState.
#[allow(deprecated)]
impl From<crate::gemini_gate::OAuthFlowState> for OAuthFlowState {
    fn from(state: crate::gemini_gate::OAuthFlowState) -> Self {
        Self {
            code_verifier: state.code_verifier,
            code_challenge: state.code_challenge,
            state: state.state,
        }
    }
}

/// Convert from unified gate::OAuthFlowState to gemini_gate::OAuthFlowState.
#[allow(deprecated)]
impl From<OAuthFlowState> for crate::gemini_gate::OAuthFlowState {
    fn from(state: OAuthFlowState) -> Self {
        Self {
            code_verifier: state.code_verifier,
            code_challenge: state.code_challenge,
            state: state.state,
        }
    }
}
