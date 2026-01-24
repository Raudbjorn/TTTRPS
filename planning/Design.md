# Design: GitHub Copilot API Integration

## Overview

This document describes the technical architecture for integrating `copilot-api-rs` into the TTRPG Assistant as a third OAuth-based LLM provider. The design follows the established "tri-gate" pattern, where each OAuth provider (Claude, Gemini, Copilot) shares common infrastructure for storage, authentication flow orchestration, and LLM routing. (Note: OpenAI and Ollama use separate API-key authentication and are not part of the gate module.)

### Design Goals

- **Consistency**: Follow existing patterns from `claude-gate` and `antigravity-gate` integrations
- **Minimal Coupling**: CopilotProvider depends only on `LLMProvider` trait, not other providers
- **Storage Reuse**: Share `TokenStorage` trait and implementations across all OAuth providers
- **Type Safety**: Compile-time guarantees for request/response conversions
- **Async-First**: Full tokio integration, no blocking operations

### Key Design Decisions

- **Embedded Library**: Copy `copilot-api-rs` into `src-tauri/src/gate/copilot/` following existing pattern
- **Unified TokenInfo**: Extend existing `TokenInfo` with optional `provider` field to distinguish tokens
- **Provider Trait**: Implement `OAuthProvider` trait for CopilotProvider to enable shared auth flow
- **Type Aliases**: Provide convenience types like `CopilotFileGate`, `CopilotMemoryGate`

## Architecture

### System Overview

The integration adds Copilot as a third authentication gate alongside Claude and Gemini:

```
┌─────────────────────────────────────────────────────────────┐
│                    TTRPG Assistant                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Tauri Commands │  │   Leptos UI     │                  │
│  │  (commands.rs)  │  │   (frontend)    │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                            │
│           ▼                    ▼                            │
│  ┌──────────────────────────────────────────┐              │
│  │              LLM Router                   │              │
│  │  (core/llm_router.rs)                    │              │
│  │  - Provider selection                     │              │
│  │  - Cost tracking                          │              │
│  │  - Failover logic                         │              │
│  └──────────────────┬───────────────────────┘              │
│                     │                                       │
│    ┌────────────────┼────────────────┐                     │
│    ▼                ▼                ▼                     │
│ ┌──────┐      ┌──────────┐     ┌──────────┐               │
│ │Claude│      │  Gemini  │     │ Copilot  │   ◀── NEW    │
│ │Gate  │      │   Gate   │     │   Gate   │               │
│ └──┬───┘      └────┬─────┘     └────┬─────┘               │
│    │               │                │                      │
│    └───────────────┼────────────────┘                      │
│                    ▼                                        │
│         ┌──────────────────────┐                           │
│         │   TokenStorage       │                           │
│         │   (Shared Trait)     │                           │
│         │   - File             │                           │
│         │   - Memory           │                           │
│         │   - Keyring          │                           │
│         │   - Callback         │                           │
│         └──────────────────────┘                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
src-tauri/src/
├── gate/
│   ├── mod.rs                    # Unified exports, type aliases
│   ├── token.rs                  # Unified TokenInfo (add provider field)
│   ├── storage/                  # Shared TokenStorage trait + impls
│   │   ├── mod.rs
│   │   ├── file.rs
│   │   ├── memory.rs
│   │   ├── keyring.rs
│   │   └── callback.rs
│   ├── auth/                     # Shared OAuthFlow<S, P> orchestration
│   │   ├── mod.rs
│   │   └── flow.rs
│   ├── providers/
│   │   ├── mod.rs
│   │   ├── claude.rs             # OAuthProvider for Claude
│   │   ├── gemini.rs             # OAuthProvider for Gemini
│   │   └── copilot.rs            # OAuthProvider for Copilot  ◀── NEW
│   ├── claude/                   # Claude-specific types (existing)
│   ├── gemini/                   # Gemini-specific types (existing)
│   └── copilot/                  # Copilot-specific types      ◀── NEW
│       ├── mod.rs                # Re-exports
│       ├── client.rs             # CopilotClient wrapper
│       ├── auth/
│       │   ├── mod.rs
│       │   ├── device_flow.rs    # Device Code OAuth
│       │   ├── token_exchange.rs # GitHub → Copilot token
│       │   └── refresh.rs        # Token refresh logic
│       ├── models/
│       │   ├── mod.rs
│       │   ├── auth.rs           # TokenInfo, OAuth responses
│       │   ├── chat.rs           # Message, Role, Content
│       │   └── streaming.rs      # StreamChunk, SSE parsing
│       ├── transform/
│       │   ├── mod.rs
│       │   ├── openai.rs         # OpenAI ↔ internal format
│       │   └── anthropic.rs      # Anthropic ↔ internal format
│       └── error.rs              # Copilot-specific errors
│
├── core/llm/
│   ├── providers/
│   │   ├── mod.rs
│   │   ├── claude.rs             # LLMProvider for Claude (existing)
│   │   ├── gemini.rs             # LLMProvider for Gemini (existing)
│   │   └── copilot.rs            # LLMProvider for Copilot  ◀── NEW
│   └── ...
│
└── commands.rs                   # Add Copilot auth commands
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Async Runtime | tokio 1.x | Already in use, full feature set |
| HTTP Client | reqwest 0.12 | Already in use, streaming + TLS |
| Serialization | serde + serde_json | Already in use, derive macros |
| Async Traits | async-trait 0.1 | Already in use for TokenStorage |
| Error Handling | thiserror | Already in use, derive macro |
| Keyring | keyring 3 (optional) | Already feature-gated |

## Components and Interfaces

### CopilotProvider (OAuthProvider Implementation)

**Purpose:** Implement the shared `OAuthProvider` trait for GitHub Copilot OAuth.

**Responsibilities:**
- Provide Copilot-specific OAuth configuration (client ID, URLs, scopes)
- Build authorization URLs for Device Code flow
- Exchange device codes for tokens
- Refresh expired tokens

**Interface:**
```rust
pub struct CopilotProvider;

