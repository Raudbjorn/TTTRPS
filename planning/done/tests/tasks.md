# Test Coverage Tasks: Actionable Checklist

## Legend
- [ ] Not started
- [x] Completed

---

## Phase 1: Test Infrastructure Setup

### 1.1 Add Testing Dependencies
- [ ] Add `proptest = "1.4"` to dev-dependencies in src-tauri/Cargo.toml
- [ ] Add `mockall = "0.12"` to dev-dependencies
- [ ] Add `wiremock = "0.6"` to dev-dependencies
- [ ] Add `fake = "2.9"` to dev-dependencies
- [ ] Add `rstest = "0.18"` to dev-dependencies
- [ ] Verify dependencies compile with `cargo check`

### 1.2 Create Test Fixtures Directory
- [ ] Create `src-tauri/src/tests/fixtures/` directory
- [ ] Create sample PDF fixture for ingestion tests
- [ ] Create sample EPUB fixture for ingestion tests
- [ ] Create sample DOCX fixture for ingestion tests
- [ ] Create sample JSON responses for LLM provider mocking
- [ ] Create attack vector samples for security testing

### 1.3 Set Up Mock Traits
- [ ] Create `src-tauri/src/tests/mocks/mod.rs` module
- [ ] Define MockLlmClient trait with automock
- [ ] Define MockVoiceProvider trait with automock
- [ ] Define MockSearchClient trait with automock
- [ ] Define MockDatabase trait for isolated testing

---

## Phase 2: Unit Tests - Critical Modules

### 2.1 LLM Router Tests (`llm_router_tests.rs`)
- [ ] Test provider selection with single available provider
- [ ] Test provider selection with multiple providers (cost-based)
- [ ] Test provider selection with multiple providers (capability-based)
- [ ] Test failover when primary provider fails
- [ ] Test failover chain exhaustion error handling
- [ ] Test cost calculation for Claude models
- [ ] Test cost calculation for OpenAI models
- [ ] Test cost calculation for Gemini models
- [ ] Test token counting accuracy for short prompts
- [ ] Test token counting accuracy for long prompts
- [ ] Test rate limit detection and backoff
- [ ] Test provider health check success
- [ ] Test provider health check failure
- [ ] Test streaming response assembly
- [ ] Test streaming error recovery
- [ ] Test model compatibility matrix lookups
- [ ] Test unknown model handling

### 2.2 Session Manager Tests (`session_manager_tests.rs`)
- [ ] Test session creation with valid campaign
- [ ] Test session creation with invalid campaign
- [ ] Test combat start with empty combatants
- [ ] Test combat start with multiple combatants
- [ ] Test initiative ordering (descending)
- [ ] Test initiative tie-breaking
- [ ] Test turn advancement (next combatant)
- [ ] Test turn advancement (wrap around)
- [ ] Test HP modification (damage)
- [ ] Test HP modification (healing)
- [ ] Test HP modification (temporary HP)
- [ ] Test HP bounds (no negative HP)
- [ ] Test HP bounds (no exceeding max)
- [ ] Test condition application (single)
- [ ] Test condition application (multiple)
- [ ] Test condition duration countdown
- [ ] Test condition removal (manual)
- [ ] Test condition removal (expiry)
- [ ] Test condition stacking rules
- [ ] Test combatant death (0 HP)
- [ ] Test combatant removal from combat
- [ ] Test combat end (all enemies defeated)
- [ ] Test combat end (manual)
- [ ] Test session notes creation
- [ ] Test session notes categorization
- [ ] Test session notes search
- [ ] Test timeline event ordering
- [ ] Test timeline event filtering by type
- [ ] Test session summary generation
- [ ] Test session snapshot creation
- [ ] Test session snapshot restoration

### 2.3 Voice Manager Tests (`voice_manager_tests.rs`)
- [ ] Test voice profile creation
- [ ] Test voice profile update
- [ ] Test voice profile deletion
- [ ] Test voice profile retrieval by ID
- [ ] Test voice profile list retrieval
- [ ] Test voice provider detection (ElevenLabs)
- [ ] Test voice provider detection (OpenAI)
- [ ] Test voice provider detection (Ollama)
- [ ] Test voice provider validation
- [ ] Test TTS queue addition
- [ ] Test TTS queue ordering (FIFO)
- [ ] Test TTS queue priority override
- [ ] Test TTS queue cancellation
- [ ] Test voice caching (cache miss)
- [ ] Test voice caching (cache hit)
- [ ] Test voice cache invalidation
- [ ] Test audio playback state management
- [ ] Test provider-specific error handling

