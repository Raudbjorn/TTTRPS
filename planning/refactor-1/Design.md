# Design: Codebase Refactoring Overhaul

## Overview

This document describes the technical design for refactoring the TTRPG Assistant codebase to reduce line count, eliminate dead code, and improve maintainability. The design addresses all requirements from Requirements.md.

### Design Goals

1. **Reduce total LOC by ~15%** (~7,700 lines) through dead code removal and deduplication
2. **Break monolithic files into focused modules** with max 1,500 lines each
3. **Eliminate all compiler warnings** (`dead_code`, `unused_variables`, `deprecated`)
4. **Establish patterns that prevent future bloat** through shared infrastructure

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Domain-based command extraction | Commands naturally group by domain (LLM, voice, campaign); reflects user mental model |
| Delete `llm_router.rs` | Analysis confirms it's entirely unused dead code (2,131 lines) |
| Shared OAuth infrastructure | Three providers duplicate identical patterns; generic trait saves ~600 lines |
| Error type consolidation | 400+ `.map_err()` calls can use a single error type |
| Keep `bindings.rs` as-is | Auto-generated file; manual intervention risks drift |
| Preserve function names | Function names (e.g., `get_campaign`) MUST match the command name to avoid breaking frontend bindings. Do not rename to `get` inside a module unless using `#[tauri::command(rename="...")]`. |

---

## Architecture

### Current State

```
src-tauri/src/
├── commands.rs          # 10,679 lines - ALL Tauri commands
├── main.rs              # 31,242 lines
├── backstory_commands.rs # 15,720 lines (already extracted)
├── core/
│   ├── llm/
│   │   └── router.rs    # 2,563 lines - ACTIVE router
│   ├── llm_router.rs    # 2,131 lines - DEAD CODE
│   └── ... (40+ modules)
└── ...
```

### Target State

```
src-tauri/src/
├── commands/
│   ├── mod.rs           # Registration and re-exports (~200 lines)
│   ├── state.rs         # AppState definition (~200 lines)
│   ├── error.rs         # Unified error types (~50 lines)
│   ├── macros.rs        # Helper macros (~30 lines)
│   ├── llm/             # 5 files, ~980 lines total
│   ├── oauth/           # 4 files, ~850 lines total
│   ├── documents/       # 4 files, ~980 lines total
│   ├── campaign/        # 6 files, ~640 lines total
│   ├── session/         # 6 files, ~1,060 lines total
│   ├── npc/             # 4 files, ~580 lines total
│   ├── voice/           # 7 files, ~1,270 lines total
│   ├── personality/     # 4 files, ~900 lines total
│   ├── archetype/       # 4 files, ~1,200 lines total
│   └── ...              # Remaining small modules
├── main.rs              # Reduced (~500 lines)
├── core/
│   ├── llm/
│   │   └── router.rs    # Unchanged (active implementation)
│   └── ...              # llm_router.rs DELETED
└── ...
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Leptos)                     │
│                       bindings.rs (auto-gen)                │
└─────────────────────────┬───────────────────────────────────┘
                          │ Tauri IPC
┌─────────────────────────▼───────────────────────────────────┐
│                    commands/mod.rs                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │  llm/   │ │ oauth/  │ │campaign/│ │ voice/  │  ...      │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       │           │           │           │                 │
│  ┌────▼───────────▼───────────▼───────────▼────┐           │
│  │              state.rs (AppState)             │           │
│  └──────────────────┬──────────────────────────┘           │
└─────────────────────┼───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                         core/                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ llm/router   │ │session_mgr   │ │ archetype/   │  ...   │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## Components and Interfaces

### Component 1: Unified Error Type (`commands/error.rs`)

**Purpose:** Eliminate repetitive `.map_err(|e| e.to_string())` patterns.

**Interface:**
```rust
#[derive(Debug, thiserror::Error)]
pub enum CommandError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("LLM error: {0}")]
    Llm(#[from] crate::core::llm::LLMError),

    #[error("Voice error: {0}")]
    Voice(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("{0}")]
    Other(String),
}

