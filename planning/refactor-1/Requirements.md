# Requirements: Codebase Refactoring Overhaul

## Introduction

The TTRPG Assistant (Sidecar DM) codebase has grown to ~86,000 lines of Rust code across backend (Tauri) and frontend (Leptos WASM) components. Organic growth has led to several maintenance challenges:

1. **Monolithic command handler** - `commands.rs` at 10,679 lines contains all Tauri IPC commands in a single file, making navigation, testing, and maintenance difficult.

2. **Code duplication** - Multiple modules implement similar functionality (e.g., vocabulary handling in `ingestion/ttrpg/vocabulary.rs` and `core/archetype/vocabulary.rs`, dual LLM routers in `core/llm/router.rs` and `core/llm_router.rs`).

3. **Dead code accumulation** - Compiler warnings indicate unused constants, variants, functions, and fields across multiple modules that increase cognitive load and binary size.

4. **Large monolithic modules** - Several files exceed 1,500 lines with mixed responsibilities that could be better organized.

This refactoring effort aims to reduce total lines of code by 15-25%, improve modularity, eliminate dead code, and establish patterns that prevent future bloat.

## Requirements

### Requirement 1: Command Module Extraction

**User Story:** As a developer, I want Tauri commands organized into logical domain modules, so that I can find, modify, and test related commands together.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN `src-tauri/src/commands.rs` SHALL be replaced with a `commands/` directory containing domain-specific modules
2. WHEN a developer searches for LLM-related commands THEN all LLM commands SHALL be located in `commands/llm.rs`
3. WHEN a developer searches for database-related commands THEN all database commands SHALL be located in `commands/database.rs`
4. WHEN commands share helper functions THEN those helpers SHALL be extracted to `commands/helpers.rs` or domain-appropriate submodules
5. IF a command group contains fewer than 3 commands THEN those commands MAY remain in a `commands/misc.rs` module
6. WHEN the extraction is complete THEN the total line count of `commands/` SHALL be less than or equal to the original `commands.rs` line count
7. WHEN commands are extracted THEN all existing Tauri command names SHALL remain unchanged to preserve frontend compatibility

---

### Requirement 2: Dead Code Elimination

**User Story:** As a developer, I want unused code removed from the codebase, so that the codebase is easier to understand and produces smaller binaries.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN `cargo build` SHALL produce zero `dead_code` warnings
2. WHEN the refactoring is complete THEN `cargo build` SHALL produce zero `unused_variables` warnings
3. WHEN a function/struct/variant is identified as dead code AND it has no TODO/FIXME comments indicating planned use THEN it SHALL be deleted
4. WHEN a function/struct/variant is identified as dead code AND it has comments indicating planned use THEN it SHALL be prefixed with underscore OR documented in a "planned features" file
5. WHEN deprecated API usage is identified (e.g., `MaybeSignal`) THEN it SHALL be migrated to the recommended replacement
6. IF dead code removal would break public API contracts THEN the removal SHALL be documented and the API SHALL be marked deprecated first

---

### Requirement 3: LLM Router Consolidation

**User Story:** As a developer, I want a single, well-organized LLM routing system, so that adding new providers or modifying routing logic doesn't require changes in multiple places.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN there SHALL be exactly one LLM router module (not two separate implementations)
2. WHEN provider implementations share common patterns THEN those patterns SHALL be extracted to a shared trait or utility module
3. WHEN the consolidation is complete THEN the combined LLM routing code SHALL be at least 20% smaller than the current combined total (~4,694 lines)
4. WHEN a new LLM provider is added THEN it SHALL require implementing only provider-specific logic, not duplicating routing infrastructure
5. IF the two router implementations serve different purposes THEN they SHALL be documented and renamed to reflect their distinct roles

---

### Requirement 4: Large Module Decomposition

**User Story:** As a developer, I want large modules split into focused submodules, so that each file has a single clear responsibility.

#### Acceptance Criteria

