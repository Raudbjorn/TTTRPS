# Test Coverage Strategy: 100% Coverage for Sidecar DM

## Executive Summary

This document outlines the comprehensive testing strategy to achieve 100% test coverage for the Sidecar DM AI-powered TTRPG assistant. The project consists of ~35,700 lines of Rust code across a Tauri desktop backend and Leptos WebAssembly frontend.

## Current State

- **Existing Test Functions:** 336
- **Async Tests (Tokio):** 194
- **Files with Tests:** 76/228
- **Estimated Current Coverage:** ~50-60%
- **Target Coverage:** 100%

## Testing Pyramid

```
        /\
       /  \  E2E/Acceptance Tests (5%)
      /----\  Integration Tests (15%)
     /------\  Property-Based Tests (10%)
    /--------\  Unit Tests (70%)
   /----------\
```

---

## 1. Unit Testing Strategy

### 1.1 Backend Core Modules (Priority: CRITICAL)

#### LLM System (2,127 lines)
- **Router Logic:** Provider selection, fallover chains, cost-based routing
- **Token Counting:** Accurate token estimation per provider
- **Health Checks:** Provider availability detection
- **Cost Tracking:** Usage cost calculation accuracy
- **Test Approach:** Mock HTTP clients, test decision matrices

#### Session Manager (1,966 lines)
- **Combat Tracker:** Initiative ordering, turn management, HP tracking
- **Condition System:** Condition application, duration, stacking rules
- **Timeline Events:** Event ordering, filtering, aggregation
- **Notes System:** Categorization, search, persistence
- **Test Approach:** State machine testing, boundary value analysis

#### Voice System (11 providers)
- **Profile Management:** CRUD operations, validation
- **Queue System:** Ordering, priority, cancellation
- **Caching:** Cache hits/misses, invalidation
- **Test Approach:** Mock audio APIs, test state transitions

#### Database Layer (4 files, ~2,000 lines)
- **Models:** All CRUD operations per entity type
- **Migrations:** Schema version transitions
- **Backup/Restore:** Data integrity verification
- **Test Approach:** In-memory SQLite, transaction isolation

#### Security & Validation
- **Input Validator:** All attack vector prevention (XSS, SQLi, path traversal)
- **Credential Manager:** Secure storage, retrieval
- **Audit Logger:** Event capture completeness
- **Test Approach:** Fuzzing, known attack patterns

### 1.2 LLM Provider Coverage (13 providers)

Each provider requires:
- API request formatting tests
- Response parsing tests
- Error handling tests (timeouts, rate limits, invalid responses)
- Model capability mapping tests

| Provider | Priority | Complexity |
|----------|----------|------------|
| Claude | Critical | High |
| OpenAI | Critical | High |
| Gemini | Critical | Medium |
| Ollama | High | Medium |
| Groq | Medium | Low |
| Mistral | Medium | Low |
| Others (7) | Low | Low |

### 1.3 Character Generation (9 game systems)

Each system requires:
- Valid character generation
- Attribute bounds checking
- System-specific rule compliance
- Backstory generation quality

| System | Priority | Test Focus |
|--------|----------|------------|
| D&D 5e | Critical | Class features, spells, multiclass |
| PF2e | High | Actions, ancestries, dedications |
| Call of Cthulhu | High | Sanity, skills, occupations |
| Cyberpunk | Medium | Chrome, roles, lifepath |
| FATE | Medium | Aspects, stress, stunts |
| Others (4) | Low | System-specific validation |

### 1.4 Ingestion Pipeline (11 files)

- **PDF Parser:** Text extraction, metadata, multi-column handling
- **EPUB Parser:** Chapter extraction, TOC parsing
- **MOBI Parser:** Format conversion, content extraction
- **DOCX Parser:** Text, tables, formatting preservation
- **Chunker:** Overlap logic, semantic boundaries
- **Test Approach:** Sample documents of varying complexity

### 1.5 Frontend Services

- **Theme Service:** Color blending, CSS generation, preset validation
- **Layout Service:** Responsive breakpoints, panel states
- **Notification Service:** Toast lifecycle, dismissal
- **Test Approach:** WASM test harness, component isolation