// Tauri commands require Result<T, String>, so we implement Into<String>
impl From<CommandError> for String {
    fn from(e: CommandError) -> String {
        e.to_string()
    }
}
```

*Note: Tauri IPC requires `Result<T, String>` for command returns. The `From<CommandError> for String` impl enables `?` operator with automatic conversion. Alternative: implement `serde::Serialize` on `CommandError` for richer error payloads.*

**Usage:**
```rust
// Before (400+ instances)
.map_err(|e| e.to_string())

// After
.map_err(CommandError::from)?
// or simply
?  // with proper From impls
```

### Component 2: Shared OAuth Infrastructure (`commands/oauth/common.rs`, `commands/oauth/state.rs`)

**Purpose:** Eliminate triplicated OAuth flow logic AND state management for Claude, Gemini, and Copilot.

**Interface (`commands/oauth/common.rs`):**
```rust
#[async_trait]
pub trait OAuthGate: Send + Sync + 'static {
    fn provider_name(&self) -> &'static str;
    fn storage_backend(&self) -> StorageBackend;
    async fn is_authenticated(&self) -> Result<bool, CommandError>;
    async fn get_status(&self) -> Result<OAuthStatus, CommandError>;
    async fn start_oauth(&self) -> Result<OAuthFlowState, CommandError>;
    async fn complete_oauth(&self, code: &str) -> Result<(), CommandError>;
    async fn logout(&self) -> Result<(), CommandError>;
}

// ... StorageBackend and OAuthStatus enums as before ...
```

**State Abstraction (`commands/oauth/state.rs`):**
```rust
/// Generic state manager for any OAuth provider.
/// Handles backend switching, pending state verification, and client access.
pub struct GenericGateState<T: OAuthGate> {
    client: AsyncRwLock<Option<Box<dyn OAuthGate>>>, // Or specific T if we don't need trait objects here
    pending_oauth_state: AsyncRwLock<Option<String>>,
    storage_backend: AsyncRwLock<StorageBackend>,
    factory: Box<dyn Fn(StorageBackend) -> Result<T, CommandError> + Send + Sync>,
}

impl<T: OAuthGate> GenericGateState<T> {
    pub fn new(backend: StorageBackend, factory: impl Fn...) -> Self { ... }
    pub async fn switch_backend(&self, new_backend: StorageBackend) -> Result<(), CommandError> { ... }
    pub async fn start_oauth(&self) -> Result<(String, String), CommandError> {
        // Common logic: get client -> start flow -> store pending state -> return url
    }
    // ... complete_oauth with state verification implemented ONCE here ...
}
```

**Implementation Notes:**
- `OAuthGate` trait abstracts the *provider API operations*.
- `GenericGateState<T>` abstracts the *application state management* (locks, backend switching, flow verification).
- This removes ~300 lines of duplicated state management code found in `commands.rs`.

### Component 3: Command Module Structure (`commands/`)

**Purpose:** Replace 10,679-line monolith with organized domain modules.

**Module Registration Pattern:**
```rust
// commands/mod.rs
pub fn register_commands(builder: tauri::Builder<tauri::Wry>) -> tauri::Builder<tauri::Wry> {
    builder
        .invoke_handler(tauri::generate_handler![
            // LLM
            llm::configure_llm,
            llm::chat,
            llm::stream_chat,
            // OAuth
            oauth::claude_gate_get_status,
            oauth::claude_gate_start_oauth,
            // ... etc
        ])
}
```

**Domain Modules:** (404 commands total, counts are approximate)

| Module | Commands | Purpose |
|--------|----------|---------|
| `llm/` | ~25 | LLM configuration, chat, streaming, model listing |
| `oauth/` | ~18 | Claude, Gemini, Copilot OAuth flows |
| `documents/` | ~35 | Document ingestion, search, library, extraction settings |
| `campaign/` | ~30 | Campaign CRUD, themes, snapshots, notes, versioning |
| `session/` | ~45 | Sessions, combat, conditions, timeline, notes |
| `npc/` | ~25 | NPC generation, CRUD, vocabulary, conversations |
| `voice/` | ~55 | Voice config, synthesis, queue, presets, profiles, cache |
| `personality/` | ~40 | Personality application, templates, blending, context |
| `archetype/` | ~50 | Archetype CRUD, vocabulary banks, setting packs, resolution |
| `credentials/` | ~10 | API key management |
| `meilisearch/` | ~15 | Meilisearch health and chat integration |
| `audio/` | ~12 | Audio playback controls |
| `theme/` | ~8 | UI theme management |
| `utility/` | ~15 | File dialogs, system utilities |
| `character/` | ~6 | Character generation |
| `location/` | ~15 | Location generation and CRUD |

*Note: Exact counts will be determined during extraction. See commands-analysis.md for detailed breakdown.*

### Component 4: State Access Helpers (`commands/macros.rs`)

**Purpose:** Reduce boilerplate for common state access patterns.

```rust
/// Access read-locked state manager
macro_rules! read_state {
    ($state:expr, $field:ident) => {
        $state.$field.read().await
    };
}

