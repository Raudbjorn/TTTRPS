//! OAuth flow orchestrator.
//!
//! This module provides the [`OAuthFlow`] struct which orchestrates the complete
//! OAuth authentication lifecycle including:
//!
//! - Starting authorization (generating PKCE and authorization URL)
//! - Exchanging authorization codes for tokens
//! - Refreshing access tokens automatically
//! - Token storage and retrieval
//! - Logout functionality
//!
//! # Example
//!
//! ```rust,ignore
//! use gate::auth::{OAuthFlow, OAuthConfig};
//! use gate::storage::MemoryTokenStorage;
//!
//! # async fn example() -> gate::Result<()> {
//! let storage = MemoryTokenStorage::new();
//! let config = OAuthConfig::claude();
//! let flow = OAuthFlow::new(storage, config, "anthropic");
//!
//! // Check if already authenticated
//! if !flow.is_authenticated().await? {
//!     // Start OAuth flow
//!     let (url, state) = flow.start_authorization()?;
//!     println!("Open: {}", url);
//!
//!     // After user authorizes, exchange the code
//!     // let code = "..."; // From callback
//!     // flow.exchange_code(code, Some(&state.state)).await?;
//! }
//!
//! // Get access token (auto-refreshes if needed)
//! let token = flow.get_access_token().await?;
//! # Ok(())
//! # }
//! ```

use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, info, instrument, warn};

use super::config::OAuthConfig;
use super::state::OAuthFlowState;
use crate::gate::error::{AuthError, Error, Result};
use crate::gate::storage::TokenStorage;
use crate::gate::token::TokenInfo;

/// Response from the OAuth token endpoint.
#[derive(Debug, serde::Deserialize)]
struct TokenResponse {
    access_token: String,
    #[serde(default)]
    refresh_token: Option<String>,
    expires_in: i64,
    #[serde(default)]
    #[allow(dead_code)]
    token_type: Option<String>,
}

/// Error response from the OAuth token endpoint.
#[derive(Debug, serde::Deserialize)]
struct TokenErrorResponse {
    error: String,
    #[serde(default)]
    error_description: Option<String>,
}

/// OAuth flow orchestrator.
///
/// Manages the complete OAuth lifecycle including authorization,
/// token exchange, refresh, and storage. The flow is generic over
/// the storage backend to support different persistence strategies.
///
/// # Thread Safety
///
/// `OAuthFlow` is `Send + Sync` when the storage backend is `Send + Sync`,
/// allowing use from multiple async tasks.
///
/// # Provider Identification
///
/// Each flow is associated with a provider ID (e.g., "anthropic", "gemini")
/// which is used for storage namespacing.
///
/// # Example
///
/// ```rust,ignore
/// use gate::auth::{OAuthFlow, OAuthConfig};
/// use gate::storage::FileTokenStorage;
///
/// # async fn example() -> gate::Result<()> {
/// let storage = FileTokenStorage::default_path()?;
/// let config = OAuthConfig::gemini();
/// let flow = OAuthFlow::new(storage, config, "gemini");
///
/// // Use from multiple tasks
/// let flow = std::sync::Arc::new(flow);
/// let flow_clone = flow.clone();
///
/// tokio::spawn(async move {
///     let token = flow_clone.get_access_token().await;
/// });
/// # Ok(())
/// # }
/// ```
pub struct OAuthFlow<S: TokenStorage> {
    /// Token storage backend.
    storage: S,
    /// OAuth configuration.
    config: OAuthConfig,
    /// Provider identifier (e.g., "anthropic", "gemini").
    provider_id: String,
    /// Pending OAuth flow state (PKCE verifier, challenge, state).
    ///
    /// This is set when `start_authorization()` is called and cleared
    /// after `exchange_code()` completes.
    pending_state: Arc<RwLock<Option<OAuthFlowState>>>,
    /// HTTP client for token operations.
    http_client: reqwest::Client,
}