### 2.4 Database Tests (`database_tests.rs` - Expand Existing)
- [ ] Test campaign CRUD - create
- [ ] Test campaign CRUD - read
- [ ] Test campaign CRUD - update
- [ ] Test campaign CRUD - delete
- [ ] Test campaign CRUD - list all
- [ ] Test session CRUD - create
- [ ] Test session CRUD - read
- [ ] Test session CRUD - update
- [ ] Test session CRUD - delete
- [ ] Test session CRUD - list by campaign
- [ ] Test NPC CRUD - create
- [ ] Test NPC CRUD - read
- [ ] Test NPC CRUD - update
- [ ] Test NPC CRUD - delete
- [ ] Test NPC CRUD - list by campaign
- [ ] Test conversation CRUD - create
- [ ] Test conversation CRUD - read history
- [ ] Test conversation CRUD - append message
- [ ] Test character CRUD - create
- [ ] Test character CRUD - read
- [ ] Test character CRUD - update
- [ ] Test character CRUD - delete
- [ ] Test transaction rollback on error
- [ ] Test concurrent read operations
- [ ] Test concurrent write operations
- [ ] Test backup creation
- [ ] Test backup file integrity
- [ ] Test restore from backup
- [ ] Test migration from older schema

### 2.5 Security Tests (`security_tests.rs`)
- [ ] Test XSS prevention - script tags
- [ ] Test XSS prevention - event handlers
- [ ] Test XSS prevention - javascript: URLs
- [ ] Test XSS prevention - data: URLs
- [ ] Test XSS prevention - encoded payloads
- [ ] Test SQL injection prevention - single quotes
- [ ] Test SQL injection prevention - UNION attacks
- [ ] Test SQL injection prevention - comment injection
- [ ] Test SQL injection prevention - stacked queries
- [ ] Test path traversal prevention - ../
- [ ] Test path traversal prevention - ..\\
- [ ] Test path traversal prevention - encoded sequences
- [ ] Test path traversal prevention - absolute paths
- [ ] Test command injection prevention - semicolons
- [ ] Test command injection prevention - pipes
- [ ] Test command injection prevention - backticks
- [ ] Test null byte injection prevention
- [ ] Test file extension validation
- [ ] Test file size limits
- [ ] Test input length limits
- [ ] Test credential storage (mock keyring)
- [ ] Test API key validation format
- [ ] Test audit log completeness

---

## Phase 3: Unit Tests - LLM Providers

### 3.1 Claude Provider Tests (`claude_tests.rs`)
- [ ] Test API request formatting
- [ ] Test response parsing (success)
- [ ] Test response parsing (error)
- [ ] Test model switching (Opus, Sonnet, Haiku)
- [ ] Test streaming response handling
- [ ] Test rate limit error handling
- [ ] Test timeout handling
- [ ] Test invalid API key handling

### 3.2 OpenAI Provider Tests (`openai_tests.rs`)
- [ ] Test API request formatting
- [ ] Test response parsing (success)
- [ ] Test response parsing (error)
- [ ] Test model switching (GPT-4, GPT-3.5)
- [ ] Test vision support request formatting
- [ ] Test function calling formatting
- [ ] Test streaming response handling
- [ ] Test rate limit error handling
- [ ] Test timeout handling

### 3.3 Gemini Provider Tests (`gemini_tests.rs`)
- [ ] Test API request formatting
- [ ] Test response parsing (success)
- [ ] Test response parsing (error)
- [ ] Test model switching (Pro, Flash)
- [ ] Test streaming response handling
- [ ] Test safety settings handling
- [ ] Test rate limit error handling
- [ ] Test timeout handling

### 3.4 Ollama Provider Tests (`ollama_tests.rs`)
- [ ] Test API request formatting
- [ ] Test response parsing (success)
- [ ] Test response parsing (error)
- [ ] Test model availability check
- [ ] Test connection refused handling
- [ ] Test streaming response handling
- [ ] Test timeout handling

### 3.5 Other Provider Tests (Groq, Mistral, Cohere, etc.)
- [ ] Test Groq provider basic operations
- [ ] Test Mistral provider basic operations
- [ ] Test Cohere provider basic operations
- [ ] Test Deepseek provider basic operations
- [ ] Test OpenRouter provider basic operations
- [ ] Test Together provider basic operations
- [ ] Test Gemini CLI provider basic operations
- [ ] Test Claude Code provider basic operations
- [ ] Test Claude Desktop (CDP) provider basic operations

