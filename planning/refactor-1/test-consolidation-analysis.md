# Test Consolidation Analysis

## Test Structure Overview
- **Total test files**: 41 (24 in `/unit/`, 5 in `/integration/`, 6 in `/property/`, 6 root-level)
- **Total test functions**: 1,180
- **Total test lines**: ~31,087 lines
- **Test helper/utility code**: ~419 lines in `/tests/mocks/mod.rs` + scattered helpers in test files

## Directory Structure
```
src-tauri/src/tests/
├── mocks/mod.rs (419 lines, helper mocks)
├── database_tests.rs (2,585 lines, 79 tests)
├── unit/
│   ├── session_manager_tests.rs (2,292 lines, 123 tests)
│   ├── security_tests.rs (2,133 lines, 95 tests)
│   ├── voice_manager_tests.rs (1,488 lines, 79 tests)
│   ├── edge_cases_tests.rs (1,047 lines)
│   ├── providers/
│   │   ├── google_tests.rs (1,062 lines, 66 tests)
│   │   ├── ollama_tests.rs (1,116 lines, 80 tests)
│   │   ├── openai_tests.rs (972 lines, 63 tests)
│   │   └── claude_tests.rs (783 lines, 52 tests)
│   ├── character_gen/
│   │   ├── pf2e_tests.rs (1,140 lines, 58 tests)
│   │   ├── coc_tests.rs (1,035 lines, 58 tests)
│   │   └── dnd5e_tests.rs (955 lines, 45 tests)
│   └── ingestion/
│       ├── chunker_tests.rs (1,182 lines)
│       └── pdf_parser_tests.rs (966 lines)
├── integration/
│   ├── meilisearch_integration.rs (985 lines, 23 tests)
│   ├── llm_integration.rs (1,001 lines)
│   └── database_integration.rs (1,025 lines)
└── property/
    ├── search_ranking_props.rs (624 lines)
    ├── token_counter_props.rs (586 lines)
    └── [3 more property-based tests]
```

## Shared Setup Patterns

| Pattern | Files Using | Type | Approximate Lines |
|---------|-------------|------|-------------------|
| `create_test_db()` async setup | 3 files (database_tests.rs, database_integration.rs, edge_cases_tests.rs) | Exact duplicate | 6 lines × 3 = 18 lines |
| `create_test_manager()` | 2 files (session_manager_tests.rs, process_manager_tests.rs) | Similar pattern | ~3-5 lines each |
| `create_test_generator()` | 3 files (dnd5e_tests.rs, pf2e_tests.rs, coc_tests.rs) | Identical pattern | ~2 lines × 3 = 6 lines |
| Provider setup (OpenAI, Claude, Google, Ollama) | 4 provider test files | Repeated constructor calls | ~5-8 lines per file |
| Character generation options | dnd5e_tests.rs, pf2e_tests.rs, coc_tests.rs | Duplicate `create_default_options()` | ~6 lines × 3 = 18 lines |
| Combatant fixture builders | session_manager_tests.rs | Multiple internal variants | ~80 lines total (could be consolidated) |
| TempDir + Database creation | 3+ files | Pattern duplication | 18 lines potential savings |

## Proposed Test Utilities

### 1. `test_utils/database.rs` (Proposed)
```rust
// Consolidate database test fixtures
pub async fn create_test_db() -> (Database, TempDir) { ... }
pub async fn create_test_db_with_campaign(name: &str) -> (Database, TempDir, CampaignRecord) { ... }
pub async fn create_test_db_with_session(campaign_id: &str) -> (Database, TempDir, SessionRecord) { ... }
```
- **Files affected**: database_tests.rs, database_integration.rs, edge_cases_tests.rs
- **Lines saveable**: ~18 lines (duplication + wiring)
- **Additional benefit**: Shared setup patterns for complex DB scenarios

