# Implementation Tasks

## Overview

Sequenced tasks for refactoring `commands_legacy.rs` into domain modules.
Estimated total: 6-7 weeks.

---

## Phase 1: Infrastructure Setup

### Task 1.1: Create Shared Types Module
**Priority**: High | **Effort**: 2h
- [ ] Create `commands/types.rs`
- [ ] Extract shared request/response types from legacy
- [ ] Add serde derive macros with camelCase
- [ ] Update imports in legacy file

### Task 1.2: Relocate AppState
**Priority**: High | **Effort**: 3h
- [ ] Create `commands/state.rs`
- [ ] Move AppState struct definition
- [ ] Move `init_defaults()` function
- [ ] Update imports across codebase

### Task 1.3: Extend CommandError
**Priority**: High | **Effort**: 1h
- [ ] Add domain variants to `commands/error.rs`
- [ ] Implement `From<CommandError> for String`
- [ ] Add From impls for common error types

### Task 1.4: Update Module Structure
**Priority**: High | **Effort**: 1h
- [ ] Update `commands/mod.rs` with new module declarations
- [ ] Add placeholder mod.rs for each domain
- [ ] Verify compilation

---

## Phase 2: Low-Risk Modules

### Task 2.1: Extract System Module
**Priority**: Medium | **Effort**: 1h
- [ ] Create `commands/system/mod.rs`
- [ ] Create `commands/system/info.rs`
- [ ] Create `commands/system/audio.rs`
- [ ] Move 4 commands: get_app_version, get_app_system_info, get_audio_volumes, get_sfx_categories
- [ ] Add re-exports to mod.rs

### Task 2.2: Extract Credentials Module
**Priority**: Medium | **Effort**: 1h
- [ ] Create `commands/credentials/mod.rs`
- [ ] Create `commands/credentials/keys.rs`
- [ ] Move 4 commands: save_api_key, get_api_key, delete_api_key, list_stored_providers
- [ ] Add re-exports

### Task 2.3: Extract Usage Module
**Priority**: Medium | **Effort**: 2h
- [ ] Create `commands/usage/mod.rs`
- [ ] Create `commands/usage/stats.rs`
- [ ] Create `commands/usage/budget.rs`
- [ ] Move 7 commands
- [ ] Handle UsageTrackerState reference

### Task 2.4: Extract Audit Module
**Priority**: Medium | **Effort**: 2h
- [ ] Create `commands/audit/mod.rs`
- [ ] Create `commands/audit/logs.rs`
- [ ] Create `commands/audit/export.rs`
- [ ] Move 6 commands
- [ ] Handle AuditLoggerState reference

**Phase 2 Checkpoint**: Run `cargo test`, verify all commands work

---

## Phase 3: Medium-Risk Modules

### Task 3.1: Extract World Module
**Priority**: Medium | **Effort**: 3h
- [ ] Create `commands/world/mod.rs`
- [ ] Create submodules: state.rs, calendar.rs, locations.rs, events.rs
- [ ] Move 13 commands
- [ ] Add re-exports

### Task 3.2: Extract Relationships Module
**Priority**: Medium | **Effort**: 2h
- [ ] Create `commands/relationships/mod.rs`
- [ ] Create submodules: crud.rs, queries.rs, graph.rs
- [ ] Move 8 commands
- [ ] Add re-exports

### Task 3.3: Extract Timeline Module
**Priority**: Medium | **Effort**: 1h
- [ ] Create `commands/timeline/mod.rs`
- [ ] Create `commands/timeline/events.rs`
- [ ] Move 4 commands
- [ ] Add re-exports

### Task 3.4: Extract Generation Module
**Priority**: Medium | **Effort**: 2h
- [ ] Create `commands/generation/mod.rs`
- [ ] Create submodules: character.rs, location.rs
- [ ] Move 6 commands (4 character, 2 location gen)
- [ ] Add re-exports

**Phase 3 Checkpoint**: Run `cargo test`, verify commands work

---

## Phase 4: High-Complexity Modules

### Task 4.1: Extract Campaign Module
**Priority**: High | **Effort**: 4h
- [ ] Create `commands/campaign/mod.rs`
- [ ] Create submodules: crud.rs, notes.rs, theme.rs, import_export.rs, versioning.rs, snapshots.rs
- [ ] Move ~25 commands
- [ ] Extract campaign-specific types to types.rs if needed
- [ ] Add re-exports

### Task 4.2: Extract Session Module
**Priority**: High | **Effort**: 3h
- [ ] Create `commands/session/mod.rs`
- [ ] Create submodules: crud.rs, planned.rs, chat.rs, notes.rs
- [ ] Move ~20 commands
- [ ] Handle AI categorization (async)
- [ ] Add re-exports

### Task 4.3: Extract Combat Module
**Priority**: High | **Effort**: 3h
- [ ] Create `commands/combat/mod.rs`
- [ ] Create submodules: state.rs, combatants.rs, conditions.rs
- [ ] Move ~20 commands
- [ ] Handle condition duration parsing
- [ ] Add re-exports

### Task 4.4: Extract NPC Module
**Priority**: High | **Effort**: 4h
- [ ] Create `commands/npc/mod.rs`
- [ ] Create submodules: crud.rs, conversations.rs, personality.rs, indexing.rs
- [ ] Create `commands/npc/extensions/` with vocabulary.rs, names.rs, dialects.rs
- [ ] Move ~33 commands
- [ ] Add re-exports

