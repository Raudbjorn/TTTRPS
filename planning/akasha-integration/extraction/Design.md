# Design: Akasha Extraction Enhancement

## Overview

This design extends the existing akasha integration to fully utilize its ML-powered semantic structure detection for improved TTRPG document chunking. The key insight is that akasha's layout analysis already produces structural metadata (stored in `structural_data`), but the chunking phase doesn't consume it.

### Design Goals
- **Semantic Preservation**: Never split tables, stat-blocks, or semantic units
- **Context Enrichment**: Every chunk knows its position in the document hierarchy
- **Async-First**: Non-blocking extraction with progress reporting
- **Graceful Degradation**: Fall back to text-based chunking when structure unavailable

### Key Design Decisions
- **Preserve Two-Phase Architecture**: Store rich structure in Phase 1 (raw index), consume in Phase 2 (chunking)
- **Extend TTRPGChunker**: Add structure-aware mode rather than replacing the chunker
- **Use spawn_blocking**: Offload synchronous akasha extraction to Tokio's blocking threadpool
- **Confidence Threshold**: Use 0.6 default, configurable per-user

## Architecture

### System Overview

```
PDF Upload
    ↓
DocumentExtractor::extract(path, callback)  [async]
    ↓
    ├─ if use_akasha && is_pdf?
    │   └─ spawn_blocking → AkashaExtractor::extract()
    │       ├─ Layout Analysis (LayoutLMv3-small)
    │       ├─ Table Detection (YOLOv8-nano)
    │       ├─ Structure Tree Building
    │       └─ Returns ExtractedContent with structural_data
    │
    └─ fallback to kreuzberg
        ↓
ExtractedContent
    ↓
Meilisearch Raw Index (<slug>-raw)
    ├─ content: String
    ├─ structural_data: Option<JSON>  ← NEW: Full hierarchy
    ├─ pages[].layout_info: Option<JSON>  ← Bboxes, confidence
    └─ metadata: {...}
    ↓
Phase 2: TTRPGChunker::chunk_from_structure()  ← NEW
    ├─ Parse structural_data JSON
    ├─ Build DocumentTree
    ├─ Respect semantic boundaries
    ├─ Add breadcrumb context
    └─ Split oversized at sentence boundaries
    ↓
Meilisearch Chunks Index (<slug>)
    ├─ content: String
    ├─ breadcrumb: Vec<String>  ← NEW
    ├─ confidence: f64  ← NEW
    ├─ chunk_type: String  ← NEW (paragraph, table, stat_block, etc.)
    └─ page, bbox, source_id
```

### Component Architecture

```
src-tauri/src/
├── ingestion/
│   ├── akasha_extractor.rs     # AkashaExtractor (modify: async wrapper)
│   ├── extraction_settings.rs  # Settings (modify: add akasha config)
│   ├── kreuzberg_extractor.rs  # DocumentExtractor (modify: async routing)
│   └── chunker.rs              # TTRPGChunker (modify: structure-aware mode)
├── core/
│   ├── meilisearch_pipeline.rs # chunk_from_raw (modify: use structural_data)
│   └── settings/               # NEW: AkashaConfig persistence
└── tests/
    └── akasha_ingest_test.rs   # Tests (modify: real PDF tests)
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Extraction | akasha-core (local) | ML-powered layout analysis |
| Async | tokio::task::spawn_blocking | Non-blocking sync extraction |
| Serialization | serde_json | Structure metadata storage |
| Chunking | TTRPGChunker (extended) | Domain-specific TTRPG logic |
| Storage | Meilisearch | Schemaless JSON, hybrid search |

## Components and Interfaces

### AkashaExtractor (Modification)

**Purpose**: Bridge to akasha library with async support

**Current Interface**:
```rust
impl AkashaExtractor {
    pub fn new(settings: &ExtractionSettings) -> Self;
    pub fn extract(&self, path: &Path) -> Result<ExtractedContent, KreuzbergError>;
}
```

**New Interface**:
```rust
impl AkashaExtractor {
    pub fn new(config: &AkashaConfig) -> Self;

    /// Async extraction wrapper
    pub async fn extract_async(&self, path: PathBuf) -> Result<ExtractedContent, KreuzbergError>;

    /// Synchronous extraction (internal, called via spawn_blocking)
    fn extract_sync(&self, path: &Path) -> Result<ExtractedContent, KreuzbergError>;
}
```

**Implementation Notes**:
- Use `tokio::task::spawn_blocking` to offload synchronous akasha calls
- Clone necessary data for the blocking closure
- Return `JoinHandle<Result<...>>` for cancellation support

### AkashaConfig (New)

**Purpose**: Centralized akasha configuration

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AkashaConfig {
    pub enabled: bool,                    // Default: true
    pub confidence_threshold: f64,        // Default: 0.6
    pub parallel: bool,                   // Default: true
    pub enable_vision: bool,              // Default: true
    pub enable_ocr: bool,                 // Default: true
    pub enable_formulas: bool,            // Default: false
    pub enable_charts: bool,              // Default: false
    pub performance_profile: PerformanceProfile,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PerformanceProfile {
    Speed,     // Disable heavy features
    Balanced,  // Smart defaults
    Quality,   // Enable everything
}
```

### DocumentTree (New)

**Purpose**: Hierarchical representation of document structure for chunking