impl<S: TokenStorage> OAuthFlow<S> {
    /// Create a new OAuthFlow with the specified configuration.
    ///
    /// # Arguments
    ///
    /// * `storage` - Token storage backend for persisting credentials
    /// * `config` - OAuth configuration (endpoints, client ID, scopes)
    /// * `provider_id` - Provider identifier for storage namespacing
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// use gate::auth::{OAuthFlow, OAuthConfig};
    /// use gate::storage::MemoryTokenStorage;
    ///
    /// let storage = MemoryTokenStorage::new();
    /// let config = OAuthConfig::claude();
    /// let flow = OAuthFlow::new(storage, config, "anthropic");
    /// ```
    pub fn new(storage: S, config: OAuthConfig, provider_id: impl Into<String>) -> Self {
        Self {
            storage,
            config,
            provider_id: provider_id.into(),
            pending_state: Arc::new(RwLock::new(None)),
            http_client: reqwest::Client::new(),
        }
    }

    /// Get the provider ID.
    pub fn provider_id(&self) -> &str {
        &self.provider_id
    }

    /// Get a reference to the OAuth configuration.
    pub fn config(&self) -> &OAuthConfig {
        &self.config
    }

    /// Get a reference to the storage backend.
    pub fn storage(&self) -> &S {
        &self.storage
    }

    /// Start a new authorization flow.
    ///
    /// Generates PKCE verifier/challenge and state, then returns the
    /// authorization URL for the user to visit along with the flow state.
    ///
    /// The flow state should be stored temporarily and the state parameter
    /// should be validated when the callback is received.
    ///
    /// # Returns
    ///
    /// A tuple of `(authorization_url, flow_state)` where:
    /// - `authorization_url`: URL for user to visit to authorize
    /// - `flow_state`: Contains verifier and state for later validation
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// use gate::auth::{OAuthFlow, OAuthConfig};
    /// use gate::storage::MemoryTokenStorage;
    ///
    /// let storage = MemoryTokenStorage::new();
    /// let flow = OAuthFlow::new(storage, OAuthConfig::claude(), "anthropic");
    ///
    /// let (url, state) = flow.start_authorization().unwrap();
    /// println!("Open in browser: {}", url);
    /// println!("State for validation: {}", state.state);
    /// ```
    #[instrument(skip(self))]
    pub fn start_authorization(&self) -> Result<(String, OAuthFlowState)> {
        let flow_state = OAuthFlowState::new();

        let url = self.build_authorization_url(&flow_state.code_challenge, &flow_state.state);

        debug!(state = %flow_state.state, "Started OAuth authorization flow");

        // Store the pending state
        // Note: We use try_write to avoid blocking. If lock is held, spawn a task.
        let pending_clone = flow_state.clone();

        // Try non-blocking write first
        if let Ok(mut pending) = self.pending_state.try_write() {
            *pending = Some(pending_clone);
        } else {
            // Lock is held, block until we can set the state
            // This ensures pending state is set before returning
            let pending_state = Arc::clone(&self.pending_state);
            tokio::runtime::Handle::current().block_on(async move {
                let mut pending = pending_state.write().await;
                *pending = Some(pending_clone);
            });
        }

        Ok((url, flow_state))
    }

    /// Start authorization without blocking.
    ///
    /// Async version of `start_authorization()` that doesn't use try_write.
    /// Preferred when calling from an async context.
    #[instrument(skip(self))]
    pub async fn start_authorization_async(&self) -> Result<(String, OAuthFlowState)> {
        let flow_state = OAuthFlowState::new();

        let url = self.build_authorization_url(&flow_state.code_challenge, &flow_state.state);

        debug!(state = %flow_state.state, "Started OAuth authorization flow");

        // Store the pending state
        {
            let mut pending = self.pending_state.write().await;
            *pending = Some(flow_state.clone());
        }

        Ok((url, flow_state))
    }

    /// Build the authorization URL with all required parameters.
    fn build_authorization_url(&self, challenge: &str, state: &str) -> String {
        let scopes = self.config.scopes.join(" ");

        let mut url = format!(
            "{}?client_id={}&redirect_uri={}&response_type=code&scope={}&code_challenge={}&code_challenge_method=S256&state={}",
            self.config.auth_url,
            urlencoding::encode(&self.config.client_id),
            urlencoding::encode(&self.config.redirect_uri),
            urlencoding::encode(&scopes),
            urlencoding::encode(challenge),
            urlencoding::encode(state),
        );

        // Add access_type=offline and prompt=consent for Google OAuth
        // to ensure we get a refresh token
        if self.config.auth_url.contains("google.com") {
            url.push_str("&access_type=offline&prompt=consent");
        }

        url
    }

