# Feature Parity Tasks: Original Python → Rust/Tauri

This document contains detailed, actionable tasks to bring the Rust/Tauri implementation into feature parity with the original Python/MCP project.

**Legend:**
- 🔴 **Critical** - Core functionality, blocks other features
- 🟠 **High** - Important for production use
- 🟡 **Medium** - Enhances user experience
- 🟢 **Low** - Nice to have, can defer

---

# BACKEND TASKS

## 1. AI Providers Module

### 1.1 OpenAI Provider 🔴
**File:** `src-tauri/src/core/llm/openai.rs`

- [ ] Create `OpenAIClient` struct with configuration
- [ ] Implement `chat_completion()` for GPT-4o, GPT-4o-mini, GPT-3.5-turbo
- [ ] Implement `stream_completion()` with Server-Sent Events (SSE) parsing
- [ ] Add `generate_embeddings()` using text-embedding-3-small/large
- [ ] Implement rate limit header extraction (x-ratelimit-remaining, x-ratelimit-reset)
- [ ] Add vision support for GPT-4o (image input)
- [ ] Add tool/function calling support matching OpenAI format
- [ ] Implement token counting using tiktoken algorithm
- [ ] Add batch API support for async processing
- [ ] Handle API errors: 429 (rate limit), 500, 503, context length exceeded

### 1.2 Enhanced Provider Router 🔴
**File:** `src-tauri/src/core/llm/router.rs`

Current: Basic fallback routing
Needed:
- [ ] Add 7 selection strategies:
  - `CostOptimized` - Cheapest provider for task
  - `SpeedOptimized` - Lowest latency provider
  - `QualityOptimized` - Best model for task type
  - `ReliabilityFocused` - Highest uptime provider
  - `LoadBalanced` - Distribute across providers
  - `Adaptive` - Learn from past performance
  - `WeightedComposite` - Custom weight scoring
- [ ] Implement `SelectionCriteria` struct with weights (cost, speed, quality, reliability)
- [ ] Add `ProviderScore` calculation with detailed metrics
- [ ] Implement performance history tracking per provider
- [ ] Add load tracking (requests in flight per provider)
- [ ] Create pattern-based selection memory (cache successful routes)

### 1.3 Load Balancer 🟠
**File:** `src-tauri/src/core/llm/load_balancer.rs` (new)

- [ ] Create `LoadBalancer` struct
- [ ] Implement `RoundRobin` algorithm
- [ ] Implement `LeastConnection` algorithm
- [ ] Implement `WeightedDistribution` algorithm
- [ ] Implement `PerformanceBased` distribution (route to fastest)
- [ ] Add health-aware load balancing (skip unhealthy providers)
- [ ] Track concurrent requests per provider
- [ ] Implement request queuing when all providers busy

### 1.4 Fallback Manager 🟠
**File:** `src-tauri/src/core/llm/fallback.rs` (new)

- [ ] Create `FallbackManager` struct
- [ ] Define `FallbackTier` enum (primary, secondary, tertiary, emergency)
- [ ] Implement graceful degradation strategies:
  - Model downgrade (claude-opus → claude-sonnet → claude-haiku)
  - Token reduction (summarize context)
  - Provider switch (Claude → Gemini → OpenAI → Ollama)
  - Context window reduction
- [ ] Add `DegradationStrategy` enum
- [ ] Implement automatic tier selection based on error type
- [ ] Track degradation events for analytics

### 1.5 Streaming Manager 🟠
**File:** `src-tauri/src/core/llm/streaming.rs` (new)

- [ ] Create `StreamingManager` struct
- [ ] Define `StreamingChunk` struct (content, finish_reason, usage)
- [ ] Implement provider-specific stream parsing:
  - Claude: event-stream format
  - OpenAI: SSE format
  - Gemini: JSON stream format
  - Ollama: newline-delimited JSON
- [ ] Add chunk aggregation for final response
- [ ] Implement stream cancellation
- [ ] Add timeout handling for stalled streams

### 1.6 Token Estimator 🟠
**File:** `src-tauri/src/core/llm/token_estimator.rs` (new)

- [ ] Create `TokenEstimator` struct
- [ ] Implement tiktoken-compatible counting for OpenAI models
- [ ] Implement Claude tokenization estimation
- [ ] Implement Gemini token counting
- [ ] Add message-level token estimation (role overhead)
- [ ] Add tool/function token estimation
- [ ] Implement context-aware estimation (system prompt caching)
- [ ] Add image token estimation for vision models

### 1.7 Rate Limiter 🟠
**File:** `src-tauri/src/core/llm/rate_limiter.rs` (new)

- [ ] Create `RateLimiter` struct
- [ ] Implement sliding window rate limiting
- [ ] Track tokens-per-minute (TPM) limits per provider
- [ ] Track requests-per-minute (RPM) limits per provider
- [ ] Add per-user rate limiting support
- [ ] Implement rate limit backoff with jitter
- [ ] Extract and respect provider rate limit headers
- [ ] Add queue with priority for rate-limited requests

### 1.8 Health Monitor 🟠
**File:** `src-tauri/src/core/llm/health_monitor.rs` (enhance existing)

Current: Basic health check
Needed:
- [ ] Add `ProviderStatus` enum (available, unavailable, rate_limited, quota_exceeded, degraded)
- [ ] Add `ErrorType` classification (auth, rate_limit, timeout, quota, network, server)
- [ ] Track success/error counts with sliding window
- [ ] Calculate uptime percentage per provider
- [ ] Track rate limit reset times
- [ ] Add latency percentiles (P50, P95, P99)
- [ ] Implement periodic background health checks
- [ ] Add health status change notifications

