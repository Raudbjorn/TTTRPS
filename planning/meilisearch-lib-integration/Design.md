# Design: Embedded Meilisearch + SurrealDB Vector Store Integration

## Overview

This document describes the technical architecture for integrating `meilisearch-lib` as an embedded search engine and SurrealDB as a dedicated vector store, replacing the current HTTP-based Meilisearch SDK and in-Meilisearch vectorStore.

---

## 1. Architecture Overview

### 1.1 Current Architecture (To Be Replaced)

```
┌─────────────────────────────────────────────────────────────┐
│                    TTRPG Assistant                          │
├─────────────────────────────────────────────────────────────┤
│  SearchClient (meilisearch-sdk)                             │
│       │                                                     │
│       │ HTTP                                                │
│       ▼                                                     │
│  ┌─────────────────┐                                        │
│  │ SidecarManager  │──spawns──▶ [meilisearch process :7700] │
│  └─────────────────┘                                        │
│                                                             │
│  HybridSearchEngine                                         │
│       │                                                     │
│       ├── Keyword search ──▶ Meilisearch HTTP               │
│       └── Vector search ──▶ Meilisearch vectorStore (exp.)  │
└─────────────────────────────────────────────────────────────┘
```

**Problems:**
- External process management (download, spawn, health-check, restart)
- Platform-specific sidecar binaries
- Network latency for local operations
- Experimental vectorStore feature with limited configuration

### 1.2 Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TTRPG Assistant                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │ EmbeddedSearch  │     │  VectorStore    │               │
│  │ (meilisearch-   │     │  (SurrealDB     │               │
│  │  lib)           │     │   embedded)     │               │
│  └────────┬────────┘     └────────┬────────┘               │
│           │                       │                         │
│           │  in-process           │  in-process             │
│           ▼                       ▼                         │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │ LMDB (indexes)  │     │ RocksDB (vecs)  │               │
│  └─────────────────┘     └─────────────────┘               │
│                                                             │
│  HybridSearchEngine                                         │
│       │                                                     │
│       ├── Keyword search ──▶ EmbeddedSearch (direct)        │
│       └── Vector search ──▶ VectorStore (direct)            │
│       │                                                     │
│       └── RRF Fusion ──▶ Combined results                   │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- No external processes
- Zero network latency
- Full control over vector indexing
- Cleaner separation of concerns

---

## 2. Component Design

### 2.1 EmbeddedSearch Module

**Location**: `src-tauri/src/core/search/embedded.rs`

**Responsibility**: Wrapper around `meilisearch-lib` providing type-safe search operations.

```rust
use meilisearch_lib::{MeilisearchLib, Config, SearchQuery, SearchResult};
use std::sync::Arc;
use std::path::PathBuf;

/// Embedded Meilisearch search engine
pub struct EmbeddedSearch {
    inner: Arc<MeilisearchLib>,
    config: EmbeddedSearchConfig,
}

#[derive(Debug, Clone)]
pub struct EmbeddedSearchConfig {
    pub db_path: PathBuf,
    pub max_index_size_bytes: usize,
    pub max_task_db_size_bytes: usize,
}

impl Default for EmbeddedSearchConfig {
    fn default() -> Self {
        Self {
            db_path: dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("ttrpg-assistant")
                .join("meilisearch"),
            max_index_size_bytes: 10 * 1024 * 1024 * 1024, // 10 GiB
            max_task_db_size_bytes: 1 * 1024 * 1024 * 1024, // 1 GiB
        }
    }
}

impl EmbeddedSearch {
    /// Initialize embedded Meilisearch
    pub fn new(config: EmbeddedSearchConfig) -> Result<Self, EmbeddedSearchError> {
        let lib_config = Config::builder()
            .db_path(&config.db_path)
            .max_index_size(config.max_index_size_bytes)
            .max_task_db_size(config.max_task_db_size_bytes)
            .build()
            .map_err(EmbeddedSearchError::Config)?;

        let inner = MeilisearchLib::new(lib_config)
            .map_err(EmbeddedSearchError::Init)?;

        Ok(Self {
            inner: Arc::new(inner),
            config,
        })
    }

    /// Get health status
    pub fn health(&self) -> SearchHealth {
        let health = self.inner.health();
        SearchHealth {
            status: match health.status.as_str() {
                "available" => HealthStatus::Available,
                _ => HealthStatus::Degraded,
            },
        }
    }

    /// Create index with optional primary key
    pub async fn create_index(
        &self,
        uid: &str,
        primary_key: Option<&str>,
    ) -> Result<(), EmbeddedSearchError> {
        let task = self.inner
            .create_index(uid, primary_key.map(String::from))
            .map_err(EmbeddedSearchError::Index)?;

        self.wait_for_task(task.uid).await
    }

    /// Add documents to index
    pub async fn add_documents(
        &self,
        index_uid: &str,
        documents: Vec<serde_json::Value>,
        primary_key: Option<&str>,
    ) -> Result<u32, EmbeddedSearchError> {
        let task = self.inner
            .add_documents(index_uid, documents, primary_key.map(String::from))
            .map_err(EmbeddedSearchError::Document)?;

        self.wait_for_task(task.uid).await?;
        Ok(task.uid)
    }

    /// Search with query builder
    pub fn search(
        &self,
        index_uid: &str,
        query: impl Into<SearchQueryBuilder>,
    ) -> Result<SearchResults, EmbeddedSearchError> {
        let query = query.into().build();
        let result = self.inner
            .search(index_uid, query)
            .map_err(EmbeddedSearchError::Search)?;

        Ok(SearchResults::from(result))
    }

    /// Wait for task completion with timeout
    async fn wait_for_task(&self, task_id: u32) -> Result<(), EmbeddedSearchError> {
        let timeout = std::time::Duration::from_secs(30);
        let task = self.inner
            .wait_for_task_async(task_id, Some(timeout))
            .await
            .map_err(EmbeddedSearchError::Task)?;

        match task.status {
            meilisearch_lib::Status::Succeeded => Ok(()),
            meilisearch_lib::Status::Failed => {
                Err(EmbeddedSearchError::TaskFailed(
                    task.error.map(|e| e.message).unwrap_or_default()
                ))
            }
            _ => Err(EmbeddedSearchError::TaskTimeout(task_id)),
        }
    }

    /// Shutdown gracefully
    pub fn shutdown(self) -> Result<(), EmbeddedSearchError> {
        Arc::try_unwrap(self.inner)
            .map_err(|_| EmbeddedSearchError::InUse)?
            .shutdown()
            .map_err(EmbeddedSearchError::Shutdown)
    }
}
```