    /// Exchange an authorization code for tokens.
    ///
    /// Completes the OAuth flow by exchanging the authorization code
    /// for access and refresh tokens. Optionally validates the state
    /// parameter to protect against CSRF attacks.
    ///
    /// # Arguments
    ///
    /// * `code` - Authorization code from the OAuth callback
    /// * `state` - Optional state parameter to validate (recommended)
    ///
    /// # State Validation
    ///
    /// If `state` is provided, it is validated against the pending flow state.
    /// This protects against CSRF attacks where an attacker might try to
    /// inject their own authorization code.
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - State validation fails (`AuthError::StateMismatch`)
    /// - No pending flow state exists
    /// - Token exchange fails
    /// - Storage fails
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// use gate::auth::{OAuthFlow, OAuthConfig};
    /// use gate::storage::MemoryTokenStorage;
    ///
    /// # async fn example() -> gate::Result<()> {
    /// let storage = MemoryTokenStorage::new();
    /// let flow = OAuthFlow::new(storage, OAuthConfig::claude(), "anthropic");
    ///
    /// // Start authorization
    /// let (url, flow_state) = flow.start_authorization_async().await?;
    ///
    /// // ... user completes authorization ...
    ///
    /// // Exchange code (with state validation)
    /// let code = "auth_code_from_callback";
    /// let state = "state_from_callback";
    /// let token = flow.exchange_code(code, Some(state)).await?;
    /// # Ok(())
    /// # }
    /// ```
    #[instrument(skip(self, code, state))]
    pub async fn exchange_code(&self, code: &str, state: Option<&str>) -> Result<TokenInfo> {
        // Get and clear pending state
        let pending_state = {
            let mut pending = self.pending_state.write().await;
            pending.take()
        };

        // Validate state if provided
        if let Some(expected_state) = state {
            match &pending_state {
                Some(flow_state) if flow_state.state != expected_state => {
                    warn!(
                        expected = %flow_state.state,
                        received = %expected_state,
                        "OAuth state mismatch"
                    );
                    return Err(Error::Auth(AuthError::StateMismatch));
                }
                None => {
                    warn!("OAuth state provided but no pending flow state found");
                    return Err(Error::Auth(AuthError::StateMismatch));
                }
                _ => {
                    debug!("OAuth state validated successfully");
                }
            }
        }

        // Get the verifier from pending state
        let verifier = match &pending_state {
            Some(flow_state) => flow_state.code_verifier.clone(),
            None => {
                // If no pending state, we can't proceed without a verifier
                warn!("No pending flow state, cannot exchange code");
                return Err(Error::Auth(AuthError::StateMismatch));
            }
        };

        // Exchange the code for tokens
        let token = self.do_exchange_code(code, &verifier).await?;

        // Save the token
        self.storage.save(&self.provider_id, &token).await?;

        info!("OAuth flow completed successfully");

        Ok(token)
    }

    /// Exchange code using an externally-provided verifier.
    ///
    /// Use this when you've stored the verifier externally rather than
    /// relying on the pending flow state.
    ///
    /// # Arguments
    ///
    /// * `code` - Authorization code from callback
    /// * `verifier` - PKCE code verifier
    /// * `expected_state` - Optional state to validate against
    /// * `received_state` - State received in callback
    #[instrument(skip(self, code, verifier))]
    pub async fn exchange_code_with_verifier(
        &self,
        code: &str,
        verifier: &str,
        expected_state: Option<&str>,
        received_state: Option<&str>,
    ) -> Result<TokenInfo> {
        // Validate state if both are provided
        if let (Some(expected), Some(received)) = (expected_state, received_state) {
            if expected != received {
                warn!(
                    expected = %expected,
                    received = %received,
                    "OAuth state mismatch"
                );
                return Err(Error::Auth(AuthError::StateMismatch));
            }
            debug!("OAuth state validated successfully");
        }

        // Exchange the code for tokens
        let token = self.do_exchange_code(code, verifier).await?;

        // Save the token
        self.storage.save(&self.provider_id, &token).await?;

        info!("OAuth flow completed successfully");

        Ok(token)
    }