#[async_trait]
impl OAuthProvider for CopilotProvider {
    fn provider_id(&self) -> &str { "copilot" }
    fn name(&self) -> &str { "GitHub Copilot" }
    fn oauth_config(&self) -> CopilotOAuthConfig { /* ... */ }

    async fn initiate_device_flow(&self, http: &Client)
        -> Result<DeviceFlowPending>;

    async fn poll_device_flow(&self, http: &Client, pending: &DeviceFlowPending)
        -> Result<PollResult>;

    async fn exchange_github_token(&self, http: &Client, github_token: &str)
        -> Result<TokenInfo>;

    async fn refresh_token(&self, http: &Client, refresh: &str)
        -> Result<TokenInfo>;
}
```

**Implementation Notes:**
- Device Code flow is Copilot-specific (not PKCE like Claude/Gemini)
- Requires two-step exchange: GitHub token → Copilot token
- Poll interval comes from GitHub API response

### CopilotClient (High-Level Client)

**Purpose:** Provide ergonomic API for Copilot chat completions and embeddings.

**Responsibilities:**
- Manage token caching and automatic refresh
- Build and send chat completion requests
- Handle streaming responses
- Cache model list

**Interface:**
```rust
pub struct CopilotClient<S: TokenStorage> {
    storage: Arc<S>,
    config: Config,
    http_client: reqwest::Client,
    token_cache: Arc<RwLock<Option<TokenInfo>>>,
    models_cache: Arc<RwLock<Option<ModelsResponse>>>,
}