### 2.2 VectorStore Module

**Location**: `src-tauri/src/core/search/vector_store.rs`

**Responsibility**: SurrealDB-based vector storage and similarity search.

```rust
use surrealdb::engine::local::{Db, RocksDb};
use surrealdb::Surreal;
use std::sync::LazyLock;
use std::path::PathBuf;

/// Static database instance for application lifetime
static VECTOR_DB: LazyLock<Surreal<Db>> = LazyLock::new(Surreal::init);

/// Vector store configuration
#[derive(Debug, Clone)]
pub struct VectorStoreConfig {
    pub db_path: PathBuf,
    pub namespace: String,
    pub database: String,
    pub default_dimension: u32,
    pub hnsw_efc: u32,
    pub hnsw_m: u32,
}

impl Default for VectorStoreConfig {
    fn default() -> Self {
        Self {
            db_path: dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("ttrpg-assistant")
                .join("surrealdb"),
            namespace: "ttrpg".into(),
            database: "vectors".into(),
            default_dimension: 1536, // text-embedding-3-small
            hnsw_efc: 200,
            hnsw_m: 16,
        }
    }
}

/// Vector record stored in SurrealDB
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorRecord {
    pub id: String,
    pub index_uid: String,
    pub document_id: String,
    pub content_hash: String,
    pub embedding: Vec<f32>,
    pub dimension: u32,
    pub embedder: String,
    pub metadata: serde_json::Value,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

/// Vector search result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorSearchResult {
    pub document_id: String,
    pub index_uid: String,
    pub distance: f64,
    pub score: f64,
}

/// Vector store operations
pub struct VectorStore {
    config: VectorStoreConfig,
}

impl VectorStore {
    /// Initialize vector store
    pub async fn new(config: VectorStoreConfig) -> Result<Self, VectorStoreError> {
        // Ensure directory exists
        std::fs::create_dir_all(&config.db_path)
            .map_err(VectorStoreError::Io)?;

        // Connect to embedded database
        VECTOR_DB.connect::<RocksDb>(&config.db_path)
            .await
            .map_err(VectorStoreError::Connection)?;

        // Set namespace and database
        VECTOR_DB.use_ns(&config.namespace)
            .use_db(&config.database)
            .await
            .map_err(VectorStoreError::Connection)?;

        let store = Self { config };
        store.initialize_schema().await?;

        Ok(store)
    }

    /// Initialize database schema
    async fn initialize_schema(&self) -> Result<(), VectorStoreError> {
        // Define table with schema
        VECTOR_DB.query(r#"
            DEFINE TABLE IF NOT EXISTS vectors SCHEMAFULL;

            DEFINE FIELD id ON vectors TYPE string;
            DEFINE FIELD index_uid ON vectors TYPE string;
            DEFINE FIELD document_id ON vectors TYPE string;
            DEFINE FIELD content_hash ON vectors TYPE string;
            DEFINE FIELD embedding ON vectors TYPE array;
            DEFINE FIELD dimension ON vectors TYPE int;
            DEFINE FIELD embedder ON vectors TYPE string;
            DEFINE FIELD metadata ON vectors TYPE object;
            DEFINE FIELD created_at ON vectors TYPE datetime DEFAULT time::now();
            DEFINE FIELD updated_at ON vectors TYPE datetime DEFAULT time::now();

            DEFINE INDEX idx_document ON vectors FIELDS index_uid, document_id UNIQUE;
            DEFINE INDEX idx_hash ON vectors FIELDS content_hash;
        "#).await.map_err(VectorStoreError::Query)?;

        Ok(())
    }

    /// Create HNSW index for specific dimension
    pub async fn ensure_vector_index(&self, dimension: u32) -> Result<(), VectorStoreError> {
        let query = format!(
            r#"
            DEFINE INDEX IF NOT EXISTS embedding_hnsw_{dim} ON vectors
            FIELDS embedding
            HNSW DIMENSION {dim}
            DIST COSINE
            EFC {efc}
            M {m}
            "#,
            dim = dimension,
            efc = self.config.hnsw_efc,
            m = self.config.hnsw_m,
        );

        VECTOR_DB.query(&query)
            .await
            .map_err(VectorStoreError::Query)?;

        Ok(())
    }

    /// Upsert vector record
    pub async fn upsert(&self, record: VectorRecord) -> Result<(), VectorStoreError> {
        // Ensure index exists for this dimension
        self.ensure_vector_index(record.dimension).await?;

        VECTOR_DB.query(r#"
            UPSERT vectors CONTENT $record
            WHERE index_uid = $index_uid AND document_id = $document_id
        "#)
        .bind(("record", &record))
        .bind(("index_uid", &record.index_uid))
        .bind(("document_id", &record.document_id))
        .await
        .map_err(VectorStoreError::Query)?;

        Ok(())
    }

    /// Batch upsert vectors
    pub async fn upsert_batch(&self, records: Vec<VectorRecord>) -> Result<usize, VectorStoreError> {
        if records.is_empty() {
            return Ok(0);
        }

        // Ensure index exists (all records should have same dimension)
        if let Some(first) = records.first() {
            self.ensure_vector_index(first.dimension).await?;
        }

        let count = records.len();

        // Use transaction for atomicity
        VECTOR_DB.query("BEGIN TRANSACTION").await.map_err(VectorStoreError::Query)?;

        for record in records {
            self.upsert(record).await?;
        }

        VECTOR_DB.query("COMMIT TRANSACTION").await.map_err(VectorStoreError::Query)?;

        Ok(count)
    }

    /// K-nearest neighbor search
    pub async fn knn_search(
        &self,
        query_vector: &[f32],
        k: usize,
        index_filter: Option<&str>,
    ) -> Result<Vec<VectorSearchResult>, VectorStoreError> {
        let dimension = query_vector.len() as u32;

        // Build query with optional filter
        let filter_clause = index_filter
            .map(|uid| format!("WHERE index_uid = '{}'", uid))
            .unwrap_or_default();

        let query = format!(
            r#"
            SELECT
                document_id,
                index_uid,
                vector::distance::knn() AS distance
            FROM vectors
            {filter}
            AND embedding <|{k}, 100|> $query_vec
            ORDER BY distance ASC
            LIMIT {k}
            "#,
            filter = filter_clause,
            k = k,
        );

        let mut results = VECTOR_DB.query(&query)
            .bind(("query_vec", query_vector.to_vec()))
            .await
            .map_err(VectorStoreError::Query)?;

        let records: Vec<VectorSearchResult> = results.take(0)
            .map_err(VectorStoreError::Query)?;

        // Convert distance to similarity score (cosine: 1 - distance)
        Ok(records.into_iter().map(|mut r| {
            r.score = 1.0 - r.distance;
            r
        }).collect())
    }

    /// Delete vectors by document
    pub async fn delete_by_document(
        &self,
        index_uid: &str,
        document_id: &str,
    ) -> Result<u64, VectorStoreError> {
        let result = VECTOR_DB.query(r#"
            DELETE FROM vectors
            WHERE index_uid = $index_uid AND document_id = $document_id
            RETURN count()
        "#)
        .bind(("index_uid", index_uid))
        .bind(("document_id", document_id))
        .await
        .map_err(VectorStoreError::Query)?;

        // Extract count from result
        Ok(1) // TODO: Extract actual count
    }

    /// Delete all vectors for an index
    pub async fn delete_by_index(&self, index_uid: &str) -> Result<u64, VectorStoreError> {
        let result = VECTOR_DB.query(r#"
            DELETE FROM vectors WHERE index_uid = $index_uid
        "#)
        .bind(("index_uid", index_uid))
        .await
        .map_err(VectorStoreError::Query)?;

        Ok(0) // TODO: Extract count
    }

    /// Get vector count for index
    pub async fn count(&self, index_uid: Option<&str>) -> Result<u64, VectorStoreError> {
        let query = match index_uid {
            Some(uid) => format!(
                "SELECT count() FROM vectors WHERE index_uid = '{}'", uid
            ),
            None => "SELECT count() FROM vectors".into(),
        };

        let mut result = VECTOR_DB.query(&query)
            .await
            .map_err(VectorStoreError::Query)?;

        // Extract count
        Ok(0) // TODO: Extract actual count
    }
}
```