/// Access write-locked state manager
macro_rules! write_state {
    ($state:expr, $field:ident) => {
        $state.$field.write().await
    };
}

/// Execute database operation with connection
macro_rules! with_db {
    ($state:expr, |$conn:ident| $body:expr) => {{
        let db = $state.database.read().await;
        let $conn = db.connection();
        $body
    }};
}
```

---

## Dead Code Elimination

### Confirmed Dead Code (From Analysis)

*Note: Use `cargo clippy` to get current locations as line numbers may shift during refactoring.*

| File | Item | Est. Lines | Action |
|------|------|------------|--------|
| `core/llm_router.rs` | Entire file | 2,131 | DELETE |
| `core/llm/router.rs` | `StreamState` unused fields | ~4 | Prefix `_` or remove |
| `core/llm/providers/claude.rs` | `storage_name()` method | ~10 | DELETE |
| `core/llm/providers/gemini.rs` | `storage_name()` method | ~10 | DELETE |
| `core/llm/providers/copilot.rs` | `storage_name()` method | ~10 | DELETE |
| `core/meilisearch_pipeline.rs` | `process_text_file()` method | ~50 | DELETE |
| `core/voice/providers/coqui.rs` | `TtsRequest` struct | ~20 | DELETE |
| `ingestion/claude_extractor.rs` | `PAGE_EXTRACTION_PROMPT` const | ~10 | DELETE |
| `ingestion/layout/column_detector.rs` | `DEFAULT_MIN_COLUMN_WIDTH` const | ~1 | DELETE |

### Unused Variables (Prefix with `_`)

*Identify via `cargo build` warnings or `cargo clippy`. Common patterns:*

| File | Variables |
|------|-----------|
| `commands.rs` | `system_prompt`, `connection_type`, `description` |
| `core/voice/queue.rs` | `was_pending` |
| `core/search/hybrid.rs` | `query_embedding`, `filter` |
| `ingestion/kreuzberg_extractor.rs` | `expected_pages` |
| `core/personality/application.rs` | `patterns`, `content_type` |
| `core/character_gen/mod.rs` | `options` |
| `core/location_gen.rs` | `rng` |
| `core/query_expansion.rs` | `words` |
| `core/session/conditions.rs` | `n` |

### Deprecated API Usage

| File | Issue | Fix |
|------|-------|-----|
| `frontend/components/button.rs` | `MaybeSignal<T>` | Use `Signal<T>` |
| `frontend/components/select.rs` | `MaybeSignal<T>` | Use `Signal<T>` |
| `commands.rs` | `Shell::open()` deprecated | Use `tauri-plugin-opener` |

---

## Data Flow

### Command Invocation Flow

```
Frontend                 Commands                    Core
   │                        │                         │
   │ invoke("chat", msg)    │                         │
   │───────────────────────>│                         │
   │                        │ state.llm_router        │
   │                        │ .read().await           │
   │                        │────────────────────────>│
   │                        │                         │ router.chat(req)
   │                        │<────────────────────────│
   │                        │                         │
   │ Result<ChatResponse>   │                         │
   │<───────────────────────│                         │