### Task 4.5: Extract Location Module
**Priority**: High | **Effort**: 3h
- [ ] Create `commands/location/mod.rs`
- [ ] Create submodules: crud.rs, connections.rs, details.rs, types.rs
- [ ] Move ~18 commands
- [ ] Add re-exports

### Task 4.6: Extract Personality Module
**Priority**: High | **Effort**: 4h
- [ ] Create `commands/personality/mod.rs`
- [ ] Create types.rs with all request/response types
- [ ] Create submodules: profiles.rs, templates.rs, blending.rs, context.rs, styling.rs
- [ ] Move ~35 commands
- [ ] Add re-exports

### Task 4.7: Extract Search Module
**Priority**: High | **Effort**: 5h
- [ ] Create `commands/search/mod.rs`
- [ ] Create types.rs
- [ ] Create submodules: basic.rs, hybrid.rs, analytics.rs, ingestion.rs, library.rs, ttrpg.rs, meilisearch.rs, extraction.rs
- [ ] Move ~40 commands
- [ ] Handle SearchAnalyticsState reference
- [ ] Add re-exports

**Phase 4 Checkpoint**: Full test suite, verify all commands

---

## Phase 5: LLM Module (High Risk)

### Task 5.1: Extract LLM Types
**Priority**: High | **Effort**: 2h
- [ ] Create `commands/llm/types.rs`
- [ ] Extract ChatRequestPayload, ChatResponsePayload
- [ ] Extract embedding types
- [ ] Add serde derives

### Task 5.2: Extract LLM Config
**Priority**: High | **Effort**: 2h
- [ ] Create `commands/llm/config.rs`
- [ ] Move configure_llm, check_llm_health, get_llm_config
- [ ] Move router commands: get_router_stats, set_routing_strategy, etc.
- [ ] Move config persistence helpers

### Task 5.3: Extract Chat Commands
**Priority**: High | **Effort**: 2h
- [ ] Create `commands/llm/chat.rs`
- [ ] Move chat() command
- [ ] Verify RAG integration works

### Task 5.4: Extract Streaming Commands (Critical)
**Priority**: Critical | **Effort**: 3h
- [ ] Create `commands/llm/streaming.rs`
- [ ] Move stream_chat() with tokio::spawn logic
- [ ] Move cancel_stream, get_active_streams
- [ ] **TEST**: Verify Tauri event emission works
- [ ] **TEST**: Verify stream cancellation works

### Task 5.5: Extract Model Listing
**Priority**: High | **Effort**: 2h
- [ ] Create `commands/llm/models.rs`
- [ ] Move all list_*_models commands
- [ ] Verify fallback chains work

### Task 5.6: Extract Embeddings
**Priority**: High | **Effort**: 2h
- [ ] Create `commands/llm/embeddings.rs`
- [ ] Move configure_meilisearch_embedder, setup_* commands
- [ ] Move dimension lookup helper

### Task 5.7: Extract Model Selection
**Priority**: Medium | **Effort**: 1h
- [ ] Create `commands/llm/selection.rs`
- [ ] Move get_model_selection, set_model_override
- [ ] Add re-exports

**Phase 5 Checkpoint**: Full streaming test, verify chat works

---

## Phase 6: Cleanup

### Task 6.1: Delete Legacy File
**Priority**: High | **Effort**: 1h
- [ ] Verify all commands moved
- [ ] Remove `#[path = "../commands_legacy.rs"]` from mod.rs
- [ ] Delete `commands_legacy.rs`
- [ ] Run full test suite

### Task 6.2: Documentation
**Priority**: Medium | **Effort**: 2h
- [ ] Add module-level doc comments
- [ ] Update CLAUDE.md with new structure
- [ ] Document command module patterns

### Task 6.3: Final Verification
**Priority**: High | **Effort**: 2h
- [ ] Run `cargo clippy`
- [ ] Run `cargo fmt`
- [ ] Run full test suite
- [ ] Test frontend integration
- [ ] Verify build time acceptable

---

## Summary

| Phase | Tasks | Estimated Hours |
|-------|-------|-----------------|
| 1. Infrastructure | 4 | 7h |
| 2. Low-Risk | 4 | 6h |
| 3. Medium-Risk | 4 | 8h |
| 4. High-Complexity | 7 | 26h |
| 5. LLM Module | 7 | 14h |
| 6. Cleanup | 3 | 5h |
| **Total** | **29** | **~66h** |

---

## Dependencies Graph

```
Phase 1 (Infrastructure)
    │
    ├──> Phase 2 (Low-Risk) ──> Phase 3 (Medium-Risk)
    │                                  │
    └──────────────────────────────────┴──> Phase 4 (High-Complexity)
                                                │
                                                ├──> Phase 5 (LLM)
                                                │
                                                └──> Phase 6 (Cleanup)
```

---

## Risk Log

| Task | Risk | Mitigation |
|------|------|-----------|
| 5.4 Streaming | Event emission may break | Test immediately, keep fallback |
| 4.6 Personality | Complex interdependencies | Extract types first |
| 4.7 Search | Large module (40 commands) | Split carefully by function |
| 6.1 Delete Legacy | Missing command | Verify with grep before delete |