impl<S: TokenStorage> CopilotClient<S> {
    pub fn builder() -> CopilotClientBuilder<S>;
    pub async fn is_authenticated(&self) -> Result<bool>;
    pub async fn authenticate(&self) -> Result<DeviceFlowPending>;
    pub async fn poll_authentication(&self, pending: &DeviceFlowPending) -> Result<PollResult>;
    pub async fn logout(&self) -> Result<()>;
    pub fn chat(&self) -> ChatRequestBuilder<'_, S>;
    pub fn embeddings(&self) -> EmbeddingsRequestBuilder<'_, S>;
    pub async fn models(&self) -> Result<ModelsResponse>;
    pub async fn models_cached(&self) -> Result<ModelsResponse>;
    pub async fn usage(&self) -> Result<UsageResponse>;
}
```

### CopilotLLMProvider (LLMProvider Implementation)

**Purpose:** Adapt CopilotClient to the application's LLMProvider trait.

**Responsibilities:**
- Implement `LLMProvider::generate()` for non-streaming requests
- Implement `LLMProvider::generate_stream()` for streaming requests
- Convert between application message format and Copilot format
- Handle authentication state and errors

**Interface:**
```rust
pub struct CopilotLLMProvider {
    client: Arc<dyn CopilotClientTrait>,
    default_model: String,
    max_tokens: u32,
}

#[async_trait]
impl LLMProvider for CopilotLLMProvider {
    fn name(&self) -> &str { "copilot" }

    async fn generate(&self, request: &LLMRequest) -> Result<LLMResponse, LLMError>;

    async fn generate_stream(
        &self,
        request: &LLMRequest
    ) -> Result<Pin<Box<dyn Stream<Item = Result<StreamChunk, LLMError>> + Send>>, LLMError>;

    async fn available_models(&self) -> Result<Vec<ModelInfo>, LLMError>;

    fn supports_streaming(&self) -> bool { true }
    fn supports_tools(&self) -> bool { true }
    fn supports_vision(&self) -> bool { true }
}
```

**Implementation Notes:**
- Type-erase `CopilotClient<S>` via trait object for runtime flexibility
- Factory methods: `new()` (file), `with_keyring()`, `with_memory()`

### Tauri Commands

**Purpose:** Expose Copilot authentication to the frontend.

**Interface:**
```rust
#[tauri::command]
pub async fn start_copilot_auth(
    state: State<'_, AppState>,
) -> Result<DeviceCodeResponse, String>;

#[tauri::command]
pub async fn poll_copilot_auth(
    state: State<'_, AppState>,
    device_code: String,
) -> Result<AuthPollResult, String>;

#[tauri::command]
pub async fn check_copilot_auth(
    state: State<'_, AppState>,
) -> Result<AuthStatus, String>;

#[tauri::command]
pub async fn logout_copilot(
    state: State<'_, AppState>,
) -> Result<(), String>;

#[tauri::command]
pub async fn get_copilot_usage(
    state: State<'_, AppState>,
) -> Result<UsageInfo, String>;
```

## Data Models

### TokenInfo (Extended)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenInfo {
    pub token_type: String,           // "oauth" for all OAuth providers
    pub access_token: String,         // Provider-specific access token
    pub refresh_token: String,        // Provider-specific refresh token
    pub expires_at: i64,              // Unix timestamp
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,     // "anthropic", "google", "github"
}

impl TokenInfo {
    pub fn is_expired(&self) -> bool;
    pub fn needs_refresh(&self) -> bool;  // Within 60-second buffer
    pub fn time_until_expiry(&self) -> Duration;
}
```

### DeviceFlowPending

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceFlowPending {
    pub device_code: String,
    pub user_code: String,
    pub verification_uri: String,
    pub expires_in: u64,
    pub interval: u64,               // Poll interval in seconds
}
```

### PollResult

```rust
#[derive(Debug, Clone)]
pub enum PollResult {
    Success(TokenInfo),
    Pending,                          // Keep polling
    SlowDown(Duration),               // Increase poll interval
    Expired,                          // Device code expired
    Denied,                           // User denied authorization
}
```

### Copilot Chat Types

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatRequest {
    pub model: String,
    pub messages: Vec<Message>,
    pub max_tokens: Option<u32>,
    pub temperature: Option<f32>,
    pub stream: Option<bool>,
    pub tools: Option<Vec<Tool>>,
    pub tool_choice: Option<ToolChoice>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: Role,
    pub content: Content,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<ToolCall>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    System,
    User,
    Assistant,
    Tool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Content {
    Text(String),
    Parts(Vec<ContentPart>),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum ContentPart {
    #[serde(rename = "text")]
    Text { text: String },
    #[serde(rename = "image_url")]
    ImageUrl { image_url: ImageUrl },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    pub id: String,
    pub model: String,
    pub choices: Vec<Choice>,
    pub usage: Usage,
}
```