```rust
#[derive(Debug, Clone)]
pub struct DocumentTree {
    pub root: TreeNode,
}

#[derive(Debug, Clone)]
pub struct TreeNode {
    pub element_type: ElementType,
    pub content: String,
    pub children: Vec<TreeNode>,
    pub metadata: ElementMetadata,
}

#[derive(Debug, Clone)]
pub enum ElementType {
    Document,
    Section { level: u8, title: String },
    Paragraph,
    Table { rows: usize, cols: usize },
    List { ordered: bool },
    StatBlock,  // TTRPG-specific
    Formula,
    Figure,
}

#[derive(Debug, Clone)]
pub struct ElementMetadata {
    pub page: u32,
    pub bbox: Option<BoundingBox>,
    pub confidence: f64,
    pub token_estimate: usize,
}
```

### TTRPGChunker (Extension)

**Purpose**: Structure-aware chunking with TTRPG domain knowledge

**New Methods**:
```rust
impl TTRPGChunker {
    /// Chunk using structural metadata from akasha
    pub fn chunk_from_structure(
        &self,
        structural_data: &serde_json::Value,
        source_id: &str,
    ) -> Vec<ContentChunk>;

    /// Build document tree from JSON
    fn parse_structure(&self, json: &serde_json::Value) -> Option<DocumentTree>;

    /// Recursive tree traversal with boundary respect
    fn chunk_tree_node(
        &self,
        node: &TreeNode,
        breadcrumb: &[String],
        chunks: &mut Vec<ContentChunk>,
    );

    /// Split large content at sentence boundaries
    fn split_at_sentences(&self, content: &str, max_tokens: usize) -> Vec<String>;
}
```

**Chunking Algorithm**:
1. Parse `structural_data` JSON into `DocumentTree`
2. Depth-first traverse, accumulating breadcrumb path
3. For each leaf node (paragraph, table, etc.):
   - If tokens <= max_tokens: emit as single chunk
   - If table: always emit as single chunk (warn if oversized)
   - If paragraph > max_tokens: split at sentence boundaries
4. Merge consecutive small paragraphs within same section
5. Add breadcrumb and confidence to each chunk

### ContentChunk (Extension)

**Current Fields**: id, content, source_id, page_number, chunk_type, token_count

**New Fields**:
```rust
pub struct ContentChunk {
    // ... existing fields ...
    pub breadcrumb: Vec<String>,        // ["Chapter 3", "Combat", "Actions"]
    pub confidence: f64,                 // From akasha extraction
    pub element_type: String,            // "paragraph", "table", "stat_block"
    pub bbox: Option<BoundingBox>,       // For source highlighting
    pub related_chunks: Vec<String>,     // IDs of chunks from same section
}
```

## Data Models

### ExtractedContent (Existing + Extension)

```rust
pub struct ExtractedContent {
    pub content: String,
    pub metadata: Option<DocumentMetadata>,
    pub pages: Option<Vec<Page>>,
    pub language: Option<String>,
    pub extraction_method: Option<String>,

    // Already added on this branch:
    pub structural_data: Option<serde_json::Value>,
}

pub struct Page {
    pub content: String,
    pub page_number: u32,

    // Already added:
    pub layout_info: Option<serde_json::Value>,
}
```

### structural_data JSON Schema

```json
{
  "document_type": "pdf",
  "extraction_engine": "akasha",
  "overall_confidence": 0.87,
  "structure": {
    "type": "document",
    "children": [
      {
        "type": "section",
        "level": 1,
        "title": "Chapter 1: Introduction",
        "children": [
          {
            "type": "paragraph",
            "content": "This chapter introduces...",
            "confidence": 0.92,
            "page": 1,
            "bbox": {"x0": 72, "y0": 100, "x1": 540, "y1": 150}
          },
          {
            "type": "table",
            "title": "Table 1.1: Ability Scores",
            "rows": 7,
            "cols": 3,
            "content": "| Ability | Score | Modifier |\n|...",
            "confidence": 0.95,
            "page": 2,
            "bbox": {"x0": 72, "y0": 200, "x1": 540, "y1": 400}
          }
        ]
      }
    ]
  }
}
```

## Error Handling

| Category | Condition | Response |
|----------|-----------|----------|
| Akasha Failure | extraction throws error | Log warning, fall back to kreuzberg |
| Low Confidence | overall_confidence < threshold | Flag document for review, continue |
| Missing Structure | structural_data is None | Use text-based chunking fallback |
| Oversized Table | table_tokens > max_tokens | Keep table intact, emit warning |
| Invalid JSON | structural_data parse fails | Log error, use text-based fallback |

## Testing Strategy

### Unit Tests
- `test_parse_structure`: Verify JSON parsing to DocumentTree
- `test_chunk_section_boundary`: Verify sections not split
- `test_chunk_table_atomic`: Verify tables kept intact
- `test_breadcrumb_generation`: Verify path construction
- `test_sentence_splitting`: Verify oversized content splits correctly

### Integration Tests
- `test_akasha_real_pdf`: Extract real PDF, verify structural_data populated
- `test_chunking_with_structure`: Full pipeline with akasha extraction + chunking
- `test_fallback_to_kreuzberg`: Verify fallback when akasha disabled/fails
- `test_async_extraction`: Verify non-blocking behavior

### Test Fixtures
- `test_simple.pdf`: Single-column, headings, paragraphs
- `test_tables.pdf`: Multiple tables with headers
- `test_ttrpg_statblock.pdf`: D&D-style stat blocks
- `test_multicolumn.pdf`: Two-column layout

## Performance Considerations

- **Async Extraction**: Use `spawn_blocking` to avoid blocking Tokio runtime
- **Lazy Parsing**: Only parse structural_data when chunking, not on every query
- **Batch Processing**: Process multiple pages in parallel within akasha
- **Caching**: Consider caching DocumentTree for re-chunking scenarios
