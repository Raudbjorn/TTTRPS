# Requirements: Embedded Meilisearch + SurrealDB Vector Store Integration

## Overview

Replace the current HTTP-based Meilisearch SDK integration and in-Meilisearch vector storage with:
1. **meilisearch-lib**: Embedded library for direct in-process search without HTTP server
2. **SurrealDB**: Multi-model database for vector storage, replacing Meilisearch's experimental vectorStore

This integration eliminates the sidecar process management complexity and provides a cleaner separation of concerns: Meilisearch for full-text search, SurrealDB for vectors and hybrid fusion.

---

## User Stories

### US-1: Simplified Deployment
**As a** user installing TTRPG Assistant,
**I want** the application to work without downloading or managing external processes,
**So that** installation is reliable across all platforms without network dependencies.

### US-2: Faster Search Startup
**As a** user opening the application,
**I want** search functionality to be immediately available,
**So that** I don't have to wait for an external process to initialize.

### US-3: Reliable Vector Search
**As a** user performing semantic search on my TTRPG documents,
**I want** vector similarity search to work reliably with proper HNSW indexing,
**So that** I get relevant results based on meaning, not just keywords.

### US-4: Hybrid Search Quality
**As a** a Game Master searching for rules or lore,
**I want** hybrid search combining keyword and semantic results,
**So that** I find relevant content whether I use exact terms or describe concepts.

### US-5: Data Portability
**As a** user managing my document library,
**I want** my indexed documents and vectors to survive application updates,
**So that** I don't have to re-ingest my entire library after upgrades.

### US-6: Resource Efficiency
**As a** user running TTRPG Assistant alongside other applications,
**I want** the application to use minimal system resources when idle,
**So that** it doesn't impact my system performance.

---

## Functional Requirements

### FR-1: Embedded Meilisearch Library Integration

#### FR-1.1: Library Initialization
- WHEN application starts THEN system SHALL initialize meilisearch-lib with configured database path
- IF database path does not exist THEN system SHALL create required directories
- WHEN initialization fails THEN system SHALL display error and degrade gracefully to no-search mode

#### FR-1.2: Index Management
- WHEN user ingests first document THEN system SHALL create required indexes (rules, fiction, chat, documents, library_metadata, ttrpg)
- WHEN index operation completes THEN system SHALL await task completion before returning
- IF index creation fails THEN system SHALL report specific error to user

#### FR-1.3: Document Operations
- WHEN user adds documents THEN system SHALL add via meilisearch-lib `add_documents()` method
- WHEN documents are updated THEN system SHALL use `update_documents()` for partial updates
- WHEN documents are deleted THEN system SHALL use `delete_document()` or `delete_documents_batch()`
- WHEN document operations complete THEN system SHALL wait for task status before confirming

#### FR-1.4: Settings Configuration
- WHEN user configures searchable/filterable attributes THEN system SHALL apply via `update_settings()`
- WHEN settings are retrieved THEN system SHALL use `get_settings()` with API key masking
- WHEN settings are reset THEN system SHALL use `reset_settings()`

#### FR-1.5: Search Operations
- WHEN user performs keyword search THEN system SHALL use meilisearch-lib `search()` with keyword query
- WHEN search includes filters THEN system SHALL apply filter expressions via SearchQuery
- WHEN pagination is requested THEN system SHALL use offset/limit parameters

---

### FR-2: SurrealDB Vector Storage Integration

#### FR-2.1: Database Initialization
- WHEN application starts THEN system SHALL initialize SurrealDB with embedded RocksDB storage
- WHEN initialization completes THEN system SHALL set namespace and database context
- IF initialization fails THEN system SHALL report error and disable vector search

#### FR-2.2: Vector Schema
- WHEN database initializes THEN system SHALL create documents table with schema:
  - `id`: string (primary key)
  - `index_uid`: string (source Meilisearch index)
  - `document_id`: string (Meilisearch document reference)
  - `content_hash`: string (deduplication key)
  - `embedding`: array (vector data, dimensions per embedder)
  - `metadata`: object (arbitrary metadata)
  - `created_at`: datetime
  - `updated_at`: datetime

#### FR-2.3: Vector Index Management
- WHEN documents table has data THEN system SHALL create HNSW index on embedding field
- WHEN creating HNSW index THEN system SHALL configure:
  - DIMENSION matching embedder output (768, 1024, 1536, etc.)
  - DIST as COSINE (default for text embeddings)
  - EFC as 200 (construction effort)
  - M as 16 (connections per element)
- WHEN index needs rebuild THEN system SHALL support manual REBUILD command

#### FR-2.4: Embedding Storage
- WHEN document is chunked and indexed THEN system SHALL:
  1. Generate embedding via configured provider (Ollama, OpenAI, Copilot)
  2. Compute content hash for deduplication
  3. Upsert vector record in SurrealDB
  4. Link to Meilisearch document via document_id
- WHEN embedding generation fails THEN system SHALL index document without vector (keyword-only search)