---

## Phase 4: Unit Tests - Character Generation

### 4.1 D&D 5e Tests (`dnd5e_tests.rs`)
- [ ] Test character creation with valid inputs
- [ ] Test attribute generation (standard array)
- [ ] Test attribute generation (point buy)
- [ ] Test attribute generation (rolled)
- [ ] Test class feature assignment
- [ ] Test subclass feature assignment
- [ ] Test spell list generation
- [ ] Test multiclass validation
- [ ] Test race/species ability bonuses
- [ ] Test background feature application
- [ ] Test proficiency calculation
- [ ] Test equipment starting packages

### 4.2 Pathfinder 2e Tests (`pf2e_tests.rs`)
- [ ] Test character creation with valid inputs
- [ ] Test ancestry selection and bonuses
- [ ] Test background selection
- [ ] Test class selection and features
- [ ] Test action economy (3 actions)
- [ ] Test dedication feat validation
- [ ] Test spell tradition assignment
- [ ] Test proficiency rank progression

### 4.3 Call of Cthulhu Tests (`coc_tests.rs`)
- [ ] Test character creation with valid inputs
- [ ] Test occupation selection
- [ ] Test skill point allocation
- [ ] Test sanity calculation
- [ ] Test luck calculation
- [ ] Test backstory generation
- [ ] Test era-appropriate equipment

### 4.4 Other System Tests
- [ ] Test Cyberpunk character generation
- [ ] Test FATE character generation (aspects, stunts)
- [ ] Test GURPS character generation
- [ ] Test Dungeon World character generation
- [ ] Test Shadowrun character generation
- [ ] Test Warhammer character generation

---

## Phase 5: Unit Tests - Ingestion Pipeline

### 5.1 PDF Parser Tests (`pdf_parser_tests.rs`)
- [ ] Test text extraction from simple PDF
- [ ] Test text extraction from multi-column PDF
- [ ] Test metadata extraction (title, author)
- [ ] Test page number extraction
- [ ] Test image handling (skip/placeholder)
- [ ] Test malformed PDF handling
- [ ] Test encrypted PDF handling (error)
- [ ] Test large PDF handling (memory bounds)

### 5.2 EPUB Parser Tests (`epub_parser_tests.rs`)
- [ ] Test chapter extraction
- [ ] Test TOC parsing
- [ ] Test metadata extraction
- [ ] Test CSS stripping
- [ ] Test embedded image handling
- [ ] Test malformed EPUB handling
- [ ] Test DRM-protected EPUB handling (error)

### 5.3 DOCX Parser Tests (`docx_parser_tests.rs`)
- [ ] Test text extraction
- [ ] Test table extraction
- [ ] Test heading extraction
- [ ] Test metadata extraction
- [ ] Test embedded image handling
- [ ] Test malformed DOCX handling

### 5.4 Chunker Tests (`chunker_tests.rs`)
- [ ] Test chunking with default parameters
- [ ] Test chunking with custom chunk size
- [ ] Test chunking with overlap
- [ ] Test semantic boundary detection
- [ ] Test paragraph preservation
- [ ] Test heading inclusion in chunks
- [ ] Test data integrity (reconstruct from chunks)
- [ ] Test empty document handling
- [ ] Test very large document handling

---

## Phase 6: Property-Based Tests

### 6.1 Name Generator Properties (`name_generator_props.rs`)
- [ ] Property: output is valid UTF-8
- [ ] Property: output length is reasonable (1-100 chars)
- [ ] Property: deterministic given same seed
- [ ] Property: no offensive content (basic filter)

### 6.2 Cost Calculator Properties (`cost_calculator_props.rs`)
- [ ] Property: cost is non-negative
- [ ] Property: cost increases monotonically with tokens
- [ ] Property: cost is bounded for bounded input
- [ ] Property: zero tokens yields zero cost

### 6.3 Input Validator Properties (`input_validator_props.rs`)
- [ ] Property: never accepts script tags
- [ ] Property: never accepts SQL keywords in dangerous positions
- [ ] Property: never accepts path traversal sequences
- [ ] Property: accepts all alphanumeric input
- [ ] Property: consistent results for same input

### 6.4 Search Ranking Properties (`search_ranking_props.rs`)
- [ ] Property: same query returns same order
- [ ] Property: more relevant results score higher
- [ ] Property: empty query returns no results
- [ ] Property: ranking is transitive