### 1.9 SLA Monitor 🟡
**File:** `src-tauri/src/core/llm/sla_monitor.rs` (new)

- [ ] Create `SLAMonitor` struct
- [ ] Define SLA targets (P95 latency < 200ms, 99.9% uptime)
- [ ] Track SLA compliance per provider
- [ ] Implement SLA violation detection
- [ ] Add SLA breach alerting
- [ ] Generate SLA compliance reports
- [ ] Track degraded performance periods

---

## 2. Model Selection Module

### 2.1 Task Categorizer 🟠
**File:** `src-tauri/src/core/task_categorizer.rs` (new)

- [ ] Create `TaskCategorizer` struct
- [ ] Define `TTRPGTaskType` enum:
  - `RuleLookup` - Finding rules in rulebooks
  - `CharacterGeneration` - Creating characters
  - `CombatResolution` - Combat mechanics
  - `NarrativeGeneration` - Story/description
  - `NPCDialogue` - NPC conversations
  - `WorldBuilding` - Locations, lore
  - `MechanicsCalculation` - Math, stats
  - `SessionSummary` - Recap generation
- [ ] Define `TaskComplexity` enum (simple, moderate, complex)
- [ ] Define `LatencyRequirement` enum (realtime, interactive, batch)
- [ ] Implement task classification from user input
- [ ] Add confidence scoring for classification
- [ ] Map task types to optimal models

### 2.2 A/B Testing Framework 🟡
**File:** `src-tauri/src/core/ab_testing.rs` (new)

- [ ] Create `ABTestingFramework` struct
- [ ] Define `ExperimentType` enum (model_comparison, load_testing, feature_testing)
- [ ] Define `ExperimentStatus` enum (planning, running, completed, paused, failed)
- [ ] Create `ExperimentVariant` struct (name, model, traffic_percentage)
- [ ] Implement experiment creation and management
- [ ] Add random variant assignment with consistent hashing
- [ ] Implement statistical significance calculation (p-value, confidence interval)
- [ ] Add result aggregation and analysis
- [ ] Implement auto-termination when significance reached
- [ ] Add experiment history persistence

### 2.3 User Preference Learner 🟡
**File:** `src-tauri/src/core/preference_learner.rs` (new)

- [ ] Create `PreferenceLearner` struct
- [ ] Define `FeedbackType` enum (quality, speed, cost, usefulness, preferred_provider)
- [ ] Create `UserFeedback` struct
- [ ] Create `UserPreferenceProfile` struct
- [ ] Implement feedback collection API
- [ ] Add preference weighting over time (decay old preferences)
- [ ] Generate model recommendations based on profile
- [ ] Persist profiles to database
- [ ] Add profile-based route optimization

### 2.4 Context-Aware Selector 🟡
**File:** `src-tauri/src/core/context_selector.rs` (new)

- [ ] Create `ContextAwareSelector` struct
- [ ] Define `SessionPhase` enum (planning, preparation, active, review)
- [ ] Define `CampaignGenre` enum (fantasy, sci_fi, horror, modern, steampunk, western, etc.)
- [ ] Create `SessionContext` struct
- [ ] Create `CampaignContext` struct
- [ ] Implement genre-specific model preferences
- [ ] Add session phase-aware routing (faster during combat)
- [ ] Implement dynamic context switching
- [ ] Cache selection decisions for similar contexts

---

## 3. Cost Optimization Module

### 3.1 Budget Enforcer 🔴
**File:** `src-tauri/src/core/budget.rs` (new)

- [ ] Create `BudgetEnforcer` struct
- [ ] Define `BudgetLimit` struct (amount, period: hourly/daily/monthly/total)
- [ ] Define `BudgetAction` enum (warn, throttle, degrade, reject)
- [ ] Implement spending velocity monitoring
- [ ] Add soft/hard/emergency limit tiers
- [ ] Implement automatic model downgrade when approaching limits
- [ ] Add budget reset scheduling
- [ ] Implement per-user budget tracking
- [ ] Add adaptive limit adjustment based on usage patterns
- [ ] Create budget status API for frontend

### 3.2 Cost Predictor 🟠
**File:** `src-tauri/src/core/cost_predictor.rs` (new)

- [ ] Create `CostPredictor` struct
- [ ] Define `ForecastHorizon` enum (hourly, daily, weekly, monthly)
- [ ] Implement usage pattern detection (cyclical, trending, stable)
- [ ] Add time-series forecasting (simple moving average initially)
- [ ] Implement anomaly detection in spending
- [ ] Generate 15-day cost forecast
- [ ] Add confidence intervals on predictions
- [ ] Persist historical data for trend analysis

### 3.3 Token Optimizer 🟠
**File:** `src-tauri/src/core/token_optimizer.rs` (new)

- [ ] Create `TokenOptimizer` struct
- [ ] Define `CompressionStrategy` enum:
  - `Summarization` - Summarize long contexts
  - `TokenPruning` - Remove low-value tokens
  - `ContextCompression` - Compress system prompts
- [ ] Implement message importance scoring
- [ ] Add semantic deduplication (remove redundant context)
- [ ] Implement adaptive compression based on budget remaining
- [ ] Create compressed prompt cache
- [ ] Add compression quality metrics

### 3.4 Alert System 🟠
**File:** `src-tauri/src/core/alerts.rs` (new)

- [ ] Create `AlertSystem` struct
- [ ] Define `AlertSeverity` enum (critical, high, medium, low)
- [ ] Define `AlertChannel` enum (log, webhook, system_notification)
- [ ] Define `AlertType` enum:
  - `BudgetApproaching` (80%, 90%, 95% thresholds)
  - `BudgetExceeded`
  - `QuotaExceeded`
  - `AnomalyDetected`
  - `ProviderDown`
  - `SLAViolation`