### StreamChunk

```rust
#[derive(Debug, Clone)]
pub enum StreamChunk {
    Delta { content: String, index: u32 },
    ToolCallDelta { id: String, name: Option<String>, arguments: String },
    FinishReason { reason: String, index: u32 },
    Usage(Usage),
    Done,
}
```

### CopilotError

```rust
#[derive(Debug, thiserror::Error)]
pub enum CopilotError {
    #[error("Not authenticated")]
    NotAuthenticated,

    #[error("Authentication timeout")]
    AuthTimeout,

    #[error("Authorization denied")]
    AuthDenied,

    #[error("GitHub Copilot not enabled for this account")]
    CopilotNotEnabled,

    #[error("Token expired")]
    TokenExpired,

    #[error("Token refresh failed: {0}")]
    RefreshFailed(String),

    #[error("API error: {status} - {message}")]
    Api { status: u16, message: String },

    #[error("Rate limited, retry after {retry_after:?}")]
    RateLimited { retry_after: Option<Duration> },

    #[error("Input too large: {0}")]
    InputTooLarge(String),

    #[error("Storage error: {message} (path: {path:?})")]
    Storage { path: Option<PathBuf>, message: String },

    #[error("Network error: {0}")]
    Network(#[from] reqwest::Error),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Stream error: {0}")]
    Stream(String),
}

impl CopilotError {
    pub fn requires_reauth(&self) -> bool {
        matches!(self,
            Self::NotAuthenticated |
            Self::TokenExpired |
            Self::CopilotNotEnabled |
            Self::AuthDenied
        )
    }

    pub fn is_retryable(&self) -> bool {
        matches!(self, Self::RateLimited { .. } | Self::Network(_))
    }
}
```

## API Design

### Request Headers

Copilot API requires specific headers for authentication and identification:

```
Authorization: Bearer {copilot_token}
Content-Type: application/json
User-Agent: GitHubCopilotChat/0.26.7
Copilot-Integration-Id: vscode-chat
Editor-Version: vscode/1.95.0
Editor-Plugin-Version: copilot-chat/0.26.7
OpenAI-Intent: conversation-panel
X-GitHub-Api-Version: 2022-11-28
X-Request-Id: {uuid}
```

Conditional headers:
```
Copilot-Vision-Request: true          # If message has images
X-Initiator: agent | user             # Request source
```

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://github.com/login/device/code` | POST | Initiate device flow |
| `https://github.com/login/oauth/access_token` | POST | Poll for token |
| `https://api.github.com/copilot_internal/v2/token` | GET | Exchange for Copilot token (internal/undocumented — may change) |
| `https://api.githubcopilot.com/chat/completions` | POST | Chat completions |
| `https://api.githubcopilot.com/embeddings` | POST | Embeddings |
| `https://api.githubcopilot.com/models` | GET | List models |

Account-specific base URLs:
- Individual: `https://api.githubcopilot.com`
- Business: `https://api.business.githubcopilot.com`
- Enterprise: `https://api.enterprise.githubcopilot.com`

## Error Handling

| Category | HTTP Status | User Action | Internal Handling |
|----------|-------------|-------------|-------------------|
| Not Authenticated | N/A | Initiate auth flow | Return `NotAuthenticated` |
| Token Expired | 401 | Auto-refresh | Refresh and retry once |
| Rate Limited | 429 | Wait and retry | Include `retry_after` duration |
| Invalid Input | 400 | Fix request | Return `Api` error with message |
| Server Error | 5xx | Retry later | Return `Api` error, mark retryable |
| Network Failure | N/A | Check connection | Wrap in `Network` error |

### Error Recovery Flow