### 2.3 Hybrid Search Engine (Updated)

**Location**: `src-tauri/src/core/search/hybrid.rs` (refactored)

**Responsibility**: Coordinate keyword and vector search, apply RRF fusion.

```rust
use super::embedded::EmbeddedSearch;
use super::vector_store::{VectorStore, VectorSearchResult};
use super::fusion::RrfFusion;
use super::query::QueryEnhancer;

/// Hybrid search engine combining keyword and semantic search
pub struct HybridSearchEngine {
    keyword_search: Arc<EmbeddedSearch>,
    vector_store: Arc<VectorStore>,
    embedding_provider: Arc<dyn EmbeddingProvider>,
    query_enhancer: QueryEnhancer,
    config: HybridConfig,
}

#[derive(Debug, Clone)]
pub struct HybridConfig {
    pub semantic_weight: f32,
    pub keyword_weight: f32,
    pub rrf_k: u32,
    pub max_results_per_type: usize,
    pub normalize_scores: bool,
    pub enable_query_expansion: bool,
    pub enable_spell_correction: bool,
}

impl Default for HybridConfig {
    fn default() -> Self {
        Self {
            semantic_weight: 0.5,
            keyword_weight: 0.5,
            rrf_k: 60,
            max_results_per_type: 50,
            normalize_scores: true,
            enable_query_expansion: true,
            enable_spell_correction: true,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct HybridSearchResult {
    pub document: serde_json::Value,
    pub combined_score: f64,
    pub keyword_score: Option<f64>,
    pub semantic_score: Option<f64>,
    pub source: ResultSource,
    pub highlights: Option<Vec<String>>,
}

#[derive(Debug, Clone, Copy, Serialize, PartialEq)]
pub enum ResultSource {
    Keyword,
    Semantic,
    Both,
}

impl HybridSearchEngine {
    pub fn new(
        keyword_search: Arc<EmbeddedSearch>,
        vector_store: Arc<VectorStore>,
        embedding_provider: Arc<dyn EmbeddingProvider>,
        config: HybridConfig,
    ) -> Self {
        Self {
            keyword_search,
            vector_store,
            embedding_provider,
            query_enhancer: QueryEnhancer::new(),
            config,
        }
    }

    /// Execute hybrid search
    pub async fn search(
        &self,
        query: &str,
        index_uid: &str,
        filters: Option<&str>,
        limit: usize,
    ) -> Result<Vec<HybridSearchResult>, HybridSearchError> {
        // Enhance query
        let enhanced_query = if self.config.enable_query_expansion {
            self.query_enhancer.expand(query)
        } else {
            query.to_string()
        };

        // Execute keyword and vector search in parallel
        let keyword_future = self.keyword_search(index_uid, &enhanced_query, filters);
        let vector_future = self.vector_search(index_uid, query);

        let (keyword_results, vector_results) = tokio::join!(
            keyword_future,
            vector_future
        );

        let keyword_results = keyword_results?;
        let vector_results = vector_results?;

        // Fuse results with RRF
        let fused = RrfFusion::fuse(
            &keyword_results,
            &vector_results,
            self.config.rrf_k,
            self.config.keyword_weight,
            self.config.semantic_weight,
        );

        // Resolve full documents and build results
        let mut results = Vec::with_capacity(fused.len().min(limit));

        for (doc_id, fusion_result) in fused.into_iter().take(limit) {
            let document = self.keyword_search
                .get_document(index_uid, &doc_id)
                .ok();

            if let Some(doc) = document {
                results.push(HybridSearchResult {
                    document: doc,
                    combined_score: fusion_result.combined_score,
                    keyword_score: fusion_result.keyword_score,
                    semantic_score: fusion_result.semantic_score,
                    source: fusion_result.source,
                    highlights: None, // TODO: Extract from keyword results
                });
            }
        }

        // Normalize if configured
        if self.config.normalize_scores && !results.is_empty() {
            let max_score = results.iter()
                .map(|r| r.combined_score)
                .fold(0.0, f64::max);

            if max_score > 0.0 {
                for result in &mut results {
                    result.combined_score /= max_score;
                }
            }
        }

        Ok(results)
    }

    /// Keyword-only search
    async fn keyword_search(
        &self,
        index_uid: &str,
        query: &str,
        filters: Option<&str>,
    ) -> Result<Vec<(String, f64)>, HybridSearchError> {
        let mut search_query = SearchQueryBuilder::new(query)
            .with_limit(self.config.max_results_per_type)
            .with_show_ranking_score(true);

        if let Some(f) = filters {
            search_query = search_query.with_filter(f);
        }

        let results = self.keyword_search
            .search(index_uid, search_query)
            .map_err(HybridSearchError::Keyword)?;

        Ok(results.hits.into_iter().map(|hit| {
            let doc_id = hit.document["id"]
                .as_str()
                .unwrap_or_default()
                .to_string();
            let score = hit.ranking_score.unwrap_or(0.0);
            (doc_id, score)
        }).collect())
    }

    /// Vector-only search
    async fn vector_search(
        &self,
        index_uid: &str,
        query: &str,
    ) -> Result<Vec<(String, f64)>, HybridSearchError> {
        // Generate query embedding
        let embedding = self.embedding_provider
            .embed(query)
            .await
            .map_err(HybridSearchError::Embedding)?;

        // Execute KNN search
        let results = self.vector_store
            .knn_search(&embedding, self.config.max_results_per_type, Some(index_uid))
            .await
            .map_err(HybridSearchError::Vector)?;

        Ok(results.into_iter().map(|r| {
            (r.document_id, r.score)
        }).collect())
    }
}
```

