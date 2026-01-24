# Tasks: Codebase Refactoring Overhaul

## Implementation Overview

This task list implements the refactoring plan from Design.md. The work is organized in nine phases (Phase 0 through Phase 8), progressing from foundational infrastructure through systematic module extraction. Each phase builds on the previous, with validation checkpoints after each major step.

**Total estimated line reduction:** ~8,000-10,000 lines
**Total commands to migrate:** 404

---

## Implementation Plan

### Phase 0: Infrastructure Setup

- [ ] **0.1 Create commands module structure**
  - Create `src-tauri/src/commands/` directory
  - Create `mod.rs` with empty shell
  - Create `error.rs` with `CommandError` enum
  - Create `macros.rs` with state access helpers
  - Update `src-tauri/src/lib.rs` to include new module
  - Verify `cargo check` passes
  - _Requirements: 1.1, 1.6_

- [ ] **0.2 Extract AppState to commands/state.rs**
  - Move AppState struct definition from `commands.rs` lines 1034-1210
  - Move initialization logic
  - Move OAuth client state types (lines 128-1033)
  - Update imports in original `commands.rs`
  - Verify build passes
  - _Requirements: 1.1, 1.4_

- [ ] **0.3 Create shared request/response types**
  - Create `commands/types.rs`
  - Move shared DTOs from `commands.rs` lines 1229-1267
  - Export from `commands/mod.rs`
  - Update imports
  - _Requirements: 1.1_

---

### Phase 1: Dead Code Removal

- [ ] **1.1 Delete unused llm_router.rs**
  - Delete `src-tauri/src/core/llm_router.rs` (2,131 lines)
  - Remove any imports referencing it (none expected)
  - Remove from `core/mod.rs` if present
  - Run `cargo build` to verify no breakage
  - _Requirements: 2.1, 3.1_

- [ ] **1.2 Remove unused functions and fields**
  - Delete `core/llm/providers/claude.rs:181` `storage_name()` method
  - Delete `core/llm/providers/gemini.rs:187` `storage_name()` method
  - Delete `core/llm/providers/copilot.rs:187` `storage_name()` method
  - Delete `core/meilisearch_pipeline.rs:1934` `process_text_file()` method
  - Delete `core/voice/providers/coqui.rs:22` `TtsRequest` struct and `speakers` field
  - Delete `ingestion/claude_extractor.rs:71` `PAGE_EXTRACTION_PROMPT` constant
  - Delete `ingestion/layout/column_detector.rs:17` `DEFAULT_MIN_COLUMN_WIDTH` constant
  - Run `cargo build --all-targets`
  - _Requirements: 2.1, 2.3_

- [ ] **1.3 Fix unused variable warnings**
  - Prefix `system_prompt` with `_` in `commands.rs:1441,1816`
  - Prefix `connection_type`, `description` with `_` in `commands.rs:7550-7551`
  - Prefix `was_pending` with `_` in `core/voice/queue.rs:697`
  - Prefix `query_embedding`, `filter` with `_` in `core/search/hybrid.rs:533,619`
  - Prefix `expected_pages` with `_` in `ingestion/kreuzberg_extractor.rs:411`
  - Prefix `patterns`, `content_type` with `_` in `core/personality/application.rs:769,791`
  - Prefix `options` with `_` in `core/character_gen/mod.rs:318`
  - Prefix `rng` with `_` in `core/location_gen.rs:549,571`
  - Prefix `words` with `_` in `core/query_expansion.rs:195`
  - Prefix `n` with `_` in `core/session/conditions.rs:353`
  - Prefix unused imports in `core/personality/contextual.rs:31`
  - Prefix unused imports in `commands.rs:52`
  - Prefix unused imports in `gate/client.rs:11,14`
  - Prefix `received_done` with `_` in `core/llm/providers/meilisearch.rs:142`
  - Run `cargo build` and verify zero `unused_*` warnings
  - _Requirements: 2.2_

- [ ] **1.4 Remove dead struct fields**
  - Add `#[allow(dead_code)]` or remove `stream_id`, `provider`, `model`, `chunks_received` in `core/llm/router.rs:421` if truly unused
  - Remove `api_key` field in `core/campaign/meilisearch_client.rs:101` if unused
  - Remove `api_key` field in `core/personality/meilisearch.rs:107` if unused
  - Remove `source_archetypes` field in `core/archetype/cache.rs:196` if unused
  - Remove `keyword_rank`, `semantic_rank` fields in `core/search/hybrid.rs:705` if unused
  - Remove unused fields in `core/search/providers/openai.rs:25,37` if safe
  - Run `cargo build` and verify zero `dead_code` warnings for fields
  - _Requirements: 2.1, 2.3_