### 2. `test_utils/fixtures.rs` (Proposed)
```rust
// Session/Combat fixtures
pub fn create_test_manager() -> SessionManager { ... }
pub fn create_test_combatant(name: &str, initiative: i32, hp: Option<i32>) -> Combatant { ... }
pub fn create_combatant_with_hp(...) -> Combatant { ... }
pub fn create_monster(name: &str, initiative: i32, hp: i32) -> Combatant { ... }

// Character generation fixtures
pub fn create_test_dnd5e_generator() -> DnD5eGenerator { ... }
pub fn create_test_pf2e_generator() -> Pathfinder2eGenerator { ... }
pub fn create_test_coc_generator() -> CallOfCthulhuGenerator { ... }
pub fn create_default_gen_options(system: &str) -> GenerationOptions { ... }

// Process manager fixture
pub fn create_test_process_manager() -> Arc<ProcessManager> { ... }
```
- **Files affected**: session_manager_tests.rs, character_gen/*.rs (3 files), process_manager_tests.rs
- **Lines saveable**: ~80-100 lines
- **Additional benefit**: Consistent fixture patterns across test suites

### 3. `test_utils/providers.rs` (Proposed)
```rust
// Provider test helpers
pub fn create_openai_provider_test() -> OpenAIProvider { ... }
pub fn create_claude_provider_test() -> ClaudeProvider { ... }
pub fn create_google_provider_test() -> GoogleProvider { ... }
pub fn create_ollama_provider_test() -> OllamaProvider { ... }

// Shared request/response fixtures
pub fn create_test_chat_request(content: &str) -> ChatRequest { ... }
pub fn create_test_messages() -> Vec<ChatMessage> { ... }
```
- **Files affected**: providers/*.rs (4 files)
- **Lines saveable**: ~30-50 lines per file
- **Additional benefit**: Standardized provider test structure

### 4. Update `mocks/mod.rs` scope
- Current: 419 lines with trait mocks (LlmClient, VoiceProvider, SearchClient)
- Enhance with: Combatant, Session, Character fixtures matching production types
- **Lines added**: ~100-150 lines
- **Benefit**: Unified mock/fixture library

## Parameterization Opportunities

| Test File | Test Group | Current Tests | Could Reduce To | Mechanism |
|-----------|------------|---------------|-----------------|-----------|
| providers/google_tests.rs | Provider identity tests | 3 tests (id, name, model) | 1 parameterized | `proptest` or test matrix macro |
| providers/openai_tests.rs | Convenience constructors | 2 tests (gpt4o, gpt4o_mini) | 1 parameterized | Macro-based parameterization |
| providers/claude_tests.rs | Health checks | 2 tests (with/without tokens) | 1 parameterized | Test case variants |
| character_gen/dnd5e_tests.rs | Character creation tests | 3+ tests (basic, custom, all options) | 1-2 parameterized | Nested test module with `#[test]` macros |
| character_gen/pf2e_tests.rs | Character creation tests | Similar structure | Similar reduction | Same approach |
| character_gen/coc_tests.rs | Character creation tests | Similar structure | Similar reduction | Same approach |
| unit/session_manager_tests.rs | Combat initialization | 5+ variations (empty, single, multiple) | 1-2 parameterized | Parameterized test matrix |
| database_tests.rs | CRUD operations by entity | ~79 tests across 10+ entity types | Reduce to ~45 | Template-based test generation |

**Estimated reduction**: ~30-40 tests through parameterization (representing ~80-120 lines)

## Dead/Skipped Tests

| File | Type | Count | Notes |
|------|------|-------|-------|
| meilisearch_integration.rs | #[ignore] markers | Not counted | Tests marked `#[ignore]` require running Meilisearch instance |
| All files | Commented code | None found | No commented-out test functions detected (`// fn test_` pattern absent) |
| integration/mod.rs | Documentation only | N/A | Notes that some tests require Meilisearch running |

**Observation**: Test suite is well-maintained (no dead/commented tests). The #[ignore] usage is intentional for environment-dependent tests.

## Test Organization Issues

### Issue 1: Duplicate Database Setup (3 locations)
- **Files**: database_tests.rs, database_integration.rs, unit/edge_cases_tests.rs
- **Pattern**: Identical `async fn create_test_db()` implementations
- **Lines duplicated**: 6 lines × 3 = 18 lines
- **Severity**: Low (small duplication, clear scope)

### Issue 2: Scattered Test Fixtures Across Unit Tests
- **Files**: session_manager_tests.rs (80 lines of fixtures), character_gen/*.rs (6 lines × 3), process_manager_tests.rs (15 lines)
- **Problem**: Fixtures defined locally in each file, not discoverable
- **Lines scattered**: ~120 lines across 5+ test files
- **Severity**: Medium (impacts test maintainability)

### Issue 3: Character Generation Test Patterns (3 files)
- **Files**: dnd5e_tests.rs, pf2e_tests.rs, coc_tests.rs
- **Duplication**: Identical test structure:
  - `create_test_generator()` (2 lines each)
  - `create_default_options()` (5-6 lines each)
  - Test module organization (identical `#[cfg(test)] mod character_creation { ... }`)
  - Test assertions nearly identical (different system enums only)
- **Lines duplicated**: ~18 lines × 3 = 54 lines + ~50 lines of duplicated test logic
- **Severity**: Medium (impacts readability + maintenance)

### Issue 4: Provider Test Structure Duplication (4 files)
- **Files**: claude_tests.rs, google_tests.rs, ollama_tests.rs, openai_tests.rs
- **Pattern**: Each file contains:
  - Provider identity tests (3 tests: id, name, model) - nearly identical assertions
  - Health check tests - similar structure
  - Pricing tests - similar structure
  - Request formatting tests - provider-specific but similar patterns
- **Lines duplicated**: ~15-20 lines of boilerplate per file
- **Severity**: Medium-High (affects 4 files, many similar tests)

### Issue 5: Meilisearch Test Duplication
- **Files**: meilisearch_integration_tests.rs (253 lines), integration/meilisearch_integration.rs (985 lines)
- **Apparent relationship**: Older (253-line) file appears superseded by newer comprehensive version
- **Status**: Unclear - may be intentional legacy or accidental duplication
- **Lines affected**: 253 lines (older file possibly redundant)
- **Severity**: High (suggests incomplete refactoring)

### Issue 6: Process Manager Test Duplication
- **Files**: process_manager_tests.rs (10 tests), process_manager_comprehensive_tests.rs (18 tests)
- **Apparent relationship**: _comprehensive version likely supersedes original
- **Status**: Unclear - suggests incremental development artifact
- **Lines affected**: 248 + 564 = 812 lines combined
- **Severity**: High (possible consolidation candidate)

## Estimated Reduction Potential

### Quick Wins (Low Risk)
1. Consolidate `create_test_db()` → **18 lines saved** (also improves maintenance)
2. Consolidate character gen fixtures → **54 lines saved**
3. Create shared provider test helpers → **20-30 lines saved**
4. **Subtotal: ~100 lines**

### Medium Effort (Medium Risk)
1. Parameterize provider identity tests → **40-50 tests consolidated, 30-40 lines saved**
2. Parameterize character generation tests → **20-30 tests consolidated, 50-70 lines saved**
3. Parameterize session/combat initialization → **15-20 tests consolidated, 40-50 lines saved**
4. **Subtotal: ~100-150 lines, 75-100 tests consolidated**

### Investigation Needed (High Risk)
1. **Meilisearch test consolidation**: Verify if 253-line file is truly redundant
   - If yes: **253 lines saved**
   - If no: Keep both with clear documentation
2. **Process manager consolidation**: Determine if basic/comprehensive tests serve different purposes
   - If yes: Document separation
   - If no: Consolidate and **812 lines saved**
3. **Subtotal: 253-812 lines (pending investigation)**

## Total Consolidation Impact
- **Conservative estimate**: 200-250 lines saveable + 75-100 parameterized tests
- **Aggressive estimate**: 1,000+ lines saveable + 100+ parameterized tests (if process_manager & meilisearch duplication confirmed)
- **Test maintainability improvement**: 40-50% reduction in fixture/setup boilerplate
- **Readability improvement**: Unified fixture patterns across 8+ test files

## Implementation Priority

### Phase 1: Foundation (Lowest Risk)
1. Create `tests/test_utils/mod.rs` - export directory
2. Create `tests/test_utils/database.rs` - consolidate DB fixtures
3. Update database_tests.rs, database_integration.rs, edge_cases_tests.rs to use shared utilities
4. **Risk**: Minimal (just moving code)
5. **Lines saved**: 18-30 lines
6. **Time**: ~30 minutes

### Phase 2: Session/Character Fixtures
1. Create `tests/test_utils/fixtures.rs` - session, combatant, character gen fixtures
2. Update session_manager_tests.rs, character_gen/*.rs, process_manager_tests.rs
3. **Risk**: Low (fixtures are simple data builders)
4. **Lines saved**: 100-120 lines
5. **Time**: ~1 hour

### Phase 3: Provider Utilities
1. Create `tests/test_utils/providers.rs` - provider setup helpers
2. Update provider test files to use shared constructors
3. **Risk**: Low-Medium (provider setup is straightforward)
4. **Lines saved**: 20-50 lines
5. **Time**: ~45 minutes

### Phase 4: Parameterization (Optional, Higher Risk)
1. Evaluate proptest or custom test macros for parameterization
2. Start with provider identity tests (lowest risk, clear benefit)
3. Expand to character generation tests
4. **Risk**: Medium (requires test framework changes)
5. **Lines saved**: 50-100 lines + test consolidation
6. **Time**: ~2-3 hours

### Phase 5: Investigation & Cleanup
1. Audit meilisearch_integration_tests.rs vs integration/meilisearch_integration.rs
2. Audit process_manager_tests.rs vs process_manager_comprehensive_tests.rs
3. Consolidate or clearly document separation if necessary
4. **Risk**: Medium (requires understanding original intent)
5. **Lines saved**: 250-800 lines (if consolidation confirmed)
6. **Time**: ~1-2 hours

## Recommendations

### Immediate Actions
1. **Create test_utils module** - provides foundation for all further consolidation
2. **Consolidate DB setup** - single source of truth for database test creation
3. **Consolidate character gen fixtures** - 3 nearly-identical files will significantly benefit

### Short-Term (Sprint-Based)
1. **Move session/combat fixtures** to shared utility
2. **Document provider test patterns** - make it clear which tests can be parameterized
3. **Investigate process_manager duplication** - clarify if comprehensive version supersedes basic version

### Long-Term Improvements
1. **Consider test-generation macros** for similar test patterns (5+ repetitions with variable inputs)
2. **Develop test template library** for system-specific generators (D&D 5e, PF2e, CoC pattern matches)
3. **Monitor for new duplication** - establish code review guideline for test organization