### 2.4 RRF Fusion Module

**Location**: `src-tauri/src/core/search/fusion.rs` (simplified)

```rust
use std::collections::HashMap;

/// Fusion result for a single document
#[derive(Debug, Clone)]
pub struct FusionResult {
    pub combined_score: f64,
    pub keyword_score: Option<f64>,
    pub semantic_score: Option<f64>,
    pub source: ResultSource,
}

/// Reciprocal Rank Fusion algorithm
pub struct RrfFusion;

impl RrfFusion {
    /// Fuse keyword and semantic results using RRF
    pub fn fuse(
        keyword_results: &[(String, f64)],
        semantic_results: &[(String, f64)],
        k: u32,
        keyword_weight: f32,
        semantic_weight: f32,
    ) -> Vec<(String, FusionResult)> {
        let mut scores: HashMap<String, FusionResult> = HashMap::new();
        let k = k as f64;

        // Process keyword results
        for (rank, (doc_id, score)) in keyword_results.iter().enumerate() {
            let rrf_score = keyword_weight as f64 * (1.0 / (k + rank as f64 + 1.0));

            scores.entry(doc_id.clone()).or_insert_with(|| FusionResult {
                combined_score: 0.0,
                keyword_score: None,
                semantic_score: None,
                source: ResultSource::Keyword,
            }).keyword_score = Some(*score);

            scores.get_mut(doc_id).unwrap().combined_score += rrf_score;
        }

        // Process semantic results
        for (rank, (doc_id, score)) in semantic_results.iter().enumerate() {
            let rrf_score = semantic_weight as f64 * (1.0 / (k + rank as f64 + 1.0));

            let entry = scores.entry(doc_id.clone()).or_insert_with(|| FusionResult {
                combined_score: 0.0,
                keyword_score: None,
                semantic_score: None,
                source: ResultSource::Semantic,
            });

            entry.semantic_score = Some(*score);
            entry.combined_score += rrf_score;

            // Update source if appeared in both
            if entry.keyword_score.is_some() {
                entry.source = ResultSource::Both;
            }
        }

        // Sort by combined score descending
        let mut results: Vec<_> = scores.into_iter().collect();
        results.sort_by(|a, b| b.1.combined_score.partial_cmp(&a.1.combined_score).unwrap());

        results
    }
}
```