- [ ] **1.5 Validation checkpoint**
  - Run `cargo build 2>&1 | grep -c "warning:"` should be < 10 (only deprecation warnings)
  - Run `cargo test` - all tests pass
  - Document any warnings that must remain with justification
  - _Requirements: 2.1, 2.2_

---

### Phase 2: OAuth Module Extraction

- [ ] **2.1 Create OAuth trait infrastructure**
  - Create `commands/oauth/mod.rs`
  - Create `commands/oauth/common.rs` with `OAuthGate` trait
  - Create `commands/oauth/state.rs` with `GenericGateState<T>` struct
  - Implement generic methods: `switch_backend`, `start_oauth`, `complete_oauth` (with verification)
  - Define `StorageBackend` enum and `OAuthStatus` struct in `common.rs`
  - _Requirements: 1.3, 3.2_

- [ ] **2.2 Extract Claude OAuth commands**
  - Create `commands/oauth/claude.rs`
  - Move commands from `commands.rs` lines 8164-8397 (~234 lines)
  - Implement `OAuthGate` for Claude client wrapper
  - Move Claude state types from `state.rs`
  - Update `mod.rs` exports
  - Register commands in handler
  - Test OAuth flow works
  - _Requirements: 1.2, 1.7_

- [ ] **2.3 Extract Gemini OAuth commands**
  - Create `commands/oauth/gemini.rs`
  - Move commands from `commands.rs` lines 8398-8590 (~193 lines)
  - Implement `OAuthGate` for Gemini client wrapper
  - Move Gemini state types from `state.rs`
  - Update `mod.rs` exports
  - Test OAuth flow works
  - _Requirements: 1.2, 1.7_

- [ ] **2.4 Extract Copilot OAuth commands**
  - Create `commands/oauth/copilot.rs`
  - Move commands from `commands.rs` lines 8591-8900 (~310 lines)
  - Implement `OAuthGate` for Copilot client wrapper
  - Move Copilot state types from `state.rs`
  - Update `mod.rs` exports
  - Test device code flow works
  - _Requirements: 1.2, 1.7_

- [ ] **2.5 Phase 2 validation**
  - All OAuth commands registered correctly
  - `commands.rs` reduced by ~900 lines
  - OAuth flows tested end-to-end
  - `cargo test` passes
  - _Requirements: 1.6, 1.7_

---

### Phase 3: Large Isolated Module Extraction

- [ ] **3.1 Extract archetype commands**
  - Create `commands/archetype/mod.rs`
  - Create `commands/archetype/crud.rs` - archetype CRUD (~500 lines)
  - Create `commands/archetype/vocabulary.rs` - vocabulary banks (~300 lines)
  - Create `commands/archetype/setting_packs.rs` - setting pack commands (~200 lines)
  - Create `commands/archetype/resolution.rs` - resolution commands (~200 lines)
  - Move commands from `commands.rs` lines 9471-10679 (~1,209 lines)
  - Update handler registration
  - Test archetype functionality
  - _Requirements: 1.2, 1.4_

- [ ] **3.2 Extract personality commands**
  - Create `commands/personality/mod.rs`
  - Create `commands/personality/application.rs` - personality application (~350 lines)
  - Create `commands/personality/templates.rs` - template commands (~200 lines)
  - Create `commands/personality/blending.rs` - blend rules (~200 lines)
  - Create `commands/personality/context.rs` - context detection (~150 lines)
  - Move commands from `commands.rs` lines 7010-7359, 8901-9452 (~900 lines)
  - Update handler registration
  - Test personality features
  - _Requirements: 1.2, 1.4_

- [ ] **3.3 Extract voice commands**
  - Create `commands/voice/mod.rs`
  - Create `commands/voice/config.rs` - configuration (~150 lines)
  - Create `commands/voice/providers.rs` - provider management (~150 lines)
  - Create `commands/voice/synthesis.rs` - TTS synthesis (~200 lines)
  - Create `commands/voice/queue.rs` - voice queue (~350 lines)
  - Create `commands/voice/presets.rs` - voice presets (~150 lines)
  - Create `commands/voice/profiles.rs` - voice profiles (~150 lines)
  - Create `commands/voice/cache.rs` - audio cache (~120 lines)
  - Move scattered voice commands (~1,270 lines total)
  - Update handler registration
  - Test voice synthesis
  - _Requirements: 1.2, 1.4_