    /// Perform the actual token exchange HTTP request.
    async fn do_exchange_code(&self, code: &str, verifier: &str) -> Result<TokenInfo> {
        debug!("Exchanging authorization code for tokens");

        let mut form_data = vec![
            ("code", code.to_string()),
            ("code_verifier", verifier.to_string()),
            ("grant_type", "authorization_code".to_string()),
            ("redirect_uri", self.config.redirect_uri.clone()),
            ("client_id", self.config.client_id.clone()),
        ];

        // Add client_secret if present (required for some providers)
        if let Some(ref secret) = self.config.client_secret {
            form_data.push(("client_secret", secret.clone()));
        }

        let response = self
            .http_client
            .post(&self.config.token_url)
            .form(&form_data)
            .send()
            .await?;

        let status = response.status();
        let body = response.text().await?;

        if !status.is_success() {
            // Try to parse error response
            if let Ok(error) = serde_json::from_str::<TokenErrorResponse>(&body) {
                warn!(
                    error = %error.error,
                    description = ?error.error_description,
                    "Token exchange failed"
                );

                if error.error == "invalid_grant" {
                    return Err(Error::Auth(AuthError::InvalidGrant));
                }

                return Err(Error::api(
                    status.as_u16(),
                    error
                        .error_description
                        .unwrap_or_else(|| error.error.clone()),
                    None,
                ));
            }

            return Err(Error::api(status.as_u16(), body, None));
        }

        let token_response: TokenResponse = serde_json::from_str(&body)?;

        // refresh_token is required for initial exchange
        let refresh_token = token_response.refresh_token.ok_or_else(|| {
            Error::Auth(AuthError::InvalidGrant)
        })?;

        debug!("Token exchange successful");

        Ok(TokenInfo::new(
            token_response.access_token,
            refresh_token,
            token_response.expires_in,
        ).with_provider(&self.provider_id))
    }

    /// Get a valid access token, refreshing if necessary.
    ///
    /// If the stored access token is expired or about to expire (within 5 minutes),
    /// automatically refreshes it using the refresh token.
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - Not authenticated (`AuthError::NotAuthenticated`)
    /// - Token refresh fails (`AuthError::InvalidGrant` if revoked)
    /// - Storage access fails
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// use gate::auth::{OAuthFlow, OAuthConfig};
    /// use gate::storage::MemoryTokenStorage;
    ///
    /// # async fn example() -> gate::Result<()> {
    /// let storage = MemoryTokenStorage::new();
    /// let flow = OAuthFlow::new(storage, OAuthConfig::claude(), "anthropic");
    ///
    /// // Get token (auto-refreshes if needed)
    /// let access_token = flow.get_access_token().await?;
    /// # Ok(())
    /// # }
    /// ```
    #[instrument(skip(self))]
    pub async fn get_access_token(&self) -> Result<String> {
        let token = self
            .storage
            .load(&self.provider_id)
            .await?
            .ok_or(Error::Auth(AuthError::NotAuthenticated))?;

        // Check if token needs refresh (expired or within 5-minute window)
        if token.needs_refresh() {
            debug!("Access token expired or expiring soon, refreshing");
            let new_token = self.refresh_token(&token.refresh_token).await?;
            self.storage.save(&self.provider_id, &new_token).await?;
            return Ok(new_token.access_token);
        }

        Ok(token.access_token)
    }

    /// Get the full TokenInfo, refreshing if necessary.
    ///
    /// Like `get_access_token()` but returns the complete token info
    /// including refresh token and expiry.
    #[instrument(skip(self))]
    pub async fn get_token(&self) -> Result<TokenInfo> {
        let token = self
            .storage
            .load(&self.provider_id)
            .await?
            .ok_or(Error::Auth(AuthError::NotAuthenticated))?;

        // Check if token needs refresh
        if token.needs_refresh() {
            debug!("Access token expired or expiring soon, refreshing");
            let new_token = self.refresh_token(&token.refresh_token).await?;
            self.storage.save(&self.provider_id, &new_token).await?;
            return Ok(new_token);
        }

        Ok(token)
    }