---

## 2. Property-Based Testing Strategy

Using `proptest` and `quickcheck` crates for:

### 2.1 Invariant Properties

```rust
// Example: Character generation always produces valid characters
proptest! {
    #[test]
    fn character_always_valid(system in any::<GameSystem>(), seed in any::<u64>()) {
        let character = generate_character(system, seed);
        prop_assert!(character.is_valid());
    }
}
```

### 2.2 Target Areas

| Module | Property | Generator |
|--------|----------|-----------|
| Name Generator | Valid UTF-8, reasonable length | Random seeds |
| Cost Calculator | Non-negative, monotonic with tokens | Token counts 0..1M |
| Input Validator | Never accepts attack patterns | Arbitrary strings |
| Search Ranking | Consistent ordering | Same query repeated |
| Token Counter | Within 10% of actual | Sample texts |
| Chunker | No data loss after chunk + reconstruct | Arbitrary documents |

### 2.3 Fuzzing Targets

- Input validation functions
- Document parsers (PDF, EPUB, MOBI, DOCX)
- JSON/API response parsers
- Search query parser

---

## 3. Integration Testing Strategy

### 3.1 Database Integration

- **Campaign Lifecycle:** Create -> Update -> Snapshot -> Rollback -> Delete
- **Session Management:** Start -> Combat -> End -> Summary
- **NPC Conversations:** Create -> Multiple turns -> History retrieval
- **Concurrent Access:** Multiple reads/writes without corruption

### 3.2 Search Integration (Meilisearch)

- **Indexing Pipeline:** Document -> Chunk -> Embed -> Index -> Search
- **Hybrid Search:** BM25 + Vector fusion accuracy
- **Query Expansion:** Synonym handling, spell correction
- **Analytics:** Search tracking, popular queries

### 3.3 LLM Integration

- **Provider Switching:** Seamless failover between providers
- **Streaming:** Chunk assembly, error recovery mid-stream
- **Context Management:** Token limits, truncation strategies
- **Cost Tracking:** Accurate accumulation across calls

### 3.4 Voice Integration

- **TTS Pipeline:** Text -> Voice -> Audio -> Playback
- **Caching:** Cache creation, retrieval, invalidation
- **Queue Management:** Priority handling, cancellation

---

## 4. Acceptance/E2E Testing Strategy

### 4.1 Critical User Journeys

1. **New Campaign Flow**
   - Create campaign -> Set system -> Add initial NPCs -> Start session

2. **Document Library Flow**
   - Upload rulebook -> Wait for indexing -> Search -> Use in chat

3. **Combat Session Flow**
   - Start combat -> Add combatants -> Run initiative -> Process turns -> End combat

4. **NPC Conversation Flow**
   - Select NPC -> Apply personality -> Conduct conversation -> Save to history

5. **Settings Configuration Flow**
   - Configure LLM provider -> Test connection -> Save -> Use in generation

### 4.2 Error Recovery Scenarios

- Network failure during LLM call
- Meilisearch unavailable
- Invalid API key handling
- Database corruption recovery
- Disk space exhaustion

---

## 5. Test Infrastructure Requirements

### 5.1 Mocking Strategy

```rust
// Trait-based mocking for external services
#[cfg_attr(test, mockall::automock)]
pub trait LlmClient {
    async fn complete(&self, prompt: &str) -> Result<String>;
}
```

### 5.2 Test Fixtures

```
tests/fixtures/
├── documents/
│   ├── sample.pdf
│   ├── sample.epub
│   ├── sample.mobi
│   └── sample.docx
├── responses/
│   ├── claude_response.json
│   ├── openai_response.json
│   └── gemini_response.json
└── data/
    ├── test_campaign.json
    ├── test_characters.json
    └── attack_vectors.txt
```

### 5.3 Test Database Setup

```rust
async fn test_db() -> Database {
    Database::new(":memory:").await.unwrap()
}
```

### 5.4 Required Dependencies

