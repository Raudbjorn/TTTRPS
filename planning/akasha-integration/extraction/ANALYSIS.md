# Akasha Integration Analysis

## ML Capabilities for Semantic Boundary Detection

### Overview

Akasha uses a **hybrid ML approach** combining embedded ONNX models with heuristic algorithms for semantic boundary detection. The key insight is that semantic boundaries are identified through **layout analysis** (what type of element is this?) combined with **structure building** (how do elements relate hierarchically?).

### ML Models for Semantic Detection

| Model | Size | Purpose | Detects |
|-------|------|---------|---------|
| **LayoutLMv3-small** | 15MB | Layout Analysis | headings, paragraphs, lists, tables, figures, captions, headers, footers |
| **YOLOv8-nano** | 10MB | Table Detection | tables, figures, charts |
| **Column Detector** | 8MB | Multi-column Layout | column boundaries, reading order |
| **Formula Detector** | 12MB | Formula Detection | mathematical/chemical formulas |
| **TinyBERT Confidence** | 5MB | Text Quality | extraction confidence scores |

### "Bring Your Own" Models (README.md lines 173-176)

```python
# bring your own onnx models
akasha = Akasha(
    table_model="models/custom_table.onnx",
    ocr_model="models/custom_ocr.onnx"
)
```

This allows substituting akasha's embedded models with custom ONNX models for:
- **Table detection**: Train on domain-specific table formats (e.g., TTRPG stat blocks)
- **OCR**: Use specialized OCR for handwritten annotations or unusual fonts

### Semantic Boundary Detection Pipeline

```
PDF Page Image
    ↓
Layout Analysis (LayoutLMv3)
    ├── Identifies regions: heading, paragraph, table, list, figure, caption
    ├── Assigns bounding boxes to each region
    └── Determines reading order
    ↓
Table Detection (YOLOv8)
    ├── Refines table boundaries
    └── Detects nested tables
    ↓
Structure Building (Heuristics + ML)
    ├── Font size changes → section hierarchy
    ├── Spacing patterns → paragraph breaks
    ├── Indentation → list nesting
    └── Position → reading order
    ↓
Document Tree
    └── Hierarchical representation ready for chunking
```

### Key Semantic Preservation Features

1. **Never Split Tables**: Table cells and rows are atomic units
2. **Section Awareness**: Headings create natural boundaries
3. **Breadcrumb Context**: Each element knows its path in the document hierarchy
4. **Reading Order**: Multi-column layouts read correctly
5. **Confidence Scoring**: Every element has extraction confidence

## Current Implementation Status (This Branch)

### Completed Work

| Component | Status | Notes |
|-----------|--------|-------|
| AkashaExtractor module | ✅ Done | Basic extraction working |
| Settings `use_akasha` flag | ✅ Done | Can toggle akasha on/off |
| Fallback to kreuzberg | ✅ Done | Graceful degradation |
| `structural_data` storage | ✅ Done | JSON stored in ExtractedContent |
| `layout_info` per page | ✅ Done | Per-page bbox and confidence |
| Cargo.toml dependency | ✅ Done | Local path to akasha-core |

### Missing/Incomplete

| Component | Status | Impact |
|-----------|--------|--------|
| **Async extraction** | ❌ Missing | Blocks main thread during extraction |
| **UI toggle visibility** | ⚠️ Unclear | Settings exist but toggle may not be visible |
| **Chunker integration** | ❌ Missing | `structural_data` stored but not used by TTRPGChunker |
| **Akasha config exposure** | ❌ Missing | confidence_threshold etc. hardcoded |
| **Real integration tests** | ❌ Missing | Only stub tests exist |
| **Confidence utilization** | ❌ Missing | Scores stored but not used downstream |
| **Breadcrumb context** | ❌ Missing | Chunks don't include hierarchy path |

## Immediate Improvement Opportunities

### 1. Structure-Aware Chunking (High Impact)

**Current State**: TTRPGChunker uses text-based chunking, ignoring `structural_data`

**Improvement**: Modify `chunk_from_raw` to parse `structural_data` and respect semantic boundaries

**Code Location**: `src-tauri/src/core/meilisearch_pipeline.rs:1332`

**Expected Impact**:
- Tables never split mid-row
- Stat blocks kept intact
- Better RAG retrieval quality

### 2. Async Extraction (Medium Impact)

**Current State**: `AkashaExtractor::extract()` is synchronous

**Improvement**: Wrap with `tokio::task::spawn_blocking`

**Code Location**: `src-tauri/src/ingestion/akasha_extractor.rs`

**Expected Impact**:
- UI remains responsive during extraction
- Better UX for large documents

### 3. UI Settings Toggle (Low Effort)

**Current State**: `use_akasha` exists in settings but may not have visible UI

**Improvement**: Ensure checkbox/toggle is rendered in settings component

**Code Location**: `frontend/src/components/settings/data.rs`

**Expected Impact**:
- Users can enable/disable akasha without code changes

### 4. Confidence-Based Quality Feedback (Medium Impact)

**Current State**: Confidence scores stored but ignored

**Improvement**:
- Flag low-confidence documents for review
- Weight search results by confidence
- Show confidence in UI

**Expected Impact**:
- Users know when to manually review documents
- Better search ranking

## Akasha Chunking Strategies (Not Yet Exposed)

Akasha provides built-in chunking that the integration doesn't use:

```rust
pub enum ChunkStrategy {
    /// Respect document structure completely
    Semantic { merge_short_sections: bool, split_long_sections: bool },

    /// Chunk by specific element types
    ByElement { types: Vec<ElementType> },

    /// Sliding window with structure awareness
    SlidingWindow { respect_boundaries: bool },

    /// Optimized for specific embedding models
    EmbeddingOptimized { model: EmbeddingModel },

    /// Custom function for specialized needs
    Custom(Box<dyn Fn(&Element) -> Vec<ChunkDecision>>),
}
```

**Option A**: Use akasha's `doc.chunk()` during Phase 1 (extraction), store pre-chunked data
**Option B**: Store structure, implement equivalent chunking in Phase 2 (current approach)

Option B is preferred to preserve the two-phase architecture and allow re-chunking without re-extraction.

## Diagnostic Warnings (Code Cleanup)

The system-reminder shows several warnings that should be fixed:

```
unified.rs: unused imports (Formula, rayon::prelude), unused variables
lattice.rs: unused import (HashMap), unused variables, dead_code
text.rs: unused import (BoundingBox), unused variable, dead_code
lib.rs: unused import (rayon::prelude::*)
```

These are in the akasha-core library, not the ttrpg-assistant code. They may need to be fixed upstream or suppressed.

## Recommended Next Steps

1. **Phase 1 (Quick Wins)**:
   - Add UI toggle visibility for `use_akasha`
   - Add async wrapper for extraction
   - Fix diagnostic warnings

2. **Phase 2 (Core Value)**:
   - Implement `chunk_from_structure` in TTRPGChunker
   - Add breadcrumb context to chunks
   - Preserve tables as atomic units

3. **Phase 3 (Polish)**:
   - Expose akasha configuration in UI
   - Add confidence-based quality feedback
   - Write comprehensive integration tests

## References

- Akasha README: `./planning/akasha-integration/akasha/README.md`
- Architecture: `./planning/akasha-integration/akasha/references/project-references/akasha_architecture.md`
- Chunking Deep Dive: `./planning/akasha-integration/akasha/references/project-references/akasha_chunking_deep_dive.md`
- ML/OCR Strategy: `./planning/akasha-integration/akasha/references/project-references/akasha_ml_ocr_strategy.md`
- Original Integration Design: `./planning/akasha-integration/Design.md`