### 6.5 Token Counter Properties (`token_counter_props.rs`)
- [ ] Property: count is non-negative
- [ ] Property: empty string yields zero tokens
- [ ] Property: count increases with string length
- [ ] Property: count is within 20% of actual (spot check)

---

## Phase 7: Integration Tests

### 7.1 Database Integration (`database_integration.rs`)
- [ ] Test full campaign lifecycle
- [ ] Test session with combat flow
- [ ] Test NPC conversation persistence
- [ ] Test concurrent campaign access
- [ ] Test backup and restore cycle
- [ ] Test database recovery from corruption

### 7.2 Meilisearch Integration (`meilisearch_integration.rs` - Expand)
- [ ] Test document indexing end-to-end
- [ ] Test search with various query types
- [ ] Test hybrid search (BM25 + vector)
- [ ] Test faceted search
- [ ] Test search analytics recording
- [ ] Test index deletion and cleanup
- [ ] Test connection failure recovery
- [ ] Test large batch indexing

### 7.3 LLM Integration (`llm_integration.rs`)
- [ ] Test provider failover (mock failures)
- [ ] Test streaming assembly
- [ ] Test context window management
- [ ] Test cost tracking accumulation
- [ ] Test rate limit backoff
- [ ] Test timeout recovery

### 7.4 Voice Integration (`voice_integration.rs`)
- [ ] Test TTS pipeline end-to-end (mock audio)
- [ ] Test voice caching round-trip
- [ ] Test queue processing order
- [ ] Test provider switching

---

## Phase 8: Frontend Tests

### 8.1 Campaign Components (`campaign_tests.rs`)
- [ ] Test CampaignDashboard rendering
- [ ] Test CampaignCard display
- [ ] Test CampaignCreateModal form validation
- [ ] Test campaign selection state
- [ ] Test campaign deletion confirmation

### 8.2 Session Components (`session_tests.rs`)
- [ ] Test ActiveSession rendering
- [ ] Test CombatTracker display
- [ ] Test InitiativeList ordering
- [ ] Test CombatantCard HP display
- [ ] Test condition badge rendering
- [ ] Test session notes input

### 8.3 Settings Components (`settings_tests.rs`)
- [ ] Test LLM settings form
- [ ] Test voice settings form
- [ ] Test theme editor
- [ ] Test API key input masking
- [ ] Test settings persistence

### 8.4 Service Tests
- [ ] Expand ThemeService tests (color blending edge cases)
- [ ] Test LayoutService responsive states
- [ ] Test NotificationService toast lifecycle

---

## Phase 9: Edge Cases & Error Handling

### 9.1 Network Errors
- [ ] Test timeout during LLM call
- [ ] Test connection refused
- [ ] Test DNS resolution failure
- [ ] Test SSL certificate error
- [ ] Test mid-stream disconnect

### 9.2 Data Errors
- [ ] Test malformed JSON response
- [ ] Test missing required fields
- [ ] Test invalid UTF-8 in response
- [ ] Test extremely large response
- [ ] Test empty response

### 9.3 Resource Errors
- [ ] Test database file locked
- [ ] Test disk space exhaustion (mock)
- [ ] Test memory limits (large documents)
- [ ] Test file permission denied

### 9.4 Concurrent Access
- [ ] Test simultaneous session updates
- [ ] Test simultaneous NPC edits
- [ ] Test race condition in combat tracker

---

## Phase 10: Coverage Verification

### 10.1 Run Coverage Analysis
- [ ] Install cargo-llvm-cov or cargo-tarpaulin
- [ ] Run coverage report on backend
- [ ] Identify untested code paths
- [ ] Add tests for missed branches

### 10.2 Documentation
- [ ] Document test conventions in README
- [ ] Add example test patterns
- [ ] Document mock setup procedures
- [ ] Document CI test configuration

---

## Summary Statistics

| Phase | Total Tasks | Priority |
|-------|-------------|----------|
| 1. Infrastructure | 17 | Critical |
| 2. Critical Unit Tests | 105 | Critical |
| 3. LLM Provider Tests | 44 | High |
| 4. Character Gen Tests | 32 | High |
| 5. Ingestion Tests | 28 | High |
| 6. Property Tests | 20 | Medium |
| 7. Integration Tests | 26 | Medium |
| 8. Frontend Tests | 19 | Medium |
| 9. Edge Cases | 19 | Low |
| 10. Coverage | 5 | Critical |
| **TOTAL** | **315** | - |

---

*Generated: 2026-01-04*