- [ ] Implement threshold-based alert triggering
- [ ] Add alert deduplication (don't spam same alert)
- [ ] Implement webhook delivery for external integration
- [ ] Add system notification delivery (desktop notifications)
- [ ] Create alert history with acknowledgment

### 3.5 Pricing Engine 🟠
**File:** `src-tauri/src/core/pricing.rs` (enhance existing in models.rs)

Current: Basic cost estimation
Needed:
- [ ] Create comprehensive `PricingEngine` struct
- [ ] Add per-model pricing (input/output per 1M tokens):
  - Claude Opus: $15/$75
  - Claude Sonnet: $3/$15
  - Claude Haiku: $0.25/$1.25
  - GPT-4o: $2.50/$10
  - GPT-4o-mini: $0.15/$0.60
  - Gemini Pro: $1.25/$5
  - Gemini Flash: $0.075/$0.30
- [ ] Add cached input token pricing (reduced rates)
- [ ] Implement batch API pricing (50% discount)
- [ ] Add volume tier discounts
- [ ] Create real-time cost calculator
- [ ] Track costs per conversation/session

---

## 4. Search Module

### 4.1 Query Expansion 🟠
**File:** `src-tauri/src/core/query_expansion.rs` (new)

- [ ] Create `QueryExpander` struct
- [ ] Implement synonym expansion using word embeddings
- [ ] Add TTRPG-specific synonym map:
  - "HP" → "hit points", "health"
  - "AC" → "armor class", "defense"
  - "DC" → "difficulty class", "check"
- [ ] Implement related term suggestion
- [ ] Add context-based expansion (campaign-specific terms)
- [ ] Implement stemming/lemmatization
- [ ] Add wildcard and fuzzy matching

### 4.2 Spell Correction 🟡
**File:** `src-tauri/src/core/spell_correction.rs` (new)

- [ ] Create `SpellCorrector` struct
- [ ] Implement Levenshtein distance calculation
- [ ] Build TTRPG vocabulary dictionary
- [ ] Add phonetic matching (Soundex/Metaphone)
- [ ] Implement "did you mean?" suggestions
- [ ] Add auto-correction for common typos
- [ ] Build learning dictionary from indexed documents

### 4.3 Search Analytics 🟡
**File:** `src-tauri/src/core/search_analytics.rs` (new)

- [ ] Create `SearchAnalytics` struct
- [ ] Track query frequency
- [ ] Track result click-through rates
- [ ] Measure search success (found what looking for)
- [ ] Identify popular queries
- [ ] Track zero-result queries
- [ ] Generate search quality reports
- [ ] Persist analytics to database

### 4.4 Faceted Search 🟡
**File:** `src-tauri/src/core/faceted_search.rs` (new)

- [ ] Create `FacetedSearch` struct
- [ ] Define facets for TTRPG content:
  - Source book
  - Content type (spell, monster, rule, equipment)
  - Level/CR range
  - School (for spells)
  - Category
- [ ] Implement facet extraction from documents
- [ ] Add facet filtering to search queries
- [ ] Return facet counts with search results
- [ ] Support multi-select facets

---

## 5. Document Processing Module

### 5.1 MOBI/AZW Parser 🟡
**File:** `src-tauri/src/ingestion/mobi_parser.rs` (new)

- [ ] Add `mobi` crate dependency
- [ ] Create `MobiParser` struct
- [ ] Implement MOBI format detection
- [ ] Extract text content from MOBI
- [ ] Handle AZW/AZW3 Kindle formats
- [ ] Extract metadata (title, author, publisher)
- [ ] Handle DRM-free files only (document limitation)
- [ ] Add format conversion to standard text

### 5.2 Parallel Document Processing 🟠
**File:** `src-tauri/src/ingestion/pipeline.rs` (new)

- [ ] Create `DocumentPipeline` struct
- [ ] Implement parallel processing with configurable worker count
- [ ] Add job queue for document processing
- [ ] Implement progress tracking per document
- [ ] Add batch processing API
- [ ] Implement partial failure handling (continue on single doc failure)
- [ ] Add processing priority queue
- [ ] Create processing status API for frontend

### 5.3 Enhanced Adaptive Learning 🟡
**File:** `src-tauri/src/ingestion/adaptive_learning.rs` (enhance existing)

Current: Basic pattern storage
Needed:
- [ ] Implement document type classification (rulebook, adventure, supplement)
- [ ] Add format-specific extraction optimization
- [ ] Learn header detection patterns per source
- [ ] Improve table extraction based on feedback
- [ ] Add OCR confidence tracking
- [ ] Implement extraction quality scoring
- [ ] Persist learned patterns to database

---

## 6. Campaign Module

### 6.1 Campaign Versioning 🟠
**File:** `src-tauri/src/core/campaign_manager.rs` (enhance existing)

Current: Basic CRUD
Needed:
- [ ] Add `CampaignVersion` struct (version_id, timestamp, changes, snapshot)
- [ ] Implement `create_snapshot()` for manual versioning
- [ ] Implement auto-snapshot on significant changes
- [ ] Add `list_versions()` API
- [ ] Implement `rollback_to_version()`
- [ ] Add version diff comparison
- [ ] Implement version pruning (keep last N versions)
- [ ] Add version description/notes

### 6.2 Location Management 🟡
**File:** `src-tauri/src/core/location_manager.rs` (new)

- [ ] Create `LocationManager` struct
- [ ] Define `Location` struct:
  - id, name, description
  - location_type (city, dungeon, wilderness, building)
  - parent_location_id (for hierarchy)
  - connections (list of connected location IDs)
  - npcs_present (list of NPC IDs)
  - notable_features
  - custom_attributes
- [ ] Implement CRUD operations
- [ ] Add location hierarchy traversal
- [ ] Implement location search
- [ ] Add location-NPC linking

### 6.3 Plot Point Tracking 🟡
**File:** `src-tauri/src/core/plot_manager.rs` (new)

- [ ] Create `PlotManager` struct
- [ ] Define `PlotPoint` struct:
  - id, title, description
  - status (active, completed, failed, pending)
  - priority (main, side, background)
  - involved_npcs, involved_locations
  - prerequisites (other plot point IDs)
  - consequences
- [ ] Implement CRUD operations
- [ ] Add plot point status transitions
- [ ] Implement dependency tracking
- [ ] Add timeline visualization data

### 6.4 Rulebook Linker 🟡
**File:** `src-tauri/src/core/rulebook_linker.rs` (new)

- [ ] Create `RulebookLinker` struct
- [ ] Implement campaign-to-rulebook association
- [ ] Auto-suggest rulebooks based on campaign system
- [ ] Add rule reference embedding in campaign context
- [ ] Implement citation management
- [ ] Track which rules are referenced in campaign

---

## 7. Session Module

### 7.1 Enhanced Initiative Tracker 🟠
**File:** `src-tauri/src/core/session_manager.rs` (enhance existing)

Current: Basic initiative
Needed:
- [ ] Add `InitiativeEntry` struct with full tracking:
  - combatant_id, initiative_roll, initiative_modifier
  - delayed (bool), ready_action (Option<String>)
  - reactions_used, legendary_actions_remaining
- [ ] Implement initiative tie-breaking (DEX modifier, then roll-off)
- [ ] Add delay turn functionality
- [ ] Add ready action tracking
- [ ] Implement surprise round handling
- [ ] Add lair action tracking (specific initiative counts)
- [ ] Support legendary actions between turns

### 7.2 Condition Tracking 🟠
**File:** `src-tauri/src/core/conditions.rs` (new)

- [ ] Create `ConditionManager` struct
- [ ] Define all D&D 5e conditions with effects:
  - Blinded, Charmed, Deafened, Frightened
  - Grappled, Incapacitated, Invisible, Paralyzed
  - Petrified, Poisoned, Prone, Restrained
  - Stunned, Unconscious, Exhaustion (6 levels)
- [ ] Implement condition application with duration
- [ ] Add automatic condition removal on turn end/start
- [ ] Track concentration for spell conditions
- [ ] Add condition effect reminders
- [ ] Support custom conditions

### 7.3 Damage Type Tracking 🟡
**File:** `src-tauri/src/core/damage.rs` (new)

- [ ] Create `DamageTracker` struct
- [ ] Define damage types:
  - Physical: bludgeoning, piercing, slashing
  - Elemental: acid, cold, fire, lightning, thunder
  - Other: force, necrotic, poison, psychic, radiant
- [ ] Implement resistance/vulnerability/immunity tracking per combatant
- [ ] Auto-calculate damage with resistances applied
- [ ] Track damage source for death save failures
- [ ] Add damage history per combat

### 7.4 Session Notes with AI Categorization 🟡
**File:** `src-tauri/src/core/session_notes.rs` (new)

- [ ] Create `SessionNoteManager` struct
- [ ] Define `NoteCategory` enum (plot, combat, character, npc, mechanics, lore, other)
- [ ] Implement LLM-based note categorization
- [ ] Add tagged entity extraction (NPC names, locations)
- [ ] Implement note search within session
- [ ] Add cross-session note linking
- [ ] Generate session summary from notes

### 7.5 Session Summary Generation 🟡
**File:** `src-tauri/src/core/session_summary.rs` (new)

- [ ] Create `SessionSummarizer` struct
- [ ] Implement LLM-based summary generation
- [ ] Extract key events, combat outcomes
- [ ] List NPCs encountered
- [ ] Track XP/loot awarded
- [ ] Generate "previously on..." recap
- [ ] Add summary templates (brief, detailed, narrative)

---

## 8. Character Generation Module

### 8.1 Extended Genre Support 🟠
**File:** `src-tauri/src/core/character_gen.rs` (enhance existing)

Current: D&D 5e, Pathfinder, CoC
Needed:
- [ ] Add `GenreSpecificData` enum:
  ```rust
  enum GenreSpecificData {
      Cyberpunk(CyberpunkData),
      SciFi(SciFiData),
      CosmicHorror(CosmicHorrorData),
      PostApocalyptic(PostApocData),
      Superhero(SuperheroData),
  }
  ```
- [ ] Implement `CyberpunkData`:
  - Cyberware slots and implants
  - Neural interface level
  - Hacking skill tree
  - Street cred/reputation
- [ ] Implement `SciFiData`:
  - Starship certifications
  - Alien contacts
  - Tech specializations
- [ ] Implement `CosmicHorrorData`:
  - Sanity score and threshold
  - Forbidden knowledge list
  - Trauma history
- [ ] Implement `PostApocData`:
  - Mutation list
  - Radiation resistance
  - Scavenging skills
- [ ] Implement `SuperheroData`:
  - Power list with levels
  - Weakness
  - Origin story type
  - Secret identity

### 8.2 Point Buy System 🟡
**File:** `src-tauri/src/core/stat_generation.rs` (new)

- [ ] Create `StatGenerator` struct
- [ ] Implement point buy with configurable points (default 27)
- [ ] Add point cost table (8=0, 9=1, 10=2, ..., 15=9)
- [ ] Validate point buy constraints
- [ ] Implement standard array option (15,14,13,12,10,8)
- [ ] Add 4d6-drop-lowest random generation
- [ ] Implement 3d6 straight for old-school
- [ ] Add racial modifier application

### 8.3 Equipment Generator 🟡
**File:** `src-tauri/src/core/equipment_gen.rs` (new)

- [ ] Create `EquipmentGenerator` struct
- [ ] Define starting equipment by class
- [ ] Implement starting gold alternative
- [ ] Add equipment pack contents
- [ ] Implement encumbrance calculation
- [ ] Add magic item generation (by rarity)
- [ ] Support custom equipment lists

### 8.4 Name Generator 🟡
**File:** `src-tauri/src/core/name_gen.rs` (new)

- [ ] Create `NameGenerator` struct
- [ ] Add race-specific name tables:
  - Human (by culture: Norse, Celtic, Arabic, etc.)
  - Elven (Sindarin-inspired)
  - Dwarven (Germanic-inspired)
  - Orcish, Goblin, Dragonborn, Tiefling, etc.
- [ ] Support gender variants
- [ ] Add surname/clan name generation
- [ ] Implement title generation
- [ ] Add nickname generation

---

## 9. Voice Synthesis Module

### 9.1 Fish Audio Provider 🟡
**File:** `src-tauri/src/core/voice_fish.rs` (new)

- [ ] Add Fish Audio API client
- [ ] Implement authentication
- [ ] Add voice list retrieval
- [ ] Implement synthesis request
- [ ] Add streaming audio support
- [ ] Handle rate limits

### 9.2 Audio Caching 🟠
**File:** `src-tauri/src/core/audio_cache.rs` (new)

- [ ] Create `AudioCacheManager` struct
- [ ] Implement LRU cache with configurable size limit (default 5GB)
- [ ] Add cache key generation (hash of text + voice + settings)
- [ ] Implement cache hit/miss tracking
- [ ] Add cache cleanup on limit exceeded
- [ ] Implement persistent cache directory
- [ ] Add cache prewarming for common phrases

### 9.3 Voice Profile Manager 🟡
**File:** `src-tauri/src/core/voice_profiles.rs` (new)

- [ ] Create `VoiceProfileManager` struct
- [ ] Define `VoiceProfile` struct:
  - profile_id (e.g., "dm_narrator", "npc_tavern_keeper")
  - provider
  - voice_id
  - language
  - speed/rate
  - pitch_adjustment
  - emotion_default
- [ ] Implement CRUD for profiles
- [ ] Add NPC-to-voice mapping
- [ ] Implement genre-specific voice styles
- [ ] Add voice preview generation

### 9.4 Pre-generation Queue 🟡
**File:** `src-tauri/src/core/voice_queue.rs` (new)

- [ ] Create `PreGenerationQueue` struct
- [ ] Define `PreGenJob` struct (text, voice_profile, priority, status)
- [ ] Implement background job processing
- [ ] Add job status tracking
- [ ] Implement batch session preparation
- [ ] Add job cancellation
- [ ] Implement priority queue ordering

---

## 10. Security Module

### 10.1 Input Validator 🔴
**File:** `src-tauri/src/core/input_validator.rs` (new)

- [ ] Create `InputValidator` struct
- [ ] Implement XSS prevention (sanitize HTML)
- [ ] Implement SQL injection prevention (parameterized queries only)
- [ ] Implement path traversal prevention
- [ ] Add command injection prevention
- [ ] Implement input length limits
- [ ] Add content type validation
- [ ] Create validation middleware for Tauri commands

### 10.2 Audit Logger 🟠
**File:** `src-tauri/src/core/audit.rs` (new)

- [ ] Create `AuditLogger` struct
- [ ] Define audit event types:
  - API key added/removed
  - Document ingested
  - Campaign created/deleted
  - Settings changed
  - LLM request made
- [ ] Implement structured audit logging
- [ ] Add timestamp and context to all events
- [ ] Persist audit log to SQLite
- [ ] Implement audit log rotation
- [ ] Add audit log export

### 10.3 Rate Limiter (API) 🟠
**File:** `src-tauri/src/core/api_rate_limiter.rs` (new)

- [ ] Create `ApiRateLimiter` struct
- [ ] Implement per-command rate limiting
- [ ] Add sliding window algorithm
- [ ] Configure limits per command type
- [ ] Return rate limit headers equivalent
- [ ] Add rate limit bypass for admin operations

---

## 11. Database Module

### 11.1 Connection Pooling 🟠
**File:** `src-tauri/src/database/mod.rs` (enhance existing)

Current: Single connection
Needed:
- [ ] Implement connection pool with SQLx pool
- [ ] Configure min/max connections
- [ ] Add connection timeout handling
- [ ] Implement connection health checks
- [ ] Add pool statistics API

### 11.2 Additional Tables 🟠
**File:** `src-tauri/src/database/migrations.rs` (enhance)

- [ ] Add `locations` table
- [ ] Add `plot_points` table
- [ ] Add `conditions` table (active conditions per combatant)
- [ ] Add `damage_log` table
- [ ] Add `audit_log` table
- [ ] Add `voice_profiles` table
- [ ] Add `audio_cache_metadata` table
- [ ] Add `experiments` table (A/B testing)
- [ ] Add `user_preferences` table

### 11.3 Query Optimization 🟡
**File:** `src-tauri/src/database/mod.rs` (enhance)

- [ ] Add database indices for common queries
- [ ] Implement query result caching
- [ ] Add prepared statement caching
- [ ] Implement batch insert/update
- [ ] Add query performance logging

---

## 12. Logging & Monitoring

### 12.1 Structured Logging 🟠
**File:** `src-tauri/src/core/logging.rs` (new)

- [ ] Add `tracing` with JSON output format
- [ ] Implement correlation ID tracking across requests
- [ ] Add request/response logging for LLM calls
- [ ] Implement log levels per module
- [ ] Add performance timing logs
- [ ] Implement log file rotation
- [ ] Add log export functionality

### 12.2 Metrics Collection 🟡
**File:** `src-tauri/src/core/metrics.rs` (new)

- [ ] Create `MetricsCollector` struct
- [ ] Track LLM latency per provider
- [ ] Track token usage over time
- [ ] Track error rates per provider
- [ ] Track search query performance
- [ ] Track document processing time
- [ ] Add metrics aggregation (1min, 5min, 1hour windows)
- [ ] Implement metrics export API for frontend

---

## 13. MCP Compatibility (Optional)

### 13.1 MCP Server Mode 🟢
**File:** `src-tauri/src/mcp/server.rs` (new)

- [ ] Implement MCP JSON-RPC protocol
- [ ] Add stdio transport
- [ ] Register tools matching original MCP tools
- [ ] Implement tool listing (`tools/list`)
- [ ] Implement tool execution (`tools/call`)
- [ ] Add resource support if needed
- [ ] Enable Claude Desktop integration

---

# FRONTEND TASKS

## 14. Theme & Styling

### 14.1 Dark/Light Theme Toggle 🟠
**File:** `frontend/src/theme.rs` (new)

- [ ] Create `ThemeProvider` context
- [ ] Define color palettes for dark and light modes
- [ ] Implement theme persistence to localStorage
- [ ] Add system preference detection
- [ ] Create theme toggle component
- [ ] Apply theme to all components

### 14.2 Consistent Design System 🟠
**File:** `frontend/src/components/design_system.rs` (new)

- [ ] Create reusable button variants (primary, secondary, danger, ghost)
- [ ] Create input field components (text, number, select, textarea)
- [ ] Create card/panel components
- [ ] Create modal/dialog component
- [ ] Create toast/notification component
- [ ] Create loading spinner/skeleton components
- [ ] Create badge/tag components
- [ ] Create tooltip component
- [ ] Document all components

### 14.3 Responsive Layout 🟠
**Files:** All component files

- [ ] Implement mobile-first responsive design
- [ ] Add breakpoints (sm: 640px, md: 768px, lg: 1024px, xl: 1280px)
- [ ] Create responsive navigation (hamburger menu on mobile)
- [ ] Ensure all grids collapse properly on small screens
- [ ] Test on various screen sizes

---

## 15. Chat Interface

### 15.1 Message Formatting 🟠
**File:** `frontend/src/components/chat.rs` (enhance)

- [ ] Add Markdown rendering for assistant messages
- [ ] Implement code block syntax highlighting
- [ ] Add collapsible long messages
- [ ] Implement message copy button
- [ ] Add message regeneration button
- [ ] Show message timestamp on hover
- [ ] Add message reactions (thumbs up/down for feedback)

### 15.2 Streaming Response Display 🔴
**File:** `frontend/src/components/chat.rs` (enhance)

- [ ] Implement real-time token streaming display
- [ ] Add typing indicator during generation
- [ ] Show partial response as it streams
- [ ] Add stop generation button
- [ ] Implement smooth text appearance animation

### 15.3 Context Sidebar 🟡
**File:** `frontend/src/components/chat_context.rs` (new)

- [ ] Create collapsible context sidebar
- [ ] Show active campaign info
- [ ] Show active session info
- [ ] Display current combatants (if in combat)
- [ ] Show quick NPC reference
- [ ] Add context injection controls

### 15.4 Chat History 🟡
**File:** `frontend/src/components/chat_history.rs` (new)

- [ ] Implement conversation persistence
- [ ] Add conversation list sidebar
- [ ] Implement conversation search
- [ ] Add conversation delete/archive
- [ ] Implement conversation export (Markdown, JSON)
- [ ] Add conversation sharing (export link)

---

## 16. Settings Interface

### 16.1 Provider Configuration UI 🟠
**File:** `frontend/src/components/settings.rs` (enhance)

- [ ] Add OpenAI configuration section
- [ ] Add model selection dropdowns per provider
- [ ] Add API key validation with test button
- [ ] Show provider health status indicators
- [ ] Add cost tracking toggle
- [ ] Implement provider priority ordering (drag-drop)
- [ ] Add custom endpoint configuration (for proxies)

### 16.2 Budget Settings 🟠
**File:** `frontend/src/components/budget_settings.rs` (new)

- [ ] Create budget configuration panel
- [ ] Add daily/weekly/monthly limit inputs
- [ ] Add soft/hard limit configuration
- [ ] Implement alert threshold settings
- [ ] Add current spending display
- [ ] Show spending projection
- [ ] Add budget reset controls

### 16.3 Voice Settings 🟡
**File:** `frontend/src/components/voice_settings.rs` (new)

- [ ] Create voice provider configuration
- [ ] Add ElevenLabs API key input
- [ ] Add voice profile management
- [ ] Implement voice preview playback
- [ ] Add default voice selection
- [ ] Configure audio output device
- [ ] Add volume controls

### 16.4 Advanced Settings 🟡
**File:** `frontend/src/components/advanced_settings.rs` (new)

- [ ] Add logging level configuration
- [ ] Add cache management (clear caches)
- [ ] Add data export/import
- [ ] Add database backup controls
- [ ] Add performance settings (worker threads, etc.)
- [ ] Add experimental features toggle

---

## 17. Library Interface

### 17.1 File Upload with Progress 🔴
**File:** `frontend/src/components/library.rs` (enhance)

- [ ] Implement native file picker via Tauri
- [ ] Add multi-file selection
- [ ] Show upload progress per file
- [ ] Add cancel upload button
- [ ] Show processing status (extracting, chunking, indexing)
- [ ] Display error messages per file
- [ ] Add retry failed uploads

### 17.2 Document Management 🟠
**File:** `frontend/src/components/document_list.rs` (new)

- [ ] Create document list with sorting (name, date, size, status)
- [ ] Add document search/filter
- [ ] Implement document preview (first page/chapter)
- [ ] Add document details panel (page count, chunk count, size)
- [ ] Implement document deletion with confirmation
- [ ] Add document reprocessing option
- [ ] Show indexing status

### 17.3 Search Results UI 🟠
**File:** `frontend/src/components/search_results.rs` (new)

- [ ] Create search result cards with:
  - Source document name
  - Relevance score
  - Content snippet with highlighted matches
  - Page/section reference
- [ ] Implement infinite scroll or pagination
- [ ] Add result filtering (by source, by type)
- [ ] Add result sorting (relevance, date)
- [ ] Implement "more like this" for results
- [ ] Add result bookmarking

### 17.4 Search Filters Panel 🟡
**File:** `frontend/src/components/search_filters.rs` (new)

- [ ] Create collapsible filter sidebar
- [ ] Add source document filter (multi-select)
- [ ] Add content type filter (spell, monster, rule, etc.)
- [ ] Add date range filter (if applicable)
- [ ] Add search type toggle (hybrid, semantic, keyword)
- [ ] Show active filters with clear buttons

---

## 18. Campaign Interface

### 18.1 Campaign Dashboard 🟠
**File:** `frontend/src/components/campaign_dashboard.rs` (new)

- [ ] Create campaign overview page with:
  - Campaign stats (sessions, NPCs, locations)
  - Recent activity feed
  - Quick action buttons
  - Active quest summary
- [ ] Add campaign cover image upload
- [ ] Show player character list
- [ ] Display next session scheduling

### 18.2 NPC Management UI 🟠
**File:** `frontend/src/components/npc_manager.rs` (new)

- [ ] Create NPC list with cards/table view toggle
- [ ] Add NPC creation form:
  - Name, role, description
  - Personality traits
  - Stats (optional)
  - Voice profile selection
  - Relationship to PCs
- [ ] Implement NPC search and filter
- [ ] Add NPC quick reference popup
- [ ] Implement NPC deletion with confirmation

### 18.3 Location Manager UI 🟡
**File:** `frontend/src/components/location_manager.rs` (new)

- [ ] Create location hierarchy view (tree)
- [ ] Add location creation form
- [ ] Implement location map upload (image)
- [ ] Show NPCs at location
- [ ] Add location connections (graph view)
- [ ] Implement location search

### 18.4 Plot Tracker UI 🟡
**File:** `frontend/src/components/plot_tracker.rs` (new)

- [ ] Create plot point kanban board (pending, active, completed)
- [ ] Add plot point creation form
- [ ] Implement drag-drop status changes
- [ ] Show plot point dependencies
- [ ] Add timeline view
- [ ] Implement plot point linking to sessions

### 18.5 Campaign Timeline 🟡
**File:** `frontend/src/components/campaign_timeline.rs` (new)

- [ ] Create visual timeline component
- [ ] Show sessions as timeline events
- [ ] Display major plot points
- [ ] Add in-game date tracking
- [ ] Implement timeline navigation (zoom, pan)
- [ ] Add event details on click

---

## 19. Session Interface

### 19.1 Combat Tracker Enhancement 🔴
**File:** `frontend/src/components/session.rs` (enhance)

Current: Basic initiative list
Needed:
- [ ] Add HP bars with visual health status
- [ ] Implement damage/heal input with damage type
- [ ] Add condition badges on combatant cards
- [ ] Implement condition management popup
- [ ] Add death save tracking for PCs
- [ ] Implement legendary action tracking
- [ ] Add reaction tracking
- [ ] Show current turn highlight
- [ ] Add combat log sidebar
- [ ] Implement round counter with timer

### 19.2 Quick Reference Panel 🟠
**File:** `frontend/src/components/quick_reference.rs` (new)

- [ ] Create slide-out reference panel
- [ ] Add condition reference cards
- [ ] Add action economy reference
- [ ] Implement quick rule search
- [ ] Add dice roller integration
- [ ] Show commonly used rules

### 19.3 Session Notes UI 🟠
**File:** `frontend/src/components/session_notes.rs` (new)

- [ ] Create note-taking panel during session
- [ ] Add quick note buttons (plot, combat, NPC)
- [ ] Implement auto-tagging suggestions
- [ ] Add voice-to-text notes (if supported)
- [ ] Show note history for session
- [ ] Implement note export

### 19.4 Session Summary View 🟡
**File:** `frontend/src/components/session_summary.rs` (new)

- [ ] Create post-session summary page
- [ ] Display AI-generated recap
- [ ] Show loot and XP awarded
- [ ] List NPCs encountered
- [ ] Show combat statistics
- [ ] Add manual summary editing
- [ ] Implement summary export/share

---

## 20. Character Interface

### 20.1 Character Sheet View 🟠
**File:** `frontend/src/components/character_sheet.rs` (new)

- [ ] Create full character sheet layout:
  - Stats block with modifiers
  - Skills list with proficiencies
  - Combat stats (HP, AC, initiative, speed)
  - Equipment list
  - Features and traits
  - Spellcasting (if applicable)
  - Backstory section
- [ ] Implement editable fields
- [ ] Add character level up flow
- [ ] Add character export (PDF, JSON)

### 20.2 Character Generation Wizard 🟠
**File:** `frontend/src/components/character.rs` (enhance)

Current: Basic generator
Needed:
- [ ] Create multi-step wizard flow:
  1. System selection
  2. Race selection with preview
  3. Class selection with preview
  4. Stat generation method choice
  5. Background selection
  6. Equipment selection
  7. Name and details
  8. Backstory generation
  9. Review and confirm
- [ ] Add random options at each step
- [ ] Show running character preview
- [ ] Implement step navigation

### 20.3 Character Gallery 🟡
**File:** `frontend/src/components/character_gallery.rs` (new)

- [ ] Create character card grid view
- [ ] Add character filtering (by system, level, class)
- [ ] Implement character search
- [ ] Add character comparison view
- [ ] Implement character duplication
- [ ] Add character archival

---

## 21. Voice Interface

### 21.1 Voice Playback Controls 🟡
**File:** `frontend/src/components/voice_player.rs` (new)

- [ ] Create audio player component
- [ ] Add play/pause/stop controls
- [ ] Implement progress bar
- [ ] Add volume control
- [ ] Show current voice profile
- [ ] Add playback speed control
- [ ] Implement queue management

### 21.2 Voice Generation UI 🟡
**File:** `frontend/src/components/voice_generator.rs` (new)

- [ ] Create text-to-speech input form
- [ ] Add voice profile selector
- [ ] Add emotion selector
- [ ] Implement preview before generation
- [ ] Show generation progress
- [ ] Add save to library option

---

## 22. Analytics Dashboard

### 22.1 Usage Analytics 🟡
**File:** `frontend/src/components/analytics.rs` (new)

- [ ] Create analytics dashboard page
- [ ] Add token usage chart (line graph over time)
- [ ] Add cost breakdown chart (pie by provider)
- [ ] Show request count metrics
- [ ] Add provider performance comparison
- [ ] Implement date range selector
- [ ] Add data export

### 22.2 Search Analytics 🟢
**File:** `frontend/src/components/search_analytics.rs` (new)

- [ ] Show popular queries
- [ ] Display search success rate
- [ ] List zero-result queries
- [ ] Show click-through rates

---

## 23. Onboarding & Help

### 23.1 First-Run Wizard 🟡
**File:** `frontend/src/components/onboarding.rs` (new)

- [ ] Create first-run detection
- [ ] Implement welcome screen
- [ ] Add API key setup step
- [ ] Add first document ingestion prompt
- [ ] Add campaign creation prompt
- [ ] Show feature highlights

### 23.2 Help System 🟡
**File:** `frontend/src/components/help.rs` (new)

- [ ] Add help button/tooltip system
- [ ] Create keyboard shortcuts reference
- [ ] Add contextual help popups
- [ ] Implement searchable help docs
- [ ] Add "what's new" changelog

---

## 24. Accessibility

### 24.1 Keyboard Navigation 🟠
**Files:** All component files

- [ ] Ensure all interactive elements are focusable
- [ ] Implement keyboard shortcuts:
  - Ctrl+K: Quick search
  - Ctrl+N: New chat
  - Ctrl+/: Help
  - Escape: Close modals
- [ ] Add focus indicators
- [ ] Implement skip links

### 24.2 Screen Reader Support 🟡
**Files:** All component files

- [ ] Add ARIA labels to all interactive elements
- [ ] Implement ARIA live regions for dynamic content
- [ ] Add alt text for images
- [ ] Ensure proper heading hierarchy
- [ ] Test with screen readers

---

# TASK PRIORITIZATION

## Phase 1: Core Parity (Critical) 🔴
1. OpenAI Provider
2. Budget Enforcer
3. Streaming Response Display
4. File Upload with Progress
5. Combat Tracker Enhancement
6. Input Validator

## Phase 2: Enhanced Experience (High) 🟠
1. Enhanced Provider Router
2. Load Balancer
3. Health Monitor Enhancement
4. Query Expansion
5. Task Categorizer
6. Provider Configuration UI
7. Message Formatting
8. Document Management
9. Search Results UI
10. Session Notes UI

## Phase 3: Advanced Features (Medium) 🟡
1. A/B Testing Framework
2. Cost Predictor
3. Spell Correction
4. Genre Support
5. Voice Profile Manager
6. Campaign Dashboard
7. NPC Management
8. Character Sheet View
9. Analytics Dashboard

## Phase 4: Polish (Low) 🟢
1. MCP Server Mode
2. Search Analytics
3. Help System
4. Screen Reader Support

---

# ESTIMATED EFFORT

| Category | Tasks | Est. Hours |
|----------|-------|------------|
| AI Providers | 9 | 80-100 |
| Model Selection | 4 | 30-40 |
| Cost Optimization | 5 | 40-50 |
| Search | 4 | 25-35 |
| Document Processing | 3 | 20-25 |
| Campaign | 4 | 30-35 |
| Session | 5 | 40-50 |
| Character | 4 | 30-40 |
| Voice | 4 | 25-30 |
| Security | 3 | 20-25 |
| Database | 3 | 15-20 |
| Logging | 2 | 10-15 |
| **Backend Total** | **50** | **365-465** |
| | | |
| Theme/Design | 3 | 25-30 |
| Chat Interface | 4 | 30-40 |
| Settings | 4 | 25-30 |
| Library | 4 | 30-40 |
| Campaign UI | 5 | 40-50 |
| Session UI | 4 | 35-45 |
| Character UI | 3 | 25-35 |
| Voice UI | 2 | 15-20 |
| Analytics | 2 | 15-20 |
| Onboarding | 2 | 10-15 |
| Accessibility | 2 | 15-20 |
| **Frontend Total** | **35** | **265-345** |
| | | |
| **GRAND TOTAL** | **85** | **630-810** |

---

*Generated by Claude Code for TTTRPS feature parity planning*