### 2.5 Embedding Provider Trait

**Location**: `src-tauri/src/core/search/embeddings.rs` (refactored)

```rust
use async_trait::async_trait;

/// Embedding provider abstraction
#[async_trait]
pub trait EmbeddingProvider: Send + Sync {
    /// Generate embedding for single text
    async fn embed(&self, text: &str) -> Result<Vec<f32>, EmbeddingError>;

    /// Generate embeddings for batch of texts
    async fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>, EmbeddingError>;

    /// Get embedding dimension
    fn dimension(&self) -> u32;

    /// Get provider name (for tracking)
    fn name(&self) -> &str;
}

/// Ollama embedding provider (default)
pub struct OllamaEmbedder {
    client: reqwest::Client,
    endpoint: String,
    model: String,
    dimension: u32,
}

impl OllamaEmbedder {
    pub fn new(model: &str) -> Self {
        let dimension = match model {
            "nomic-embed-text" => 768,
            "mxbai-embed-large" => 1024,
            _ => 768,
        };

        Self {
            client: reqwest::Client::new(),
            endpoint: "http://localhost:11434".into(),
            model: model.into(),
            dimension,
        }
    }
}

#[async_trait]
impl EmbeddingProvider for OllamaEmbedder {
    async fn embed(&self, text: &str) -> Result<Vec<f32>, EmbeddingError> {
        let response = self.client
            .post(format!("{}/api/embed", self.endpoint))
            .json(&serde_json::json!({
                "model": self.model,
                "input": text
            }))
            .send()
            .await
            .map_err(EmbeddingError::Request)?;

        let data: serde_json::Value = response.json().await
            .map_err(EmbeddingError::Parse)?;

        let embedding = data["embeddings"][0]
            .as_array()
            .ok_or(EmbeddingError::InvalidResponse)?
            .iter()
            .filter_map(|v| v.as_f64().map(|f| f as f32))
            .collect();

        Ok(embedding)
    }

    async fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>, EmbeddingError> {
        let response = self.client
            .post(format!("{}/api/embed", self.endpoint))
            .json(&serde_json::json!({
                "model": self.model,
                "input": texts
            }))
            .send()
            .await
            .map_err(EmbeddingError::Request)?;

        let data: serde_json::Value = response.json().await
            .map_err(EmbeddingError::Parse)?;

        let embeddings = data["embeddings"]
            .as_array()
            .ok_or(EmbeddingError::InvalidResponse)?
            .iter()
            .map(|emb| {
                emb.as_array()
                    .map(|arr| arr.iter()
                        .filter_map(|v| v.as_f64().map(|f| f as f32))
                        .collect())
                    .unwrap_or_default()
            })
            .collect();

        Ok(embeddings)
    }

    fn dimension(&self) -> u32 {
        self.dimension
    }

    fn name(&self) -> &str {
        "ollama"
    }
}
```

