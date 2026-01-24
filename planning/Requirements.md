# Requirements: GitHub Copilot API Integration

## Introduction

This document specifies requirements for integrating `copilot-api-rs` into the TTRPG Assistant as a third OAuth-based LLM provider, alongside the existing `antigravity-gate-rs` (Gemini) and `claude-gate-rs` (Claude) integrations.

GitHub Copilot offers access to multiple LLM models (GPT-4o, Claude, Gemini) through a single OAuth flow, providing users with an alternative authentication pathway. Users with GitHub Copilot subscriptions can leverage their existing credentials without requiring separate API keys or additional OAuth flows for each provider.

The integration follows the established triple-gate architecture pattern, where `copilot-api-rs` becomes the third "gate" alongside the existing Claude and Gemini gates. This provides:
- **Cost savings**: Users with existing Copilot subscriptions avoid per-token API costs
- **Simplified auth**: Single GitHub OAuth flow grants access to multiple model families
- **Model diversity**: Access to GPT-4o, o1/o3 reasoning models, Claude, and Gemini through one provider

## Requirements

### Requirement 1: OAuth Authentication Flow

**User Story:** As a user with a GitHub Copilot subscription, I want to authenticate via GitHub Device Code OAuth, so that I can use Copilot models without managing separate API keys.

#### Acceptance Criteria

1. WHEN user initiates Copilot authentication THEN system SHALL display a device code and verification URL
2. WHEN user successfully authorizes via GitHub THEN system SHALL exchange the code for GitHub and Copilot tokens
3. WHEN authentication completes THEN system SHALL store tokens securely using the configured storage backend
4. IF user's GitHub account lacks Copilot access THEN system SHALL display "GitHub Copilot subscription required" error
5. WHEN stored token expires THEN system SHALL automatically refresh using the refresh token
6. IF token refresh fails THEN system SHALL prompt user to re-authenticate
7. WHEN user requests logout THEN system SHALL remove all stored Copilot tokens

### Requirement 2: Token Storage Integration

**User Story:** As a system administrator, I want Copilot tokens stored using the same pluggable storage infrastructure as other OAuth providers, so that token management is consistent and secure.

#### Acceptance Criteria

1. WHEN Copilot provider initializes THEN system SHALL use the configured TokenStorage backend (File, Memory, Keyring, or Callback)
2. WHEN storing tokens to file THEN system SHALL set file permissions to 0600 (Unix) or equivalent
3. WHEN loading tokens from environment THEN system SHALL support `COPILOT_GITHUB_TOKEN` variable
4. IF keyring feature is enabled THEN system SHALL store tokens in system credential store
5. WHEN token storage fails THEN system SHALL propagate storage-specific error with path context
6. WHEN application starts THEN system SHALL load cached tokens without requiring network calls

### Requirement 3: LLMProvider Trait Implementation

**User Story:** As a developer extending the application, I want CopilotProvider to implement the standard LLMProvider trait, so that it integrates seamlessly with the existing LLM router.

#### Acceptance Criteria

1. WHEN CopilotProvider receives a chat completion request THEN system SHALL convert to Copilot API format and return response in unified format
2. WHEN streaming is requested THEN system SHALL return an async stream of content deltas
3. WHEN model is specified as alias (e.g., "gpt-4o") THEN system SHALL resolve to full model identifier
4. WHEN request fails with 401 THEN system SHALL attempt token refresh before returning error
5. WHEN rate limited (429) THEN system SHALL include `retry_after` duration in error
6. WHEN CopilotProvider is queried for available models THEN system SHALL return cached model list from Copilot API

### Requirement 4: Format Transformation Layer

**User Story:** As a user, I want to send requests in the application's unified format, so that I don't need to learn Copilot-specific API formats.

#### Acceptance Criteria

1. WHEN request contains system prompt THEN system SHALL place it as first message with system role
2. WHEN request contains images THEN system SHALL convert to Copilot's image_url format with data URLs
3. WHEN request contains tools THEN system SHALL convert tool definitions to OpenAI function calling format
4. WHEN response contains tool calls THEN system SHALL extract and convert to unified ToolUse blocks
5. WHEN streaming response arrives THEN system SHALL parse SSE events and emit ContentDelta events
6. WHEN response includes usage statistics THEN system SHALL include token counts in response

### Requirement 5: Multi-Model Support