    /// Refresh an access token using a refresh token.
    ///
    /// Exchanges the refresh token for a new access token. Note that
    /// some providers may not return a new refresh token on refresh requests.
    ///
    /// # Arguments
    ///
    /// * `refresh_token` - The refresh token (may be in composite format)
    ///
    /// # Composite Token Handling
    ///
    /// If the refresh token is in composite format (`refresh|project|managed`),
    /// only the base refresh token is sent to the provider. Project IDs are
    /// preserved and re-attached to the resulting TokenInfo.
    ///
    /// # Errors
    ///
    /// Returns an error if:
    /// - The refresh token is invalid or revoked (`AuthError::InvalidGrant`)
    /// - Network error occurs
    /// - Response cannot be parsed
    #[instrument(skip(self, refresh_token))]
    pub async fn refresh_token(&self, refresh_token: &str) -> Result<TokenInfo> {
        // Parse composite token format if present
        let (base_refresh, project_id, managed_project_id) = parse_composite_token(refresh_token);

        debug!("Refreshing access token");

        let mut form_data = vec![
            ("refresh_token", base_refresh.clone()),
            ("grant_type", "refresh_token".to_string()),
            ("client_id", self.config.client_id.clone()),
        ];

        // Add client_secret if present
        if let Some(ref secret) = self.config.client_secret {
            form_data.push(("client_secret", secret.clone()));
        }

        let response = self
            .http_client
            .post(&self.config.token_url)
            .form(&form_data)
            .send()
            .await?;

        let status = response.status();
        let body = response.text().await?;

        if !status.is_success() {
            // Try to parse error response
            if let Ok(error) = serde_json::from_str::<TokenErrorResponse>(&body) {
                warn!(
                    error = %error.error,
                    description = ?error.error_description,
                    "Token refresh failed"
                );

                if error.error == "invalid_grant" {
                    return Err(Error::Auth(AuthError::InvalidGrant));
                }

                return Err(Error::api(
                    status.as_u16(),
                    error
                        .error_description
                        .unwrap_or_else(|| error.error.clone()),
                    None,
                ));
            }

            return Err(Error::api(status.as_u16(), body, None));
        }

        let token_response: TokenResponse = serde_json::from_str(&body)?;

        debug!("Token refresh successful");

        // Use new refresh token if provided, otherwise preserve the old one
        let new_refresh = token_response
            .refresh_token
            .unwrap_or_else(|| base_refresh.clone());

        let mut token = TokenInfo::new(
            token_response.access_token,
            new_refresh,
            token_response.expires_in,
        ).with_provider(&self.provider_id);

        // Preserve project IDs from composite token
        if let Some(project) = project_id {
            token = token.with_project_ids(&project, managed_project_id.as_deref());
        }

        Ok(token)
    }

    /// Check if the user is currently authenticated.
    ///
    /// Returns `true` if a token exists in storage. Note that this
    /// doesn't verify the token is still valid with the provider - use
    /// `get_access_token()` for that.
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// use gate::auth::{OAuthFlow, OAuthConfig};
    /// use gate::storage::MemoryTokenStorage;
    ///
    /// # async fn example() -> gate::Result<()> {
    /// let storage = MemoryTokenStorage::new();
    /// let flow = OAuthFlow::new(storage, OAuthConfig::claude(), "anthropic");
    ///
    /// if flow.is_authenticated().await? {
    ///     println!("Already authenticated");
    /// } else {
    ///     println!("Need to authenticate");
    /// }
    /// # Ok(())
    /// # }
    /// ```
    #[instrument(skip(self))]
    pub async fn is_authenticated(&self) -> Result<bool> {
        self.storage.exists(&self.provider_id).await
    }