---

## 3. Data Flow

### 3.1 Document Ingestion Flow

```
User drops PDF
       │
       ▼
┌──────────────────┐
│ MeilisearchPipeline │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Phase 1: Extract │──▶ kreuzberg extracts pages
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Store raw pages  │──▶ EmbeddedSearch.add_documents("<slug>-raw")
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Phase 2: Chunk   │──▶ TTRPGChunker.chunk()
└────────┬─────────┘
         │
         ├─────────────────────┬────────────────────┐
         ▼                     ▼                    ▼
┌────────────────┐    ┌────────────────┐   ┌───────────────┐
│ Index chunks   │    │ Generate       │   │ Store vectors │
│ in Meilisearch │    │ embeddings     │   │ in SurrealDB  │
└────────────────┘    └────────────────┘   └───────────────┘
EmbeddedSearch        EmbeddingProvider    VectorStore
.add_documents()      .embed_batch()       .upsert_batch()
```

### 3.2 Hybrid Search Flow

```
User query: "how does flanking work"
       │
       ▼
┌──────────────────┐
│ HybridSearchEngine │
└────────┬─────────┘
         │
         ├── Query enhancement (synonyms, corrections)
         │
         ▼
┌───────────────────────────────────────┐
│         Parallel Execution            │
├───────────────────┬───────────────────┤
│                   │                   │
▼                   ▼                   │
┌─────────────┐   ┌─────────────┐       │
│ Keyword     │   │ Embed query │       │
│ Search      │   │ via Ollama  │       │
└──────┬──────┘   └──────┬──────┘       │
       │                 │              │
       │                 ▼              │
       │          ┌─────────────┐       │
       │          │ Vector KNN  │       │
       │          │ SurrealDB   │       │
       │          └──────┬──────┘       │
       │                 │              │
       ▼                 ▼              │
┌──────────────────────────────────────┐│
│        RRF Fusion                    ││
│                                      ││
│  keyword_results + semantic_results  ││
│  → combined ranked list              ││
└───────────────────┬──────────────────┘│
                    │                    │
                    ▼                    │
            ┌───────────────┐            │
            │ Resolve full  │            │
            │ documents     │            │
            └───────┬───────┘            │
                    │                    │
                    ▼                    │
            ┌───────────────┐            │
            │ Return results│            │
            └───────────────┘            │
```

---

## 4. State Management

### 4.1 AppState Changes

**Location**: `src-tauri/src/commands/state.rs`

```rust
// Current (to remove)
pub struct AppState {
    pub search_client: Arc<SearchClient>,          // HTTP client
    pub sidecar_manager: Arc<SidecarManager>,      // Process manager
    // ...
}

// New
pub struct AppState {
    pub embedded_search: Arc<EmbeddedSearch>,      // Embedded Meilisearch
    pub vector_store: Arc<VectorStore>,            // SurrealDB vectors
    pub hybrid_engine: Arc<HybridSearchEngine>,    // Combined search
    pub embedding_provider: Arc<dyn EmbeddingProvider>,
    // ... (rest unchanged)
}
```

### 4.2 Initialization Sequence

**Location**: `src-tauri/src/main.rs`