```toml
[dev-dependencies]
proptest = "1.4"
quickcheck = "1.0"
mockall = "0.12"
wiremock = "0.6"
tempfile = "3.10"
fake = "2.9"
rstest = "0.18"
criterion = "0.5"  # For benchmarks
```

---

## 6. Coverage Metrics & Goals

### 6.1 Coverage Tools

- **Backend:** `cargo-llvm-cov` or `cargo-tarpaulin`
- **Frontend:** `wasm-bindgen-test` with coverage instrumentation

### 6.2 Coverage Targets

| Category | Line | Branch | Function |
|----------|------|--------|----------|
| Critical Modules | 100% | 95% | 100% |
| High Priority | 95% | 90% | 100% |
| Medium Priority | 90% | 85% | 95% |
| Low Priority | 85% | 80% | 90% |
| **Overall Target** | **95%+** | **90%+** | **100%** |

### 6.3 Exclusions

- Dead code paths (marked with `#[cfg(test)]` or `#[allow(dead_code)]`)
- Panic-only error handlers
- Generated code (Tauri commands boilerplate)

---

## 7. Test Organization

### 7.1 Backend Test Structure

```
src-tauri/src/tests/
├── mod.rs
├── unit/
│   ├── llm_router_tests.rs
│   ├── session_manager_tests.rs
│   ├── voice_manager_tests.rs
│   ├── database_tests.rs
│   ├── security_tests.rs
│   ├── character_gen/
│   │   ├── dnd5e_tests.rs
│   │   ├── pf2e_tests.rs
│   │   └── ...
│   └── providers/
│       ├── claude_tests.rs
│       ├── openai_tests.rs
│       └── ...
├── property/
│   ├── name_generator_props.rs
│   ├── cost_calculator_props.rs
│   ├── input_validator_props.rs
│   └── search_ranking_props.rs
├── integration/
│   ├── database_integration.rs
│   ├── meilisearch_integration.rs
│   ├── llm_integration.rs
│   └── voice_integration.rs
└── fixtures/
    └── ...
```

### 7.2 Frontend Test Structure

```
frontend/tests/
├── components/
│   ├── campaign_tests.rs
│   ├── session_tests.rs
│   ├── combat_tests.rs
│   └── settings_tests.rs
├── services/
│   ├── theme_service_tests.rs
│   ├── layout_service_tests.rs
│   └── notification_tests.rs
└── integration/
    └── tauri_bridge_tests.rs
```

---

## 8. CI/CD Integration

### 8.1 Test Stages

1. **Fast Tests:** Unit tests (<30s)
2. **Integration Tests:** Database + mock services (<5m)
3. **Full Tests:** Including Meilisearch integration (<15m)
4. **Coverage Report:** Generate and upload to codecov

### 8.2 Pre-commit Hooks

```bash
#!/bin/bash
cargo test --lib  # Unit tests only
cargo clippy -- -D warnings
```

---

## 9. Success Criteria

- [ ] All 228 source files have corresponding test coverage
- [ ] Overall line coverage >= 95%
- [ ] Overall branch coverage >= 90%
- [ ] All critical paths have 100% coverage
- [ ] Property tests cover all generators and validators
- [ ] Integration tests cover all external service interactions
- [ ] E2E tests cover top 5 user journeys
- [ ] CI pipeline runs all tests on every PR
- [ ] Coverage reports published automatically

---

## 10. Timeline-Free Prioritization

### Phase 1: Foundation
- Add dev dependencies (proptest, mockall, etc.)
- Set up test fixtures directory
- Create mock traits for external services
- Expand existing database tests

### Phase 2: Critical Coverage
- LLM router unit tests
- Session manager unit tests
- Security/validation tests
- Database CRUD tests

### Phase 3: Provider & System Coverage
- All 13 LLM provider tests
- All 9 character generation system tests
- Voice provider tests
- Ingestion pipeline tests

### Phase 4: Property & Integration
- Property-based tests for generators
- Meilisearch integration tests
- LLM failover integration tests
- Frontend component tests

### Phase 5: Polish
- E2E acceptance tests
- Edge case coverage
- Performance benchmarks
- Documentation

---

*Document Version: 1.0*
*Generated: 2026-01-04*
