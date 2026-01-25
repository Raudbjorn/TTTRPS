# Requirements: Commands Module Refactoring (Phase 2)

## Introduction

The TTRPG Assistant codebase has undergone initial refactoring efforts that successfully extracted `voice/`, `oauth/`, and `archetype/` command modules from the monolithic `commands_legacy.rs` file. However, the legacy file remains at 8303 lines with approximately 310 Tauri commands requiring extraction.

This document specifies requirements for completing the command module extraction using spec-driven development methodology.

---

## Requirements

### Requirement 1: Module Organization by Domain

**User Story:** As a developer, I want Tauri commands grouped into domain-specific modules so that I can find, modify, and test related functionality without navigating a 8000+ line file.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN `commands_legacy.rs` SHALL be deleted and all commands SHALL reside in domain modules under `commands/`
2. WHEN a developer searches for LLM-related commands THEN all commands SHALL be located in `commands/llm/`
3. WHEN a developer searches for campaign-related commands THEN all commands SHALL be located in `commands/campaign/`
4. WHEN a developer searches for session-related commands THEN all commands SHALL be located in `commands/session/`
5. WHEN a developer searches for search/document commands THEN all commands SHALL be located in `commands/search/`
6. WHEN a developer searches for NPC-related commands THEN all commands SHALL be located in `commands/npc/`
7. WHEN a developer searches for personality-related commands THEN all commands SHALL be located in `commands/personality/`

---

### Requirement 2: Backward Compatible Re-Export Pattern

**User Story:** As a developer, I want extracted command modules to use glob re-exports so that the frontend can continue importing commands without path changes.

#### Acceptance Criteria

1. WHEN commands are extracted to domain modules THEN each module's `mod.rs` SHALL use `pub use submodule::*` to re-export all commands
2. WHEN the extraction is complete THEN `commands/mod.rs` SHALL re-export all domain modules
3. WHEN the extraction is complete THEN all existing Tauri command handler registrations in `main.rs` SHALL work without modification

---

### Requirement 3: Type Extraction to Dedicated Files

**User Story:** As a developer, I want request/response types separated from command implementations so that I can understand data contracts independently of business logic.

#### Acceptance Criteria

1. WHEN a domain module has more than 3 request/response types THEN those types SHALL be extracted to a `types.rs` file
2. WHEN types reference core domain models THEN they SHALL implement `From<CoreType>` for conversion
3. WHEN types are shared across multiple domain modules THEN they SHALL be placed in `commands/types.rs`

---

### Requirement 4: Unified CommandError Pattern

**User Story:** As a developer, I want a consistent error handling pattern across all commands so that I can replace repetitive `.map_err(|e| e.to_string())` with ergonomic error propagation.

#### Acceptance Criteria

1. WHEN a command encounters an error THEN it SHALL use `CommandError` variants from `commands/error.rs`
2. WHEN CommandError is used THEN it SHALL implement `From<CommandError> for String` to satisfy Tauri's requirement
3. WHEN existing commands are migrated THEN `.map_err(|e| e.to_string())` patterns SHALL be replaced with `?` operator

---

### Requirement 5: File Size Constraints

**User Story:** As a developer, I want no single command file to exceed 500 lines so that code navigation remains tractable.

#### Acceptance Criteria

1. WHEN a command file is created THEN it SHALL contain no more than 500 lines of code
2. IF a command file approaches 400 lines THEN it SHALL be evaluated for splitting into submodules

---

### Requirement 6: Testability

**User Story:** As a developer, I want each command module to have minimal dependencies so that I can unit test commands in isolation.

#### Acceptance Criteria

1. WHEN a command is extracted THEN it SHALL be testable with a mock AppState
2. WHEN testing a command THEN only the state fields used by that command SHALL need initialization

---

## Non-Functional Requirements

### NFR-1: Maintainability
- No single command file SHALL exceed 500 lines
- Average command file size SHALL be under 200 lines

### NFR-2: Build Performance
- Incremental build time SHALL NOT increase by more than 10%

### NFR-3: Backward Compatibility
- All Tauri command names SHALL remain unchanged
- All command signatures SHALL remain unchanged
- The Leptos frontend SHALL require ZERO modifications

### NFR-4: Test Coverage
- Existing test coverage percentage SHALL NOT decrease
- `cargo test` SHALL pass with no regressions

---

## Domain Module Breakdown

| Domain | Est. Commands | Submodules |
|--------|--------------|------------|
| `llm/` | ~25 | config, chat, router, models, embeddings |
| `campaign/` | ~25 | crud, notes, theme, versioning, snapshots |
| `session/` | ~35 | crud, chat, combat, conditions, timeline, notes |
| `npc/` | ~35 | crud, conversations, extensions, indexing |
| `personality/` | ~35 | profiles, templates, blending, context, styling |
| `search/` | ~40 | basic, hybrid, analytics, ingestion, library |
| `world/` | ~15 | state, calendar, locations, events |
| `relationships/` | ~10 | crud, queries, graph |
| `generation/` | ~10 | character, location |
| `credentials/` | ~5 | keys |
| `usage/` | ~7 | stats, budget |
| `audit/` | ~7 | logs, export |
| `system/` | ~10 | info, audio, browser |

---

## Success Metrics

| Metric | Current State | Target State |
|--------|---------------|--------------|
| `commands_legacy.rs` lines | 8303 | 0 (deleted) |
| Largest command file | 8303 | < 500 |
| Command modules | 3 | 16+ |
| Frontend changes required | N/A | 0 |
| Test regressions | N/A | 0 |

---

## Out of Scope

- Feature additions or behavior changes
- Database schema changes
- UI/UX changes
- Dependency upgrades
- Frontend refactoring
