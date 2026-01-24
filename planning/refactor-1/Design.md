# Design: Codebase Refactoring Overhaul

## Overview

This document describes the technical design for refactoring the TTRPG Assistant codebase to reduce line count, eliminate dead code, and improve maintainability. The design addresses all requirements from Requirements.md.

### Design Goals

1. **Reduce total LOC by 15-25%** through dead code removal and deduplication
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

impl From<CommandError> for String {
    fn from(e: CommandError) -> String {
        e.to_string()
    }
}
```

**Usage:**
```rust
// Before (400+ instances)
.map_err(|e| e.to_string())

// After
.map_err(CommandError::from)?
// or simply
?  // with proper From impls
```

### Component 2: Shared OAuth Infrastructure (`commands/oauth/common.rs`)

**Purpose:** Eliminate triplicated OAuth flow logic for Claude, Gemini, and Copilot.

**Interface:**
```rust
pub trait OAuthGate: Send + Sync {
    fn provider_name(&self) -> &'static str;
    fn storage_backend(&self) -> StorageBackend;
    async fn is_authenticated(&self) -> Result<bool, CommandError>;
    async fn get_status(&self) -> Result<OAuthStatus, CommandError>;
    async fn start_oauth(&self) -> Result<OAuthFlowState, CommandError>;
    async fn complete_oauth(&self, code: &str) -> Result<(), CommandError>;
    async fn logout(&self) -> Result<(), CommandError>;
}

#[derive(Clone, Serialize, Deserialize)]
pub enum StorageBackend {
    File,
    Keyring,
    Memory,
    Auto,
}

#[derive(Serialize)]
pub struct OAuthStatus {
    pub is_authenticated: bool,
    pub user_email: Option<String>,
    pub expires_at: Option<i64>,
    pub storage_backend: String,
}
```

**Implementation Notes:**
- Each provider (Claude, Gemini, Copilot) implements `OAuthGate`
- Common command wrappers call trait methods
- Provider-specific logic isolated to implementation

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

**Domain Modules:**

| Module | Commands | Purpose |
|--------|----------|---------|
| `llm/` | 15 | LLM configuration, chat, streaming, model listing |
| `oauth/` | 18 | Claude, Gemini, Copilot OAuth flows |
| `documents/` | 12 | Document ingestion, search, extraction settings |
| `campaign/` | 19 | Campaign CRUD, themes, snapshots, notes |
| `session/` | 25 | Sessions, combat, conditions, timeline |
| `npc/` | 15 | NPC generation, CRUD, vocabulary, conversations |
| `voice/` | 30 | Voice config, synthesis, queue, presets, profiles |
| `personality/` | 20 | Personality application, templates, blending |
| `archetype/` | 25 | Archetype CRUD, vocabulary banks, setting packs |
| `credentials/` | 8 | API key management |
| `meilisearch/` | 5 | Meilisearch health and chat integration |
| `audio/` | 8 | Audio playback controls |
| `theme/` | 4 | UI theme management |
| `utility/` | 10 | File dialogs, system utilities |
| `character/` | 2 | Character generation |
| `location/` | 10 | Location generation and CRUD |

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

| File | Item | Lines | Action |
|------|------|-------|--------|
| `core/llm_router.rs` | Entire file | 2,131 | DELETE |
| `core/llm/router.rs:421` | `StreamState` fields | 4 | Prefix `_` |
| `core/llm/providers/claude.rs:181` | `storage_name()` | ~10 | DELETE |
| `core/llm/providers/gemini.rs:187` | `storage_name()` | ~10 | DELETE |
| `core/llm/providers/copilot.rs:187` | `storage_name()` | ~10 | DELETE |
| `core/meilisearch_pipeline.rs:1934` | `process_text_file()` | ~50 | DELETE |
| `core/voice/providers/coqui.rs:22` | `TtsRequest` | ~20 | DELETE |
| `ingestion/claude_extractor.rs:71` | `PAGE_EXTRACTION_PROMPT` | ~10 | DELETE |
| `ingestion/layout/column_detector.rs:17` | `DEFAULT_MIN_COLUMN_WIDTH` | 1 | DELETE |

### Unused Variables (Prefix with `_`)

| File | Variable | Line |
|------|----------|------|
| `commands.rs` | `system_prompt` | 1441, 1816 |
| `commands.rs` | `connection_type`, `description` | 7550-7551 |
| `core/voice/queue.rs` | `was_pending` | 697 |
| `core/search/hybrid.rs` | `query_embedding`, `filter` | 533, 619 |
| `ingestion/kreuzberg_extractor.rs` | `expected_pages` | 411 |
| `core/personality/application.rs` | `patterns`, `content_type` | 769, 791 |
| `core/character_gen/mod.rs` | `options` | 318 |
| `core/location_gen.rs` | `rng` | 549, 571 |
| `core/query_expansion.rs` | `words` | 195 |
| `core/session/conditions.rs` | `n` | 353 |

### Deprecated API Usage

| File | Issue | Fix |
|------|-------|-----|
| `frontend/components/button.rs:50,53` | `MaybeSignal<T>` | Use `Signal<T>` |
| `frontend/components/select.rs:60` | `MaybeSignal<T>` | Use `Signal<T>` |
| `commands.rs:9467` | `Shell::open()` | Use `tauri-plugin-opener` |

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

| Metric | Before | After | Validation |
|--------|--------|-------|------------|
| `commands.rs` LOC | 10,679 | 0 | `wc -l` |
| Total backend LOC | ~51,500 | <45,000 | `tokei` |
| Compiler warnings | 50+ | 0 | `cargo build` |
| Max file LOC | 10,679 | <1,500 | `wc -l` |
| Command count | 404 | 404 | IPC test |
| Test pass rate | 100% | 100% | `cargo test` |

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
