# LLM Router Consolidation Analysis

## Executive Summary

The codebase has **two separate router files** that evolved independently:
- `core/llm/router.rs` (2,563 lines) - The canonical, trait-based LLM router
- `core/llm_router.rs` (2,131 lines) - A legacy/parallel implementation

After analysis, **`llm_router.rs` appears to be entirely unused/dead code** - a remnant of an earlier implementation or migration that was never deleted. The active system uses `core/llm/router.rs` exclusively.

---

## Current Architecture

### `core/llm/router.rs` (Active, Canonical)

**Purpose:** The primary LLM routing system used throughout the application.

**Responsibilities:**
- Defines the `LLMProvider` trait (lines 95-162) that all providers implement
- Core request/response types: `ChatRequest`, `ChatResponse`, `ChatMessage`, `ChatChunk`
- `LLMRouter` struct with multi-provider orchestration
- `RouterConfig` for configuring timeouts, fallback, routing strategies
- `RoutingStrategy` enum: Priority, RoundRobin, CostOptimized, LatencyOptimized, Random
- `ProviderStats` for tracking request success rates, latency, token usage
- Integration with `cost.rs` and `health.rs` modules
- `LLMRouterBuilder` for fluent construction

**Key Types Defined:**
```rust
pub enum LLMError { HttpError, ApiError, AuthError, RateLimited, InvalidResponse, ... }
pub trait LLMProvider: Send + Sync { fn id(), chat(), stream_chat(), embeddings(), ... }
pub struct LLMRouter { providers, stats, health_tracker, cost_tracker, config }
pub struct ChatRequest { messages, system_prompt, temperature, max_tokens, tools, ... }
pub struct ChatResponse { content, model, provider, usage, tool_calls, cost_usd, ... }
```

### `core/llm_router.rs` (Legacy/Dead Code)

**Purpose:** Appears to be an older implementation that was superseded.

**Responsibilities (duplicated from router.rs):**
- Re-defines `LLMProvider` trait with nearly identical signature
- Re-defines `ChatRequest`, `ChatResponse`, `ChatMessage`, `ChatChunk`
- Re-defines `LLMError` enum
- Contains its own `LLMRouter` implementation
- Has parallel routing strategies and configuration

**Evidence of Dead Code:**
1. The `core/llm/mod.rs` exports from `router.rs`, not `llm_router.rs`
2. All provider implementations import from `crate::core::llm::router`
3. No imports of `crate::core::llm_router` found in provider files
4. Types would conflict if both were used (same names, different definitions)

### Relationship

These files do NOT interact - they are parallel implementations. The `core/llm/router.rs` is the active system, while `core/llm_router.rs` is legacy code that should be removed.

---

## Code Duplication Found

### Pattern 1: LLMError Enum

**Location A:** `core/llm/router.rs:27-78`
**Location B:** `core/llm_router.rs` (similar location)

**Duplicated functionality:**
```rust
pub enum LLMError {
    HttpError(#[from] reqwest::Error),
    ApiError { status: u16, message: String },
    AuthError(String),
    RateLimited { retry_after_secs: u64 },
    InvalidResponse(String),
    NotConfigured(String),
    EmbeddingNotSupported(String),
    StreamingNotSupported(String),
    Timeout,
    AllProvidersFailed(String),
    NoProvidersAvailable,
    BudgetExceeded(String),
}
```

Both files define identical error types.

### Pattern 2: LLMProvider Trait

**Location A:** `core/llm/router.rs:95-162`
**Location B:** `core/llm_router.rs` (similar)

**Duplicated functionality:**
```rust
#[async_trait]
pub trait LLMProvider: Send + Sync {
    fn id(&self) -> &str;
    fn name(&self) -> &str;
    fn model(&self) -> &str;
    async fn health_check(&self) -> bool;
    fn pricing(&self) -> Option<ProviderPricing>;
    async fn chat(&self, request: ChatRequest) -> Result<ChatResponse>;
    async fn stream_chat(&self, request: ChatRequest) -> Result<mpsc::Receiver<Result<ChatChunk>>>;
    async fn embeddings(&self, text: String) -> Result<Vec<f32>>;
    fn supports_streaming(&self) -> bool;
    fn supports_embeddings(&self) -> bool;
}
```

### Pattern 3: Chat Message/Request/Response Types

**Location A:** `core/llm/router.rs:164-350`
**Location B:** `core/llm_router.rs` (similar)

**Duplicated functionality:**
- `MessageRole` enum (System, User, Assistant)
- `ChatMessage` struct with constructors
- `ChatRequest` builder pattern
- `ChatResponse` struct
- `ChatChunk` for streaming

### Pattern 4: Router Configuration and Strategies

**Location A:** `core/llm/router.rs:400-500`
**Location B:** `core/llm_router.rs` (similar)

**Duplicated functionality:**
- `RouterConfig` struct
- `RoutingStrategy` enum
- `ProviderStats` tracking

---

## Provider Implementation Patterns

### Common Patterns Across Providers

1. **OpenAI-Compatible Base Class**
   - `OpenAICompatibleProvider` in `openai.rs` (lines 442-731)
   - Used by: Groq, Together, DeepSeek, Cohere, Mistral, OpenRouter
   - Pattern: Composition via `inner: OpenAICompatibleProvider`

2. **OAuth Storage Abstraction**
   - Claude, Gemini, Copilot all implement identical storage backend patterns
   - Each has: `StorageBackend` enum (File, Keyring, Memory, Auto)
   - Each has: `*ClientTrait` wrapper trait for type-erased client
   - Each has: Identical wrapper structs (FileStorageClient, KeyringStorageClient, MemoryStorageClient)