- [ ] **3.4 Phase 3 validation**
  - `commands.rs` reduced by ~3,400 lines
  - All extracted commands function correctly
  - `cargo test` passes
  - No new warnings introduced
  - _Requirements: 1.6, 4.5_

---

### Phase 4: Core Module Extraction

- [ ] **4.1 Extract LLM commands**
  - Create `commands/llm/mod.rs`
  - Create `commands/llm/config.rs` - configure_llm, get_llm_config (~150 lines)
  - Create `commands/llm/chat.rs` - chat, stream_chat, cancel_stream (~400 lines)
  - Create `commands/llm/router.rs` - router commands (~200 lines)
  - Create `commands/llm/models.rs` - model listing commands (~150 lines)
  - Create `commands/llm/health.rs` - health check commands (~80 lines)
  - Move commands from `commands.rs` lines 1268-1930 (~662 lines)
  - Update handler registration
  - Test LLM chat works
  - _Requirements: 1.2_

- [ ] **4.2 Extract document commands**
  - Create `commands/documents/mod.rs`
  - Create `commands/documents/ingestion.rs` - document ingestion (~400 lines)
  - Create `commands/documents/search.rs` - search commands (~300 lines)
  - Create `commands/documents/ttrpg.rs` - TTRPG document commands (~150 lines)
  - Create `commands/documents/extraction.rs` - extraction settings (~130 lines)
  - Move commands from scattered locations (~980 lines)
  - Update handler registration
  - Test document ingestion and search
  - _Requirements: 1.2_

- [ ] **4.3 Extract session commands**
  - Create `commands/session/mod.rs`
  - Create `commands/session/crud.rs` - session CRUD (~100 lines)
  - Create `commands/session/chat.rs` - global chat sessions (~160 lines)
  - Create `commands/session/combat.rs` - combat commands (~250 lines)
  - Create `commands/session/conditions.rs` - condition commands (~200 lines)
  - Create `commands/session/timeline.rs` - timeline commands (~120 lines)
  - Create `commands/session/notes.rs` - session notes (~230 lines)
  - Move commands (~1,060 lines)
  - Update handler registration
  - Test session functionality
  - _Requirements: 1.2_

- [ ] **4.4 Phase 4 validation**
  - `commands.rs` reduced by ~2,700 lines
  - Core functionality tested
  - `cargo test` passes
  - _Requirements: 1.6_

---

### Phase 5: Entity Management Extraction

- [ ] **5.1 Extract campaign commands**
  - Create `commands/campaign/mod.rs`
  - Create `commands/campaign/crud.rs` - campaign CRUD (~150 lines)
  - Create `commands/campaign/themes.rs` - theme commands (~80 lines)
  - Create `commands/campaign/snapshots.rs` - snapshot commands (~100 lines)
  - Create `commands/campaign/notes.rs` - campaign notes (~150 lines)
  - Create `commands/campaign/versioning.rs` - version commands (~100 lines)
  - Create `commands/campaign/world_state.rs` - world state commands (~60 lines)
  - Move commands (~640 lines)
  - _Requirements: 1.2_

- [ ] **5.2 Extract NPC commands**
  - Create `commands/npc/mod.rs`
  - Create `commands/npc/generation.rs` - NPC generation (~150 lines)
  - Create `commands/npc/crud.rs` - NPC CRUD (~100 lines)
  - Create `commands/npc/extensions.rs` - vocabulary, names, dialects (~130 lines)
  - Create `commands/npc/conversation.rs` - NPC conversation (~200 lines)
  - Move commands (~580 lines)
  - _Requirements: 1.2_

- [ ] **5.3 Extract location commands**
  - Create `commands/location/mod.rs`
  - Create `commands/location/generation.rs` - location generation (~200 lines)
  - Create `commands/location/crud.rs` - location CRUD (~130 lines)
  - Move commands (~330 lines)
  - _Requirements: 1.2_

- [ ] **5.4 Phase 5 validation**
  - `commands.rs` reduced by ~1,550 lines
  - Entity management tested
  - `cargo test` passes
  - _Requirements: 1.6_

---

### Phase 6: Remaining Modules and Cleanup