**User Story:** As a user, I want to select from all models available through Copilot (GPT-4o, Claude, Gemini, o1/o3), so that I can choose the best model for each task.

#### Acceptance Criteria

1. WHEN user requests model list THEN system SHALL return all models available to user's Copilot subscription
2. WHEN model list is cached THEN system SHALL return cached list without network call
3. WHEN model has known alias THEN system SHALL display both short name and full identifier
4. WHEN user selects unsupported model THEN system SHALL return "model not available" error with available alternatives
5. WHEN Copilot account type is Business/Enterprise THEN system SHALL use appropriate API endpoint

### Requirement 6: Error Handling and Recovery

**User Story:** As a user, I want clear error messages when Copilot requests fail, so that I can understand and resolve issues.

#### Acceptance Criteria

1. WHEN authentication fails THEN system SHALL distinguish between "not authenticated", "token expired", "Copilot not enabled", and "auth denied"
2. WHEN API returns error THEN system SHALL include HTTP status code and error message
3. WHEN network request fails THEN system SHALL include connection context in error
4. WHEN input exceeds model limits THEN system SHALL return "input too large" error
5. WHEN error requires re-authentication THEN system SHALL set `requires_reauth` flag
6. WHEN error is transient THEN system SHALL indicate retryability

### Requirement 7: Tauri Command Integration

**User Story:** As a frontend developer, I want Tauri commands for Copilot authentication and status, so that I can build the OAuth UI flow.

#### Acceptance Criteria

1. WHEN `start_copilot_auth` command is invoked THEN system SHALL return device code and verification URL
2. WHEN `poll_copilot_auth` command is invoked THEN system SHALL poll GitHub until authorization completes or times out
3. WHEN `check_copilot_auth` command is invoked THEN system SHALL return current authentication status
4. WHEN `logout_copilot` command is invoked THEN system SHALL clear stored tokens and return success
5. WHEN auth command fails THEN system SHALL return error message suitable for UI display
6. WHILE polling for authorization THEN system SHALL respect GitHub's poll interval to avoid rate limiting

### Requirement 8: Usage and Quota Tracking

**User Story:** As a user, I want to see my Copilot usage and remaining quota, so that I can monitor my subscription usage.

#### Acceptance Criteria

1. WHEN user requests usage info THEN system SHALL return current quota snapshot
2. WHEN quota includes completions limit THEN system SHALL show used/remaining counts
3. WHEN quota includes reset date THEN system SHALL show when quota resets
4. WHEN quota is exhausted THEN system SHALL indicate exhaustion state
5. WHEN usage info unavailable THEN system SHALL return appropriate error

## Non-Functional Requirements

### Performance

1. WHEN token is cached THEN authentication check SHALL complete in under 10ms
2. WHEN streaming response THEN first token SHALL arrive within configured timeout (default: 600s)
3. WHEN model list is cached THEN list retrieval SHALL complete in under 5ms
4. WHILE streaming THEN chunk delivery SHALL have no artificial buffering delays

### Security

1. WHEN storing tokens THEN system SHALL never log token values at INFO level or below
2. WHEN token file created THEN system SHALL set restrictive permissions before writing content
3. WHEN displaying auth URL THEN system SHALL NOT include sensitive parameters in logs
4. WHEN building requests THEN system SHALL use TLS for all network communication

### Reliability

1. WHEN Copilot API returns 5xx THEN system SHALL be retryable with exponential backoff
2. WHEN refresh token is invalid THEN system SHALL clear cached tokens to force re-auth
3. WHEN multiple concurrent requests occur THEN system SHALL share single token cache

## Constraints and Assumptions

### Constraints

- The integration must use the existing `TokenStorage` trait from the gate module
- The `LLMProvider` trait interface cannot be modified
- Device Code OAuth is the only supported authentication method (no API keys)
- The Copilot client ID is public and matches VS Code's Copilot extension

### Assumptions

- Users have an active GitHub Copilot subscription (Individual, Business, or Enterprise)
- The system has network access to GitHub and Copilot API endpoints
- File-based token storage is acceptable for development; production may use keyring
- The existing tri-gate architecture can accommodate a fourth provider without major refactoring

### Dependencies

- `copilot-api-rs` library (local path dependency)
- `tokio` async runtime (already in use)
- `reqwest` HTTP client (already in use)
- System keyring (optional feature)