```rust
async fn initialize_search() -> Result<(
    Arc<EmbeddedSearch>,
    Arc<VectorStore>,
    Arc<HybridSearchEngine>,
), AppInitError> {
    // 1. Initialize embedded Meilisearch
    let search_config = EmbeddedSearchConfig::default();
    let embedded_search = Arc::new(
        EmbeddedSearch::new(search_config)
            .map_err(AppInitError::Search)?
    );

    // 2. Initialize SurrealDB vector store
    let vector_config = VectorStoreConfig::default();
    let vector_store = Arc::new(
        VectorStore::new(vector_config)
            .await
            .map_err(AppInitError::Vector)?
    );

    // 3. Initialize embedding provider
    let embedding_provider: Arc<dyn EmbeddingProvider> = Arc::new(
        OllamaEmbedder::new("nomic-embed-text")
    );

    // 4. Initialize hybrid search engine
    let hybrid_engine = Arc::new(HybridSearchEngine::new(
        Arc::clone(&embedded_search),
        Arc::clone(&vector_store),
        Arc::clone(&embedding_provider),
        HybridConfig::default(),
    ));

    // 5. Ensure core indexes exist
    for index in ["rules", "fiction", "chat", "documents", "library_metadata", "ttrpg"] {
        if !embedded_search.index_exists(index)? {
            embedded_search.create_index(index, Some("id")).await?;
        }
    }

    Ok((embedded_search, vector_store, hybrid_engine))
}
```

---

## 5. Migration Strategy

### 5.1 Data Directory Changes

| Old Location | New Location | Notes |
|--------------|--------------|-------|
| `~/.local/share/ttrpg-assistant/meilisearch/` | Same | meilisearch-lib compatible |
| N/A (in Meilisearch) | `~/.local/share/ttrpg-assistant/surrealdb/` | New vector storage |

### 5.2 Migration Steps

1. **Detect existing installation**
   - Check for `meilisearch/` directory
   - If exists, attempt to load with meilisearch-lib

2. **Vector migration**
   - If vectors exist in Meilisearch indexes
   - Export via search with vector fields
   - Import to SurrealDB
   - Mark migration complete in metadata

3. **Fallback**
   - If migration fails, prompt user to re-ingest
   - Preserve original data for manual recovery

### 5.3 Version Tracking

```rust
const MIGRATION_VERSION: u32 = 1;

#[derive(Serialize, Deserialize)]
struct MigrationState {
    version: u32,
    meilisearch_migrated: bool,
    vector_migrated: bool,
    completed_at: Option<chrono::DateTime<chrono::Utc>>,
}
```

---

## 6. Error Handling

### 6.1 Error Types

```rust
#[derive(Debug, thiserror::Error)]
pub enum EmbeddedSearchError {
    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Initialization failed: {0}")]
    Init(meilisearch_lib::Error),

    #[error("Index operation failed: {0}")]
    Index(meilisearch_lib::Error),

    #[error("Document operation failed: {0}")]
    Document(meilisearch_lib::Error),

    #[error("Search failed: {0}")]
    Search(meilisearch_lib::Error),

    #[error("Task failed: {0}")]
    TaskFailed(String),

    #[error("Task timeout: {0}")]
    TaskTimeout(u32),

    #[error("Instance still in use")]
    InUse,

    #[error("Shutdown failed: {0}")]
    Shutdown(meilisearch_lib::Error),
}

#[derive(Debug, thiserror::Error)]
pub enum VectorStoreError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Connection failed: {0}")]
    Connection(surrealdb::Error),

    #[error("Query failed: {0}")]
    Query(surrealdb::Error),

    #[error("Invalid dimension: expected {expected}, got {actual}")]
    DimensionMismatch { expected: u32, actual: u32 },
}

#[derive(Debug, thiserror::Error)]
pub enum HybridSearchError {
    #[error("Keyword search failed: {0}")]
    Keyword(#[from] EmbeddedSearchError),

    #[error("Vector search failed: {0}")]
    Vector(#[from] VectorStoreError),

    #[error("Embedding failed: {0}")]
    Embedding(EmbeddingError),
}
```

### 6.2 Degradation Strategy