#### FR-2.5: Vector Search Operations
- WHEN user performs semantic search THEN system SHALL:
  1. Generate query embedding via same provider as documents
  2. Execute KNN query with configurable K and effort
  3. Return document_ids with distance scores
- WHEN vector search returns results THEN system SHALL resolve full documents from Meilisearch

---

### FR-3: Hybrid Search Fusion

#### FR-3.1: Parallel Search Execution
- WHEN user performs hybrid search THEN system SHALL execute in parallel:
  1. Meilisearch keyword search (BM25)
  2. SurrealDB vector search (cosine similarity)
- WHEN both searches complete THEN system SHALL merge results

#### FR-3.2: Reciprocal Rank Fusion
- WHEN merging search results THEN system SHALL apply RRF algorithm:
  - Score = sum(1 / (k + rank)) for each result across both lists
  - Default k = 60
  - Configurable via HybridConfig.rrf_k
- WHEN result appears in both lists THEN system SHALL combine scores

#### FR-3.3: Score Normalization
- IF normalize_scores is true THEN system SHALL normalize final scores to [0, 1]
- WHEN returning results THEN system SHALL include:
  - Combined score
  - Keyword score (if matched)
  - Semantic score (if matched)
  - Result source indicator (keyword, semantic, both)

#### FR-3.4: Weight Configuration
- WHEN configuring hybrid search THEN system SHALL support:
  - semantic_weight: 0.0-1.0 (default 0.5)
  - keyword_weight: 0.0-1.0 (default 0.5)
  - Weights need not sum to 1.0 (allows boosting both)

---

### FR-4: Migration and Data Persistence

#### FR-4.1: Data Directory Structure
- WHEN application initializes THEN system SHALL use directory structure:
  ```
  ~/.local/share/ttrpg-assistant/
  ├── meilisearch/        # meilisearch-lib data
  │   ├── indexes/
  │   ├── tasks/
  │   └── auth/
  ├── surrealdb/          # SurrealDB RocksDB data
  │   └── vectors.db/
  └── ttrpg_assistant.db  # SQLite (unchanged)
  ```

#### FR-4.2: Migration from HTTP Meilisearch
- WHEN migrating from existing installation THEN system SHALL:
  1. Detect existing meilisearch/ data directory
  2. Verify data compatibility with meilisearch-lib
  3. If incompatible, prompt user for re-indexing
- WHEN migration fails THEN system SHALL preserve old data and allow manual recovery

#### FR-4.3: Vector Migration from Meilisearch
- WHEN migrating vectors from Meilisearch vectorStore THEN system SHALL:
  1. Export embeddings from existing indexes
  2. Create SurrealDB schema and indexes
  3. Bulk import vectors with document references
  4. Verify vector count matches
- IF migration is interrupted THEN system SHALL support resumption

---

### FR-5: Embedding Provider Integration

#### FR-5.1: Provider Support
- WHEN generating embeddings THEN system SHALL support:
  - Ollama (local, default): nomic-embed-text, mxbai-embed-large
  - OpenAI: text-embedding-3-small, text-embedding-3-large
  - Copilot OAuth: text-embedding-3-small via GitHub API
- WHEN provider is unavailable THEN system SHALL fallback to next configured provider

#### FR-5.2: Dimension Handling
- WHEN storing vectors THEN system SHALL record embedding dimension in metadata
- WHEN creating HNSW index THEN system SHALL match dimension to embedder
- IF dimension mismatch is detected THEN system SHALL reject operation with clear error

#### FR-5.3: Batch Processing
- WHEN generating embeddings for multiple chunks THEN system SHALL batch requests
- WHEN batch size exceeds provider limit THEN system SHALL split into sub-batches
- WHEN rate limited THEN system SHALL implement exponential backoff

---

### FR-6: Resource Management

#### FR-6.1: Startup Optimization
- WHEN application starts THEN system SHALL initialize databases asynchronously
- WHEN user interacts before initialization THEN system SHALL queue operations
- WHEN initialization completes THEN system SHALL process queued operations

#### FR-6.2: Memory Management
- WHEN configuring meilisearch-lib THEN system SHALL set:
  - max_index_size: 10 GiB (default, configurable)
  - max_task_db_size: 1 GiB (default, configurable)
- WHEN memory pressure is detected THEN system SHALL log warning

#### FR-6.3: Graceful Shutdown
- WHEN application closes THEN system SHALL:
  1. Complete pending index operations
  2. Flush meilisearch-lib data
  3. Close SurrealDB connection
- IF shutdown times out THEN system SHALL force close with data integrity warning

---

## Non-Functional Requirements

### NFR-1: Performance

#### NFR-1.1: Search Latency
- Keyword search SHALL complete in < 50ms for indexes < 100K documents
- Vector search SHALL complete in < 100ms for vector stores < 1M vectors
- Hybrid search SHALL complete in < 200ms for combined operations