- [ ] **6.1 Extract credentials commands**
  - Create `commands/credentials/mod.rs`
  - Create `commands/credentials/management.rs` (~210 lines)
  - Move commands
  - _Requirements: 1.2_

- [ ] **6.2 Extract audio commands**
  - Create `commands/audio/mod.rs`
  - Create `commands/audio/playback.rs` (~160 lines)
  - Move commands
  - _Requirements: 1.2_

- [ ] **6.3 Extract theme commands**
  - Create `commands/theme/mod.rs`
  - Create `commands/theme/commands.rs` (~60 lines)
  - Move commands
  - _Requirements: 1.2_

- [ ] **6.4 Extract utility commands**
  - Create `commands/utility/mod.rs`
  - Create `commands/utility/commands.rs` (~180 lines)
  - Move remaining utility commands
  - _Requirements: 1.2, 1.5_

- [ ] **6.5 Extract meilisearch commands**
  - Create `commands/meilisearch/mod.rs`
  - Create `commands/meilisearch/health.rs` (~60 lines)
  - Create `commands/meilisearch/chat.rs` (~180 lines)
  - Move commands
  - _Requirements: 1.2_

- [ ] **6.6 Extract character commands**
  - Create `commands/character/mod.rs`
  - Create `commands/character/generation.rs` (~50 lines)
  - Move commands
  - _Requirements: 1.2_

- [ ] **6.7 Delete original commands.rs**
  - Verify all 404 commands are registered in new modules
  - Delete `src-tauri/src/commands.rs`
  - Update `lib.rs` and `main.rs` to use `commands/mod.rs`
  - _Requirements: 1.1, 1.6_

- [ ] **6.8 Phase 6 validation**
  - `commands.rs` deleted (0 lines)
  - All 404 commands working
  - `cargo test` passes
  - `cargo build` has zero warnings
  - _Requirements: 1.6, 1.7, 2.1, 2.2_

---

### Phase 7: Frontend Cleanup

- [ ] **7.1 Fix deprecated MaybeSignal usage**
  - Update `frontend/src/components/button.rs:50,53` - replace `MaybeSignal<T>` with `Signal<T>`
  - Update `frontend/src/components/select.rs:60` - replace `MaybeSignal<T>` with `Signal<T>`
  - Update call sites to use new signature
  - Verify build passes
  - _Requirements: 2.5, 6.1_

- [ ] **7.2 Fix deprecated Shell::open usage**
  - Update `commands.rs` (now in `utility/commands.rs`) line 9467
  - Replace `tauri_plugin_shell::Shell::open` with `tauri-plugin-opener`
  - Test URL opening works
  - _Requirements: 2.5_

- [ ] **7.3 Verify bindings generation**
  - Confirm `bindings.rs` regenerates correctly
  - No manual edits needed to bindings
  - Frontend compiles and works
  - _Requirements: 6.3, 6.4_

---

### Phase 8: Final Validation

- [ ] **8.1 Run full test suite**
  - `cargo test --all-targets` passes
  - All integration tests pass
  - Manual smoke test of key features
  - _Requirements: NFR-4_

- [ ] **8.2 Verify metrics**
  - Total backend LOC < 45,000 (target: 15-25% reduction)
  - No file > 1,500 lines (excluding auto-generated)
  - Zero compiler warnings
  - All 404 commands registered
  - _Requirements: NFR-1, NFR-2_

- [ ] **8.3 Documentation update**
  - Update CLAUDE.md with new structure
  - Add comments in `commands/mod.rs` explaining organization
  - _Requirements: 4.6_

- [ ] **8.4 Create PR**
  - Commit all changes
  - Create pull request with summary
  - Request review
  - _Requirements: All_

---

## Summary

| Phase | Tasks | Commands Migrated | Lines Affected |
|-------|-------|-------------------|----------------|
| 0 | 3 | 0 | ~500 (new) |
| 1 | 5 | 0 | -2,500 (removed) |
| 2 | 5 | 18 | ~900 |
| 3 | 4 | 70+ | ~3,400 |
| 4 | 4 | 50+ | ~2,700 |
| 5 | 4 | 40+ | ~1,550 |
| 6 | 8 | 30+ | ~660 |
| 7 | 3 | 0 | ~50 |
| 8 | 4 | 0 | 0 |

**Total tasks:** 40
**Total commands:** 404
**Net LOC reduction:** ~8,000-10,000 lines