```rust
impl HybridSearchEngine {
    /// Search with graceful degradation
    pub async fn search_with_fallback(
        &self,
        query: &str,
        index_uid: &str,
        filters: Option<&str>,
        limit: usize,
    ) -> HybridSearchResult {
        match self.search(query, index_uid, filters, limit).await {
            Ok(results) => HybridSearchResult::Full(results),
            Err(HybridSearchError::Vector(_)) => {
                // Vector search failed, try keyword-only
                tracing::warn!("Vector search unavailable, falling back to keyword");
                match self.keyword_only_search(query, index_uid, filters, limit).await {
                    Ok(results) => HybridSearchResult::KeywordOnly(results),
                    Err(e) => HybridSearchResult::Failed(e.to_string()),
                }
            }
            Err(HybridSearchError::Embedding(_)) => {
                // Embedding failed, try keyword-only
                tracing::warn!("Embedding unavailable, falling back to keyword");
                match self.keyword_only_search(query, index_uid, filters, limit).await {
                    Ok(results) => HybridSearchResult::KeywordOnly(results),
                    Err(e) => HybridSearchResult::Failed(e.to_string()),
                }
            }
            Err(e) => HybridSearchResult::Failed(e.to_string()),
        }
    }
}
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Module | Test Focus |
|--------|------------|
| `embedded.rs` | Index CRUD, document operations, search queries |
| `vector_store.rs` | Schema creation, upsert, KNN search, deletion |
| `fusion.rs` | RRF algorithm correctness, edge cases |
| `embeddings.rs` | Provider abstraction, dimension tracking |
| `hybrid.rs` | Parallel execution, result merging, fallback |

### 7.2 Integration Tests

```rust
#[tokio::test]
async fn test_full_hybrid_search_flow() {
    // Setup
    let (search, vectors, hybrid) = setup_test_environment().await;

    // Ingest test document
    let doc = json!({
        "id": "test-1",
        "content": "Flanking gives a +2 bonus to attack rolls",
        "type": "rule"
    });
    search.add_documents("rules", vec![doc.clone()], Some("id")).await.unwrap();

    // Add vector
    let embedding = embed("Flanking gives a +2 bonus").await;
    vectors.upsert(VectorRecord {
        id: "test-1".into(),
        index_uid: "rules".into(),
        document_id: "test-1".into(),
        embedding,
        // ...
    }).await.unwrap();

    // Search
    let results = hybrid.search("how does flanking work", "rules", None, 10).await.unwrap();

    // Assert
    assert!(!results.is_empty());
    assert_eq!(results[0].document["id"], "test-1");
}
```

### 7.3 Benchmark Tests

```rust
#[bench]
fn bench_keyword_search_10k_docs(b: &mut Bencher) {
    let search = setup_search_with_10k_docs();
    b.iter(|| {
        search.search("rules", SearchQuery::new("combat"))
    });
}

#[bench]
fn bench_vector_search_100k_vectors(b: &mut Bencher) {
    let vectors = setup_vectors_with_100k();
    let query_vec = generate_random_vector(768);
    b.iter(|| {
        vectors.knn_search(&query_vec, 10, None)
    });
}
```

---

## 8. Decisions Log

### Decision 1: SurrealDB over Qdrant

**Context**: Need dedicated vector storage to replace experimental Meilisearch vectorStore

**Options Considered**:
1. **Qdrant** - Purpose-built vector DB, Rust-native
2. **SurrealDB** - Multi-model with vectors, embedded mode
3. **Keep Meilisearch vectorStore** - Existing, experimental

**Decision**: SurrealDB

**Rationale**:
- Embedded mode with RocksDB suits desktop app deployment
- Native Rust SDK with async support
- Multi-model allows future schema flexibility
- Simpler than managing two external databases
- Built-in RRF fusion (can use SurrealDB's or custom)

### Decision 2: Separate Search and Vector Components

**Context**: Could keep hybrid search in single system vs. separate

**Decision**: Separate EmbeddedSearch (Meilisearch) + VectorStore (SurrealDB)

**Rationale**:
- Cleaner separation of concerns
- Each system optimized for its purpose
- Easier to test and debug
- Can upgrade components independently
- Meilisearch excels at full-text, SurrealDB at vectors

### Decision 3: Custom RRF over SurrealDB's search::rrf

**Context**: SurrealDB has built-in RRF, but we have custom implementation

**Decision**: Keep custom RRF in `fusion.rs`

**Rationale**:
- More control over algorithm parameters
- Can add TTRPG-specific boosting
- Already tested and working
- SurrealDB's RRF would require running both searches in SurrealDB

---

## 9. Dependencies

### 9.1 New Dependencies

```toml
# Cargo.toml additions
[dependencies]
# Embedded Meilisearch - from workspace
meilisearch-lib = { path = "../../crates/meilisearch-lib" }

# SurrealDB with embedded storage
surrealdb = { version = "2.5", features = [
    "kv-rocksdb",      # RocksDB for persistence
    "rustls",          # TLS support
] }
```

### 9.2 Removed Dependencies

```toml
# To remove
meilisearch-sdk = "0.31"  # Replaced by meilisearch-lib
```

### 9.3 Build Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Binary size (release) | ~50 MB | ~75 MB | +25 MB (SurrealDB + deps) |
| Compile time (clean) | ~180s | ~240s | +60s |
| Runtime dependencies | 1 (meilisearch binary) | 0 | Eliminated |

---

## 10. Open Questions

1. **Q: Should we support multiple embedders simultaneously?**
   - Current: Single provider at a time
   - Future: May want mixed embeddings per-index
   - Recommendation: Track embedder per-vector, warn on mismatch

2. **Q: How to handle HNSW index memory for large vector stores?**
   - SurrealDB loads HNSW into memory
   - 1M vectors × 1536 dims × 4 bytes = ~6GB
   - Recommendation: Document memory requirements, add warnings

3. **Q: Migration path for users with existing vectorStore data?**
   - Meilisearch vectorStore may not export embeddings directly
   - May need to re-embed during migration
   - Recommendation: Detect and prompt, don't auto-migrate