```
Request
  │
  ├─ Success ─────────────────────► Return Response
  │
  ├─ 401 Unauthorized
  │    │
  │    ├─ Has refresh token ──► Refresh ──► Retry request
  │    │
  │    └─ No refresh token ──► Return NotAuthenticated
  │
  ├─ 429 Rate Limited
  │    │
  │    └─ Parse Retry-After ──► Return RateLimited { retry_after }
  │
  └─ Other Error ──► Return appropriate error variant
```

## Testing Strategy

### Unit Testing

- **Token serialization**: Verify round-trip JSON encoding
- **Error classification**: Test `requires_reauth()` and `is_retryable()`
- **Model alias resolution**: Test short name → full name mapping
- **Content conversion**: Test message format transformations
- **Header construction**: Verify required headers present

### Integration Testing

Using `wiremock` to mock GitHub and Copilot APIs:

- **Device flow success**: Full flow from initiate → poll → exchange
- **Device flow timeout**: Poll until expiration
- **Device flow denial**: User denies authorization
- **Token refresh**: Automatic refresh on 401
- **Chat completion**: Request/response round-trip
- **Streaming**: SSE event parsing and delivery

### Coverage Targets

- Unit tests: 80% line coverage
- Integration tests: All error paths and happy paths
- E2E tests: Manual testing with real Copilot account (optional)

## Security Considerations

### Token Protection

1. **File Permissions**: 0600 on Unix, appropriate ACL on Windows
2. **Memory**: Tokens cleared from cache on logout
3. **Logging**: Token values never logged, even at DEBUG level
4. **Transport**: TLS required for all API calls

### OAuth Security

1. **State Parameter**: Not applicable for Device Code flow
2. **Client ID**: Public (matches VS Code Copilot, no secret needed)
3. **Scope Minimization**: Request only required scopes

### Request Security

1. **Request ID**: UUID per request for tracing
2. **User-Agent**: Consistent with VS Code Copilot
3. **TLS Verification**: Certificate validation enabled

## Compatibility Notes

### Differences from antigravity-gate and claude-gate

| Aspect | Claude/Gemini | Copilot |
|--------|---------------|---------|
| OAuth Flow | PKCE (browser redirect) | Device Code (no browser callback) |
| Token Exchange | Single step | Two-step (GitHub → Copilot) |
| Client Secret | Public (PKCE) | None required |
| Refresh | Using refresh_token | Using refresh_token |
| API Format | Anthropic/Google | OpenAI-compatible |

### Migration Path

If user has existing API key provider for GPT-4o:
1. Keep API key provider as fallback
2. Prefer Copilot provider when authenticated
3. No data migration needed (different auth model)

## Decision Records

### Decision: Device Code Flow vs PKCE

**Context:** Copilot uses Device Code OAuth, unlike Claude/Gemini which use PKCE.

**Options:**
1. Adapt Device Code to look like PKCE in the OAuthProvider trait
2. Extend OAuthProvider trait to support both flows
3. Create separate CopilotOAuthProvider trait

**Decision:** Option 2 - Extend OAuthProvider with optional Device Code methods

**Rationale:**
- Maintains unified auth flow orchestration
- Device Code is fundamentally different (no redirect URI)
- Trait can use default implementations for unsupported flow

### Decision: Embedded vs External Dependency

**Context:** Should copilot-api-rs be a Cargo dependency or embedded?

**Options:**
1. External Cargo dependency from crates.io or git
2. Embedded copy in src-tauri/src/gate/copilot/

**Decision:** Option 2 - Embedded copy

**Rationale:**
- Consistent with claude-gate and antigravity-gate patterns
- Allows local modifications without forking
- Avoids version coordination issues
- Library not yet published to crates.io

### Decision: Type Erasure for LLMProvider

**Context:** CopilotClient is generic over TokenStorage, but LLMProvider needs concrete type.

**Options:**
1. Make LLMProvider generic over storage
2. Type-erase via trait object (`Arc<dyn CopilotClientTrait>`)
3. Create non-generic CopilotClient with enum storage

**Decision:** Option 2 - Type erasure via trait object

**Rationale:**
- Matches existing GeminiProvider pattern
- Allows runtime storage selection
- Keeps LLMProvider interface simple
- Minimal overhead (trait object dispatch)