```

### OAuth Flow

```
Frontend                 Commands                OAuth Client
   │                        │                         │
   │ start_oauth()          │                         │
   │───────────────────────>│                         │
   │                        │ OAuthGate::start_oauth()│
   │                        │────────────────────────>│
   │                        │      auth_url           │
   │<───────────────────────│<────────────────────────│
   │                        │                         │
   │ (user completes flow)  │                         │
   │                        │                         │
   │ complete_oauth(code)   │                         │
   │───────────────────────>│                         │
   │                        │ OAuthGate::complete()   │
   │                        │────────────────────────>│
   │                        │        token            │
   │ OAuthStatus            │<────────────────────────│
   │<───────────────────────│                         │
```

---

## Error Handling

| Error Category | HTTP/IPC Equivalent | User Action |
|----------------|---------------------|-------------|
| `NotFound` | 404 | Check input, try again |
| `InvalidInput` | 400 | Correct input format |
| `Database` | 500 | Report bug, check logs |
| `Llm` | 503 | Check provider status |
| `Voice` | 503 | Check voice provider |
| `Other` | 500 | Report bug |

All errors implement `Into<String>` for Tauri IPC compatibility.

---

## Testing Strategy

### Unit Testing

- **Scope:** Individual command functions with mocked state
- **Location:** Co-located in each command module (`#[cfg(test)]`)
- **Coverage Target:** 80% of command logic

```rust
// commands/llm/chat.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_chat_returns_response() {
        let state = mock_app_state();
        let result = chat(state, request).await;
        assert!(result.is_ok());
    }
}
```

### Integration Testing

- **Scope:** Full command flow with real state
- **Location:** `tests/integration/commands/`
- **Focus:** OAuth flows, document ingestion, multi-step operations

### Regression Testing

- **Scope:** All 404 existing commands
- **Method:** Automated IPC validation
- **Criteria:** Command names unchanged, signature compatibility maintained

---

## Migration Strategy

### Phase 0: Infrastructure Setup
1. Create `commands/` directory
2. Add `error.rs`, `state.rs`, `macros.rs`
3. Verify build passes

### Phase 1: Dead Code Removal
1. Delete `core/llm_router.rs`
2. Remove unused functions/fields from clippy output
3. Prefix unused variables with `_`
4. Target: Zero `dead_code` warnings

### Phase 2: OAuth Extraction
1. Create `oauth/common.rs` with `OAuthGate` trait
2. Extract Claude → `oauth/claude.rs`
3. Extract Gemini → `oauth/gemini.rs`
4. Extract Copilot → `oauth/copilot.rs`
5. Update `main.rs` registrations

### Phase 3: Large Module Extraction
1. Extract archetype commands (largest isolated group)
2. Extract personality commands
3. Extract voice commands
4. Validate after each group

### Phase 4: Core Module Extraction
1. Extract LLM commands
2. Extract document commands
3. Extract session commands

### Phase 5: Remaining Modules
1. Extract campaign, NPC, location
2. Extract utilities, audio, theme
3. Final cleanup

### Phase 6: Frontend Updates
1. Migrate `MaybeSignal` → `Signal`
2. Verify bindings still auto-generate correctly

---

## Success Metrics

| Metric | Before | Target | Validation |
|--------|--------|--------|------------|
| `commands.rs` LOC | 10,679 | 0 (extracted) | `wc -l` |
| Total backend LOC | ~51,500 | <44,000 (~15% reduction) | `tokei` |
| Dead code removed | 0 | ~3,000+ lines | `cargo clippy` |
| Compiler warnings | 50+ | 0 | `cargo build` |
| Max file LOC | 10,679 | <1,500 | `wc -l` |
| Command count | 404 | 404 (unchanged) | IPC test |
| Test pass rate | 100% | 100% | `cargo test` |

*The 15% target (~7,700 lines) comes from: dead llm_router.rs (2,131) + command extraction overhead reduction (~1,500) + dead code cleanup (~1,000) + test consolidation (~500) + deduplication savings (~2,500+).*

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking IPC contract | Medium | High | Never rename commands; add aliases if needed |
| Merge conflicts | High | Medium | Feature branch; frequent rebases |
| Missing edge cases | Medium | Medium | Comprehensive test coverage |
| Performance regression | Low | Medium | Benchmark before/after |

---

## Dependencies

This refactoring has no external dependencies. It uses existing:
- `thiserror` for error types
- `tokio` for async runtime
- `serde` for serialization
- All existing Tauri patterns

No new crates required.