1. WHEN a module exceeds 1,000 lines THEN it SHALL be evaluated for extraction into submodules
2. WHEN `database/mod.rs` is refactored THEN it SHALL be split into domain-specific modules (e.g., `database/campaigns.rs`, `database/documents.rs`, `database/npcs.rs`)
3. WHEN `meilisearch_pipeline.rs` is refactored THEN document extraction, chunking, and indexing logic SHALL be in separate modules
4. WHEN vocabulary code exists in multiple locations THEN it SHALL be consolidated into a single `core/vocabulary/` module
5. WHEN the decomposition is complete THEN no source file (excluding auto-generated files) SHALL exceed 1,500 lines
6. WHEN modules are split THEN public API surface visible to other modules SHALL remain stable or be explicitly documented as changed

---

### Requirement 5: Test Organization

**User Story:** As a developer, I want test utilities shared across test files, so that test setup code isn't duplicated and tests are easier to maintain.

#### Acceptance Criteria

1. WHEN test setup patterns are duplicated across 3+ test files THEN they SHALL be extracted to `tests/common/` or `tests/fixtures/`
2. WHEN a test file exceeds 1,500 lines THEN it SHALL be split into focused test modules
3. WHEN tests can be parameterized to cover multiple cases THEN they SHALL use parameterized test macros rather than copy-pasted test functions
4. WHEN dead/disabled tests exist without explanatory comments THEN they SHALL be deleted or documented
5. IF test utilities are extracted THEN all existing tests SHALL continue to pass without modification to test logic

---

### Requirement 6: Frontend Component Patterns

**User Story:** As a developer, I want consistent patterns in Leptos components, so that the frontend codebase is predictable and maintainable.

#### Acceptance Criteria

1. WHEN deprecated Leptos APIs are used (e.g., `MaybeSignal`) THEN they SHALL be migrated to current equivalents (`Signal<T>`)
2. WHEN UI patterns are duplicated across components THEN they SHALL be extracted to shared components in `components/atoms/` or `components/molecules/`
3. WHEN `bindings.rs` is auto-generated THEN the generation process SHALL be documented and the file SHALL not be manually edited
4. IF `bindings.rs` contains manual additions THEN those SHALL be extracted to a separate file
5. WHEN component refactoring is complete THEN all components SHALL follow Leptos 0.7 idioms

---

## Non-Functional Requirements

### NFR-1: Build Performance
- WHEN the refactoring is complete THEN incremental build time SHALL not increase by more than 10%
- WHEN modules are split THEN compilation unit boundaries SHALL be optimized for parallel compilation

### NFR-2: Binary Size
- WHEN dead code is eliminated THEN release binary size SHALL decrease or remain constant
- WHEN the refactoring is complete THEN release binary size SHALL not increase by more than 5%

### NFR-3: API Stability
- WHEN internal refactoring occurs THEN all Tauri command signatures SHALL remain unchanged
- WHEN internal refactoring occurs THEN all public Rust module APIs used by other crates SHALL remain stable or be documented as breaking changes

### NFR-4: Test Coverage
- WHEN code is refactored THEN existing test coverage percentage SHALL not decrease
- WHEN modules are extracted THEN tests SHALL be co-located with the new module structure

---

## Constraints and Assumptions

### Constraints

1. **Frontend/Backend Contract**: Tauri command names and signatures cannot change without coordinated frontend updates
2. **Auto-generated Code**: `frontend/src/bindings.rs` appears to be auto-generated and should not be manually refactored
3. **Feature Flags**: Existing Cargo feature flags must continue to work as expected
4. **External Dependencies**: No new dependencies should be added solely for refactoring purposes

### Assumptions

1. The two LLM router files (`llm/router.rs` and `llm_router.rs`) represent organic duplication rather than intentional separation
2. Dead code identified by compiler warnings is safe to remove unless explicitly marked as planned
3. Test organization changes will not affect CI/CD pipeline configuration
4. Vocabulary duplication between `ingestion/ttrpg/` and `core/archetype/` modules can be unified

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total backend LOC | ~51,500 | < 45,000 |
| `commands.rs` LOC | 10,679 | 0 (extracted) |
| Compiler warnings | ~20+ | 0 |
| Files > 1,500 LOC | ~12 | < 3 |
| LLM router combined LOC | ~4,694 | < 3,500 |

---

## Out of Scope

- Feature additions or behavior changes
- Performance optimizations beyond dead code elimination
- Database schema changes
- UI/UX changes
- Dependency upgrades (except where required for deprecation fixes)