#### NFR-1.2: Indexing Throughput
- Document indexing SHALL process > 100 documents/second for average TTRPG content
- Embedding generation SHALL parallelize across available cores
- Progress feedback SHALL update every 500ms during bulk operations

#### NFR-1.3: Startup Time
- Database initialization SHALL complete in < 2 seconds on SSD
- Search availability SHALL be signaled within 3 seconds of app launch
- Large index loading (>1GB) SHALL show progress indicator

### NFR-2: Reliability

#### NFR-2.1: Data Integrity
- All index operations SHALL be atomic (succeed completely or rollback)
- Task completion SHALL be verified before confirming to user
- Crash recovery SHALL preserve data written before failure

#### NFR-2.2: Error Recovery
- IF meilisearch-lib fails THEN system SHALL:
  1. Log detailed error with context
  2. Attempt single retry with exponential backoff
  3. If retry fails, degrade to keyword-only search
- IF SurrealDB fails THEN system SHALL:
  1. Log detailed error
  2. Degrade to keyword-only search
  3. Queue vector operations for retry

### NFR-3: Compatibility

#### NFR-3.1: Platform Support
- Integration SHALL work on Linux (x86_64, aarch64)
- Integration SHALL work on Windows (x86_64)
- Integration SHALL work on macOS (x86_64, aarch64)

#### NFR-3.2: Dependency Versions
- meilisearch-lib: compatible with Meilisearch v1.13+ data format
- SurrealDB: v2.5.0+ with RocksDB storage
- Rust: 2021 edition, stable toolchain

### NFR-4: Maintainability

#### NFR-4.1: Abstraction Layer
- Search operations SHALL use trait-based abstraction
- Vector operations SHALL use trait-based abstraction
- Implementations SHALL be swappable without changing callers

#### NFR-4.2: Testing
- Unit tests SHALL cover all search and vector operations
- Integration tests SHALL verify end-to-end hybrid search
- Benchmark tests SHALL track performance regressions

---

## Constraints

### C-1: No External Processes
- System SHALL NOT spawn or manage any external processes for search
- All search and vector operations SHALL be in-process library calls

### C-2: Backward Compatibility
- Existing SQLite database schema SHALL remain unchanged
- Existing document library metadata SHALL be preserved
- Chat history and campaign data SHALL be unaffected

### C-3: Feature Parity
- All current search features SHALL continue working:
  - TTRPG synonym expansion
  - Spell correction
  - Query suggestions
  - Search analytics

### C-4: Single Binary Distribution
- Application SHALL remain a single binary (plus assets)
- No runtime downloads or plugin installations required
- SurrealDB and meilisearch-lib SHALL be statically linked

---

## Assumptions

### A-1: meilisearch-lib Stability
- meilisearch-lib is assumed stable for production use
- API may evolve, but core functionality is reliable

### A-2: SurrealDB Embedded Viability
- SurrealDB embedded mode with RocksDB is production-ready
- HNSW index performance meets requirements

### A-3: Existing Data Volume
- Average user library: < 100 documents, < 500MB indexed
- Power user library: < 1000 documents, < 5GB indexed
- Vector store: < 1M embeddings per installation

### A-4: Embedding Provider Availability
- At least one embedding provider (Ollama) is available locally
- Network providers (OpenAI) require user configuration

---

## Risks

### R-1: meilisearch-lib Data Format Changes
**Risk**: Future meilisearch-lib versions may change internal data format
**Mitigation**: Pin to specific version, implement migration tooling
**Impact**: High - would require data re-indexing

### R-2: SurrealDB Memory Usage
**Risk**: HNSW index loads into memory, may consume significant RAM
**Mitigation**: Monitor memory, implement index size limits, document requirements
**Impact**: Medium - affects system with limited RAM

### R-3: Embedding Dimension Mismatch
**Risk**: User changes embedder, new vectors have different dimensions
**Mitigation**: Track embedder per-index, warn on mismatch, support re-embedding
**Impact**: Medium - requires manual intervention

### R-4: Build Complexity
**Risk**: Linking meilisearch-lib and SurrealDB increases compile time and binary size
**Mitigation**: Use feature flags, optimize release builds
**Impact**: Low - developer experience only

---

## Glossary

| Term | Definition |
|------|------------|
| **HNSW** | Hierarchical Navigable Small World - graph-based approximate nearest neighbor algorithm |
| **RRF** | Reciprocal Rank Fusion - algorithm to combine ranked lists |
| **BM25** | Best Matching 25 - probabilistic ranking function for keyword search |
| **Embedding** | Dense vector representation of text for semantic similarity |
| **Cosine Similarity** | Angle-based similarity metric for vectors |
| **KNN** | K-Nearest Neighbors - finding K most similar vectors |
| **meilisearch-lib** | Embedded Meilisearch library without HTTP server |
| **SurrealDB** | Multi-model database with vector, document, and graph capabilities |
| **Task** | Asynchronous operation in Meilisearch that can be polled for status |