3. **Message Building**
   - Every provider has `build_messages(&self, request: &ChatRequest)` method
   - Nearly identical logic with provider-specific API format differences
   - Duplicated: system prompt handling, role mapping, image handling

4. **Stream Processing**
   - SSE parsing loop duplicated in every streaming provider
   - Pattern: `while let Some(item) = stream.next().await { parse "data: " lines }`
   - Token usage extraction from final chunks

### Potential Trait Abstractions

1. **`OAuthProvider` Trait**
   ```rust
   trait OAuthProvider: LLMProvider {
       fn storage_backend(&self) -> &str;
       async fn is_authenticated(&self) -> Result<bool>;
       async fn start_oauth_flow(&self) -> Result<String>;
       async fn complete_oauth_flow(&self, code: &str) -> Result<()>;
       async fn logout(&self) -> Result<()>;
       async fn get_status(&self) -> ProviderStatus;
   }
   ```
   Would unify: Claude, Gemini, Copilot

2. **`ApiKeyProvider` Trait**
   ```rust
   trait ApiKeyProvider: LLMProvider {
       fn api_key(&self) -> &str;
       fn base_url(&self) -> &str;
   }
   ```
   Would unify: OpenAI, Groq, Together, DeepSeek, Mistral, etc.

3. **`SSEStreamParser` Utility**
   - Extract SSE parsing into a reusable async stream adapter
   - Would eliminate ~100 lines of duplicated streaming code per provider

4. **`TokenStorage` Trait Consolidation**
   - The `*ClientTrait` wrappers in Claude/Gemini/Copilot are identical
   - Could use a macro or generic implementation

---

## Proposed Consolidation

### Phase 1: Remove Dead Code (Immediate)

1. **Delete `core/llm_router.rs`** - entirely unused
2. Verify no imports reference it (already confirmed)
3. Lines saved: ~2,131

### Phase 2: Extract Shared OAuth Infrastructure

1. Create `core/llm/oauth/mod.rs` with:
   - Generic `StorageBackend` enum (move from each provider)
   - `OAuthProvider` trait definition
   - Generic `OAuthStatus` struct
   - `OAuthClientWrapper<S: TokenStorage>` generic wrapper

2. Refactor Claude, Gemini, Copilot to use shared infrastructure:
   - Each provider becomes ~300 lines instead of ~1000
   - OAuth flow handling centralized

### Phase 3: Consolidate OpenAI-Compatible Providers

1. The `OpenAICompatibleProvider` pattern is already good
2. Remaining providers (Groq, Together, etc.) are thin wrappers (~90 lines each)
3. Consider a macro for the boilerplate:
   ```rust
   openai_compatible_provider!(GroqProvider, "groq", "Groq", "https://api.groq.com/openai/v1");
   ```

### Phase 4: Stream Parsing Utilities

1. Create `core/llm/streaming.rs`:
   - `parse_sse_stream()` generic function
   - `OpenAIStreamParser`, `ClaudeStreamParser` adapters
   - Reduce per-provider streaming code by ~50 lines each

---

## Estimated Savings

### Lines Removable

| Change | Lines Saved |
|--------|-------------|
| Delete `llm_router.rs` | ~2,131 |
| OAuth infrastructure consolidation | ~400 (across 3 providers) |
| Stream parsing utilities | ~300 (across 10+ providers) |
| **Total** | **~2,831** |

### Complexity Reduction

1. **Single Source of Truth**: One router, one set of types
2. **DRY OAuth**: OAuth flow logic in one place, not three
3. **Testability**: Shared infrastructure means shared tests
4. **Maintenance**: Bug fixes in one place propagate everywhere

### Risk Assessment

- **Phase 1 (delete llm_router.rs)**: Zero risk - unused code
- **Phase 2 (OAuth)**: Medium risk - careful testing needed for auth flows
- **Phase 3 (OpenAI macro)**: Low risk - thin wrapper simplification
- **Phase 4 (streaming)**: Medium risk - streaming edge cases

---

## Files Analyzed

```
src-tauri/src/core/
├── llm/
│   ├── mod.rs           (exports)
│   ├── router.rs        (2,563 lines - ACTIVE)
│   ├── cost.rs          (794 lines)
│   ├── health.rs        (~500 lines)
│   ├── client.rs        (HTTP utilities)
│   └── providers/
│       ├── mod.rs       (323 lines - config enum)
│       ├── openai.rs    (868 lines)
│       ├── claude.rs    (1,136 lines)
│       ├── gemini.rs    (~1,000 lines)
│       ├── copilot.rs   (~1,000 lines)
│       ├── groq.rs      (90 lines - uses OpenAI base)
│       ├── together.rs  (~90 lines)
│       ├── deepseek.rs  (~90 lines)
│       ├── mistral.rs   (~90 lines)
│       ├── cohere.rs    (~150 lines)
│       ├── openrouter.rs (~150 lines)
│       ├── ollama.rs    (~200 lines)
│       ├── google.rs    (~300 lines)
│       └── meilisearch.rs (~200 lines)
└── llm_router.rs        (2,131 lines - DEAD CODE)
```

---

## Recommendation

**Immediate action**: Delete `core/llm_router.rs` - it's dead code adding 2,131 lines of confusion.

**Short-term**: Extract OAuth infrastructure to reduce Claude/Gemini/Copilot code by ~400 lines total.

**Long-term**: Create stream parsing utilities once the OAuth refactor proves the pattern works.
