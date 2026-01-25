# Search and Library Commands Analysis

## Executive Summary

The search/library domain contains ~40 commands spanning basic search, hybrid search, document ingestion, library management, TTRPG document queries, search analytics, and extraction settings.

---

## 1. Command Inventory

### 1.1 Search Commands (6 commands)

| Command | Purpose |
|---------|---------|
| `search` | Basic Meilisearch with filters |
| `hybrid_search` | BM25 + vector semantic search with RRF fusion |
| `get_search_suggestions` | Autocomplete suggestions |
| `get_search_hints` | Query enhancement hints |
| `expand_query` | Query expansion with synonyms |
| `correct_query` | Spell correction |

### 1.2 Document Ingestion (3 commands)

| Command | Purpose |
|---------|---------|
| `ingest_document` | Single-phase ingestion |
| `ingest_document_two_phase` | Two-phase with per-document indexes |
| `ingest_pdf` | Direct PDF ingestion |

### 1.3 Library Management (5 commands)

| Command | Purpose |
|---------|---------|
| `list_library_documents` | List all documents |
| `delete_library_document` | Remove document |
| `update_library_document` | Update metadata |
| `rebuild_library_metadata` | Rebuild from indices |
| `clear_and_reingest_document` | Clear and re-process |

### 1.4 TTRPG Document Commands (12 commands)

| Command | Purpose |
|---------|---------|
| `get_ttrpg_document` | Get document by ID |
| `get_ttrpg_document_attributes` | Get document attributes |
| `get_ttrpg_document_stats` | Get document statistics |
| `delete_ttrpg_document` | Delete document |
| `search_ttrpg_documents_by_name` | Search by name |
| `find_ttrpg_documents_by_attribute` | Find by attribute |
| `list_ttrpg_documents_by_type` | List by type |
| `list_ttrpg_documents_by_system` | List by system |
| `list_ttrpg_documents_by_source` | List by source |
| `list_ttrpg_documents_by_cr` | List by CR |
| `count_ttrpg_documents_by_type` | Count by type |
| `get_ttrpg_ingestion_job` | Get ingestion job status |

### 1.5 Search Analytics (8 commands)

| Command | Purpose |
|---------|---------|
| `get_search_analytics_db` | Summary stats |
| `get_popular_queries_db` | Top queries |
| `get_cache_stats_db` | Cache performance |
| `get_trending_queries_db` | Trending patterns |
| `get_zero_result_queries_db` | Failed queries |
| `get_click_distribution_db` | Result click patterns |
| `record_search_event` | Log search |
| `record_search_selection_db` | Log result clicks |

### 1.6 Meilisearch Config (5 commands)

| Command | Purpose |
|---------|---------|
| `check_meilisearch_health` | Health check with stats |
| `reindex_library` | Reindex documents |
| `configure_meilisearch_embedder` | Setup embeddings |
| `setup_ollama_embeddings` | Configure Ollama |
| `configure_meilisearch_chat` | Chat provider config |

### 1.7 Extraction Settings (4 commands)

| Command | Purpose |
|---------|---------|
| `get_extraction_settings` | Read current settings |
| `save_extraction_settings` | Persist settings |
| `get_supported_formats` | List file types |
| `check_ocr_availability` | Check Tesseract |

---

## 2. AppState Dependencies

```rust
pub search_client: Arc<SearchClient>,
pub ingestion_pipeline: Arc<MeilisearchPipeline>,
pub sidecar_manager: Arc<SidecarManager>,
pub extraction_settings: AsyncRwLock<ExtractionSettings>,
pub database: Database,
```

Additional state types:
- `SearchAnalyticsState` - In-memory analytics
- `DbSearchAnalytics` - Database-backed persistence

---

## 3. Proposed Module Structure

```
commands/search/
├── mod.rs              # Re-exports
├── types.rs            # Shared types
├── basic.rs            # search, suggestions, hints (~150 lines)
├── hybrid.rs           # hybrid_search implementation (~100 lines)
├── analytics.rs        # Analytics recording/retrieval (~200 lines)
├── ingestion.rs        # Document ingestion (~200 lines)
├── library.rs          # Library management (~150 lines)
├── ttrpg.rs            # TTRPG document queries (~300 lines)
├── meilisearch.rs      # Meilisearch config (~150 lines)
└── extraction.rs       # Extraction settings (~100 lines)
```

**Total**: ~1,350 lines across 10 files

---

## 4. Settings Tab Alignment

| Settings Tab | Files |
|--------------|-------|
| Data & Library | `library.rs`, `extraction.rs` |
| Search/Analytics | `basic.rs`, `hybrid.rs`, `analytics.rs` |
| Meilisearch Config | `meilisearch.rs` |

---

## 5. Migration Priority

1. `types.rs` - Shared types
2. `basic.rs` - Core search functionality
3. `hybrid.rs` - Advanced search
4. `meilisearch.rs` - Configuration
5. `ingestion.rs` - Document processing
6. `library.rs` - Library management
7. `ttrpg.rs` - TTRPG queries
8. `analytics.rs` - Analytics
9. `extraction.rs` - Settings