    /// Log out by removing stored tokens.
    ///
    /// Clears the stored token and any pending flow state.
    /// Does not revoke the token with the provider.
    ///
    /// # Example
    ///
    /// ```rust,ignore
    /// use gate::auth::{OAuthFlow, OAuthConfig};
    /// use gate::storage::MemoryTokenStorage;
    ///
    /// # async fn example() -> gate::Result<()> {
    /// let storage = MemoryTokenStorage::new();
    /// let flow = OAuthFlow::new(storage, OAuthConfig::claude(), "anthropic");
    ///
    /// flow.logout().await?;
    /// assert!(!flow.is_authenticated().await?);
    /// # Ok(())
    /// # }
    /// ```
    #[instrument(skip(self))]
    pub async fn logout(&self) -> Result<()> {
        // Clear pending state
        {
            let mut pending = self.pending_state.write().await;
            *pending = None;
        }

        // Remove stored token
        self.storage.remove(&self.provider_id).await?;

        info!("Logged out successfully");

        Ok(())
    }
}

/// Parse a composite refresh token into its parts.
///
/// Format: `base_refresh|project_id|managed_project_id`
///
/// Returns (base_refresh, project_id, managed_project_id)
fn parse_composite_token(token: &str) -> (String, Option<String>, Option<String>) {
    let parts: Vec<&str> = token.split('|').collect();
    let base = parts[0].to_string();
    let project = parts
        .get(1)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string());
    let managed = parts
        .get(2)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string());
    (base, project, managed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gate::storage::MemoryTokenStorage;

    #[tokio::test]
    async fn test_new_flow_not_authenticated() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        assert!(!flow.is_authenticated().await.unwrap());
    }

    #[tokio::test]
    async fn test_start_authorization_returns_url_and_state() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        let (url, state) = flow.start_authorization_async().await.unwrap();

        assert!(url.contains("claude.ai") || url.contains("oauth"));
        assert!(!state.state.is_empty());
        assert!(!state.code_verifier.is_empty());
        assert!(!state.code_challenge.is_empty());
    }

    #[tokio::test]
    async fn test_start_authorization_stores_pending_state() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        let (_, state) = flow.start_authorization_async().await.unwrap();

        // Verify pending state is stored
        let pending = flow.pending_state.read().await;
        assert!(pending.is_some());
        assert_eq!(pending.as_ref().unwrap().state, state.state);
    }

    #[tokio::test]
    async fn test_exchange_code_validates_state_mismatch() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        // Start flow to set pending state
        let (_, _state) = flow.start_authorization_async().await.unwrap();

        // Try to exchange with wrong state
        let result = flow.exchange_code("code", Some("wrong_state")).await;

        assert!(result.is_err());
        match result.unwrap_err() {
            Error::Auth(AuthError::StateMismatch) => {}
            e => panic!("Expected StateMismatch, got: {:?}", e),
        }
    }

    #[tokio::test]
    async fn test_exchange_code_validates_state_no_pending() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        // Don't start flow, so no pending state

        // Try to exchange with state (but no pending state)
        let result = flow.exchange_code("code", Some("some_state")).await;

        assert!(result.is_err());
        match result.unwrap_err() {
            Error::Auth(AuthError::StateMismatch) => {}
            e => panic!("Expected StateMismatch, got: {:?}", e),
        }
    }

    #[tokio::test]
    async fn test_get_access_token_not_authenticated() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        let result = flow.get_access_token().await;

        assert!(result.is_err());
        match result.unwrap_err() {
            Error::Auth(AuthError::NotAuthenticated) => {}
            e => panic!("Expected NotAuthenticated, got: {:?}", e),
        }
    }

    #[tokio::test]
    async fn test_get_access_token_returns_stored_token() {
        let storage = MemoryTokenStorage::new();
        let token = TokenInfo::new("my_access_token".into(), "refresh".into(), 3600);
        storage.save("anthropic", &token).await.unwrap();

        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");
        let access_token = flow.get_access_token().await.unwrap();

        assert_eq!(access_token, "my_access_token");
    }

    #[tokio::test]
    async fn test_is_authenticated_with_token() {
        let storage = MemoryTokenStorage::new();
        let token = TokenInfo::new("access".into(), "refresh".into(), 3600);
        storage.save("anthropic", &token).await.unwrap();

        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        assert!(flow.is_authenticated().await.unwrap());
    }

    #[tokio::test]
    async fn test_logout_removes_token() {
        let storage = MemoryTokenStorage::new();
        let token = TokenInfo::new("access".into(), "refresh".into(), 3600);
        storage.save("anthropic", &token).await.unwrap();

        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        // Verify authenticated
        assert!(flow.is_authenticated().await.unwrap());

        // Logout
        flow.logout().await.unwrap();

        // Verify not authenticated
        assert!(!flow.is_authenticated().await.unwrap());
    }

    #[tokio::test]
    async fn test_logout_clears_pending_state() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        // Start authorization to set pending state
        let _ = flow.start_authorization_async().await.unwrap();

        // Verify pending state exists
        {
            let pending = flow.pending_state.read().await;
            assert!(pending.is_some());
        }

        // Logout
        flow.logout().await.unwrap();

        // Verify pending state cleared
        {
            let pending = flow.pending_state.read().await;
            assert!(pending.is_none());
        }
    }

    #[tokio::test]
    async fn test_provider_id() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        assert_eq!(flow.provider_id(), "anthropic");
    }

    #[tokio::test]
    async fn test_storage_accessor() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        assert_eq!(flow.storage().name(), "memory");
    }

    #[test]
    fn test_parse_composite_token_simple() {
        let (base, project, managed) = parse_composite_token("refresh_token_here");
        assert_eq!(base, "refresh_token_here");
        assert!(project.is_none());
        assert!(managed.is_none());
    }

    #[test]
    fn test_parse_composite_token_with_project() {
        let (base, project, managed) = parse_composite_token("refresh|proj-123");
        assert_eq!(base, "refresh");
        assert_eq!(project.as_deref(), Some("proj-123"));
        assert!(managed.is_none());
    }

    #[test]
    fn test_parse_composite_token_with_both() {
        let (base, project, managed) = parse_composite_token("refresh|proj-123|managed-456");
        assert_eq!(base, "refresh");
        assert_eq!(project.as_deref(), Some("proj-123"));
        assert_eq!(managed.as_deref(), Some("managed-456"));
    }

    #[test]
    fn test_parse_composite_token_with_empty_parts() {
        // Empty project ID
        let (base, project, managed) = parse_composite_token("refresh||managed-456");
        assert_eq!(base, "refresh");
        assert!(project.is_none());
        assert_eq!(managed.as_deref(), Some("managed-456"));

        // Empty managed project ID
        let (base, project, managed) = parse_composite_token("refresh|proj-123|");
        assert_eq!(base, "refresh");
        assert_eq!(project.as_deref(), Some("proj-123"));
        assert!(managed.is_none());
    }

    #[tokio::test]
    async fn test_authorization_url_claude() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::claude();
        let flow = OAuthFlow::new(storage, config, "anthropic");

        let (url, _) = flow.start_authorization_async().await.unwrap();

        // Check Claude-specific parameters
        assert!(url.contains("client_id="));
        assert!(url.contains("redirect_uri="));
        assert!(url.contains("response_type=code"));
        assert!(url.contains("scope="));
        assert!(url.contains("code_challenge="));
        assert!(url.contains("code_challenge_method=S256"));
        assert!(url.contains("state="));
    }

    #[tokio::test]
    async fn test_authorization_url_gemini() {
        let storage = MemoryTokenStorage::new();
        let config = OAuthConfig::gemini();
        let flow = OAuthFlow::new(storage, config, "gemini");

        let (url, _) = flow.start_authorization_async().await.unwrap();

        // Check Google-specific parameters
        assert!(url.contains("client_id="));
        assert!(url.contains("redirect_uri="));
        assert!(url.contains("response_type=code"));
        assert!(url.contains("scope="));
        assert!(url.contains("code_challenge="));
        assert!(url.contains("code_challenge_method=S256"));
        assert!(url.contains("state="));
        assert!(url.contains("access_type=offline"));
        assert!(url.contains("prompt=consent"));
    }
}
