# Tasks: GitHub Copilot API Integration

## Implementation Overview

This implementation follows a **foundation-first** strategy, building from core infrastructure (storage, auth) up through the API surface (client, provider) and finally integration points (commands, router). Each task produces working, testable code before proceeding to dependent tasks.

The implementation is organized into 7 phases:
1. **Embed Library** - Copy copilot-api-rs into gate module
2. **Storage Integration** - Connect to shared TokenStorage infrastructure
3. **OAuth Provider** - Implement CopilotProvider for auth flow
4. **Client Integration** - Wire CopilotClient to storage and auth
5. **LLM Provider** - Implement LLMProvider trait adapter
6. **Commands & Router** - Add Tauri commands and router registration

---

## Implementation Plan

### Phase 1: Embed Library

- [ ] **1.1 Copy copilot-api-rs source into gate/copilot/**
  - Create `src-tauri/src/gate/copilot/` directory structure
  - Copy `client.rs`, `error.rs`, `config.rs` from copilot-api-rs/src/
  - Copy `auth/` module (device_flow.rs, token_exchange.rs, refresh.rs, constants.rs)
  - Copy `models/` module (auth.rs, chat.rs, embeddings.rs, models.rs, streaming.rs)
  - Copy `api/` module (chat.rs, embeddings.rs, models.rs, usage.rs)
  - Copy `transform/` module (openai.rs, anthropic.rs)
  - Update module paths to use `crate::gate::copilot::` prefix
  - _Requirements: 1.1, 2.1_

- [ ] **1.2 Create gate/copilot/mod.rs with re-exports**
  - Export public types: `CopilotClient`, `CopilotClientBuilder`
  - Export auth types: `DeviceFlowPending`, `PollResult`
  - Export model types: `ChatRequest`, `ChatResponse`, `Message`, `Role`, `Content`
  - Export error types: `CopilotError`, `Result`
  - Add module documentation
  - _Requirements: 3.1_

- [ ] **1.3 Update Cargo.toml with any missing dependencies**
  - Verify all dependencies exist (should be mostly covered by existing deps)
  - Add any missing optional features if needed
  - Run `cargo check` to verify compilation
  - _Requirements: 1.1_

### Phase 2: Storage Integration

- [ ] **2.1 Create gate/copilot/storage.rs with TokenStorage adapter**
  - Import shared `TokenStorage` trait from `crate::gate::storage`
  - Create `CopilotTokenStorage<S: TokenStorage>` wrapper
  - Implement token load/save with "copilot" provider discrimination
  - Map storage errors to CopilotError::Storage
  - Write unit tests for load/save/remove operations
  - _Requirements: 2.1, 2.2, 2.5, 2.6_

- [ ] **2.2 Add provider field to unified TokenInfo**
  - Extend `crate::gate::token::TokenInfo` with optional `provider: Option<String>`
  - Update serialization to include provider field
  - Add helper method `is_copilot_token(&self) -> bool`
  - Update existing Claude/Gemini code to set provider field
  - Write unit tests for provider discrimination
  - _Requirements: 2.1_

- [ ] **2.3 Implement environment variable storage source**
  - Create `EnvTokenSource` for loading from `COPILOT_GITHUB_TOKEN`
  - Support both single JSON env var and split env vars
  - Implement as read-only (save returns error)
  - Write unit tests with mocked environment
  - _Requirements: 2.3_

### Phase 3: OAuth Provider

- [ ] **3.1 Create gate/providers/copilot.rs with CopilotProvider struct**
  - Implement `OAuthProvider` trait for `CopilotProvider`
  - Define `provider_id()` returning "copilot"
  - Define `name()` returning "GitHub Copilot"
  - Define `oauth_config()` with GitHub client ID and URLs
  - Add documentation for Device Code flow differences
  - _Requirements: 1.1, 1.2_

- [ ] **3.2 Implement Device Code flow initiation**
  - Implement `initiate_device_flow()` method
  - POST to `https://github.com/login/device/code` with client_id and scope
  - Parse response into `DeviceFlowPending` struct
  - Handle error responses (rate limit, invalid request)
  - Write unit tests with wiremock mock server
  - _Requirements: 1.1_

- [ ] **3.3 Implement Device Code polling**
  - Implement `poll_device_flow()` method
  - POST to `https://github.com/login/oauth/access_token` with device_code
  - Handle response variants: success, authorization_pending, slow_down, expired, access_denied
  - Return appropriate `PollResult` variant
  - Write unit tests for each response type
  - _Requirements: 1.2, 1.4, 7.6_

- [ ] **3.4 Implement GitHub to Copilot token exchange**
  - Implement `exchange_github_token()` method
  - GET `https://api.github.com/copilot_internal/v2/token` with GitHub Bearer token
  - Parse Copilot token response
  - Handle "Copilot not enabled" error
  - Construct `TokenInfo` with both tokens
  - Write unit tests for exchange and error cases
  - _Requirements: 1.2, 1.4_

- [ ] **3.5 Implement token refresh**
  - Implement `refresh_token()` method
  - Use Copilot refresh token to get new access token
  - Handle refresh failure (invalid grant, network error)
  - Update cached token on success
  - Write unit tests for refresh success and failure
  - _Requirements: 1.5, 1.6_

### Phase 4: Client Integration

- [ ] **4.1 Update CopilotClient to use shared storage**
  - Modify `CopilotClient<S>` constructor to accept `S: TokenStorage`
  - Wire storage to `CopilotTokenStorage` adapter
  - Initialize token cache from storage on creation
  - Update builder pattern to accept storage
  - Write unit tests for client initialization
  - _Requirements: 2.1, 2.6_

- [ ] **4.2 Implement automatic token refresh in client**
  - Check token expiry before each API request
  - Trigger refresh if within 60-second buffer
  - Handle 401 responses with single retry after refresh
  - Clear token cache on refresh failure
  - Write integration tests for auto-refresh
  - _Requirements: 1.5, 3.4_

- [ ] **4.3 Implement model list caching**
  - Add `models_cache: Arc<RwLock<Option<ModelsResponse>>>` to client
  - Implement `models()` for fresh fetch
  - Implement `models_cached()` for cached retrieval
  - Cache invalidation on auth state change
  - Write unit tests for cache behavior
  - _Requirements: 5.1, 5.2_

- [ ] **4.4 Implement account type endpoint selection**
  - Add `AccountType` enum (Individual, Business, Enterprise)
  - Select base URL based on account type
  - Auto-detect from Copilot token metadata if available
  - Default to Individual if unknown
  - Write unit tests for endpoint selection
  - _Requirements: 5.5_

### Phase 5: LLM Provider

- [ ] **5.1 Create CopilotClientTrait for type erasure**
  - Define `CopilotClientTrait` with async methods matching client interface
  - Implement trait for `CopilotClient<FileTokenStorage>`
  - Implement trait for `CopilotClient<MemoryTokenStorage>`
  - Implement trait for `CopilotClient<KeyringTokenStorage>` (feature-gated)
  - Write marker tests verifying trait implementations
  - _Requirements: 3.1_

- [ ] **5.2 Create core/llm/providers/copilot.rs with CopilotLLMProvider**
  - Define `CopilotLLMProvider` struct with `Arc<dyn CopilotClientTrait>`
  - Implement factory methods: `new()`, `with_keyring()`, `with_memory()`
  - Store default model and max_tokens configuration
  - Implement `name()` returning "copilot"
  - _Requirements: 3.1_

- [ ] **5.3 Implement LLMProvider::generate()**
  - Convert `LLMRequest` to Copilot `ChatRequest`
  - Send request via client
  - Convert `ChatResponse` to `LLMResponse`
  - Map errors to `LLMError`
  - Write unit tests for request/response conversion
  - _Requirements: 3.1, 4.1, 4.3, 4.5, 4.6_

- [ ] **5.4 Implement LLMProvider::generate_stream()**
  - Convert `LLMRequest` to Copilot `ChatRequest` with `stream: true`
  - Return `Pin<Box<dyn Stream<Item = Result<StreamChunk>>>>>`
  - Parse SSE events and emit `StreamChunk` variants
  - Handle stream errors gracefully
  - Write integration tests for streaming
  - _Requirements: 3.2, 4.5_

- [ ] **5.5 Implement LLMProvider::available_models()**
  - Call `client.models_cached()`
  - Convert `ModelsResponse` to `Vec<ModelInfo>`
  - Include model aliases for user-friendly display
  - Handle not-authenticated case
  - Write unit tests for model listing
  - _Requirements: 5.1, 5.3_

- [ ] **5.6 Implement format conversion helpers**
  - Create `convert_request(request: &LLMRequest) -> ChatRequest`
  - Create `convert_response(response: ChatResponse) -> LLMResponse`
  - Handle system prompts (place as first system message)
  - Handle images (convert to data URL format)
  - Handle tools (convert to OpenAI function calling format)
  - Write comprehensive unit tests for edge cases
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

### Phase 6: Commands & Router Integration

- [ ] **6.1 Add Tauri command: start_copilot_auth**
  - Add `start_copilot_auth` command to `commands.rs`
  - Initiate device flow via CopilotProvider
  - Return `DeviceCodeResponse` with user_code, verification_uri
  - Handle errors and return user-friendly messages
  - _Requirements: 7.1_

- [ ] **6.2 Add Tauri command: poll_copilot_auth**
  - Add `poll_copilot_auth` command to `commands.rs`
  - Accept device_code parameter
  - Poll GitHub and return `AuthPollResult` (Success, Pending, Expired, Denied)
  - On success, exchange and store tokens
  - _Requirements: 7.2, 7.6_

- [ ] **6.3 Add Tauri command: check_copilot_auth**
  - Add `check_copilot_auth` command to `commands.rs`
  - Check storage for valid token
  - Return `AuthStatus` with authenticated flag and expiry info
  - _Requirements: 7.3_

- [ ] **6.4 Add Tauri command: logout_copilot**
  - Add `logout_copilot` command to `commands.rs`
  - Clear stored tokens via storage.remove()
  - Clear any cached client state
  - Return success/failure
  - _Requirements: 7.4, 1.7_

- [ ] **6.5 Add Tauri command: get_copilot_usage**
  - Add `get_copilot_usage` command to `commands.rs`
  - Call `client.usage()` and return quota info
  - Handle not-authenticated and API errors
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] **6.6 Register CopilotLLMProvider with LLM router**
  - Update `core/llm_router.rs` to include Copilot provider
  - Add Copilot to provider selection logic
  - Update cost tracking if applicable
  - Update failover chain if desired
  - Write integration test for router with Copilot
  - _Requirements: 3.1_

- [ ] **6.7 Add frontend bindings in bindings.rs**
  - Add TypeScript types for Copilot auth responses
  - Add wrapper functions for Copilot commands
  - Update any existing auth UI types to include Copilot
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

### Phase 7: Testing & Documentation

- [ ] **7.1 Write integration tests for full auth flow**
  - Test device flow → poll → exchange → storage round-trip
  - Test token refresh cycle
  - Test logout clears all state
  - Use wiremock for GitHub/Copilot API mocking
  - _Requirements: 1.1, 1.2, 1.5, 1.7_

- [ ] **7.2 Write integration tests for chat completions**
  - Test non-streaming request/response
  - Test streaming with multiple chunks
  - Test tool use request/response
  - Test error responses (401, 429, 500)
  - _Requirements: 3.1, 3.2, 4.1, 6.1, 6.2_

- [ ] **7.3 Write unit tests for error classification**
  - Test `requires_reauth()` for all error variants
  - Test `is_retryable()` for transient errors
  - Test error message formatting
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] **7.4 Add inline documentation**
  - Document public types with rustdoc comments
  - Document error conditions and recovery strategies
  - Add examples in doc comments
  - Run `cargo doc` and verify output
  - _Requirements: All_

---

## Task Dependencies

```
Phase 1 (Embed)
    │
    ▼
Phase 2 (Storage) ──────┐
    │                   │
    ▼                   ▼
Phase 3 (OAuth) ◀── Phase 4 (Client)
    │                   │
    └───────┬───────────┘
            ▼
      Phase 5 (Provider)
            │
            ▼
      Phase 6 (Commands)
            │
            ▼
      Phase 7 (Testing)
```

## Task Sizing Guidelines

Each numbered task (e.g., 1.1, 2.3) is designed to be completable in 1-4 hours of focused work. Tasks include:
- Implementation of the specified component
- Unit tests for the component
- Basic documentation

If a task takes significantly longer, it should be split into sub-tasks.

## Progress Tracking

Use this checklist format to track implementation progress:

- [x] Task completed and tested
- [ ] Task not started
- [~] Task in progress

Update this document as tasks are completed to maintain visibility into implementation status.
