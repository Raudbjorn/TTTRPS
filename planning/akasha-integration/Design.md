# Design: Akasha Ingestion Integration

## Overview
This design outlines the integration of the `akasha` library into the `ttrpg-assistant` to replace/augment the PDF extraction pipeline. The goal is to leverage `akasha`'s structure-aware extraction to improve data quality for RAG.

### Design Goals
- **Higher Quality Extraction**: Use `akasha` for PDFs to better handle multi-column layouts and tables.
- **Richer Metadata**: persist confidence scores and bounding boxes.
- **Improved Chunking**: Utilize `akasha`'s semantic chunking strategies.
- **Seamless Integration**: Maintain the existing two-phase ingestion (Extract -> Chunk) where possible, but adapt data structures to hold richer info.

## Architecture

### System Overview
The current system uses a two-phase ingestion:
1.  **Extraction**: Reads file -> `ExtractedContent` -> Writes to `<slug>-raw` index (one document per page).
2.  **Chunking**: Reads `<slug>-raw` -> Chunks -> Writes to `<slug>` index.

We will modify Phase 1 to use `akasha` for PDFs.
We will modify the data structures stored in `<slug>-raw` to include Akasha's structural metadata (JSON representation of layout).
We will modify Phase 2 to utilize this metadata for smarter chunking.

### Component Architecture

1.  **ExtractionSettings**: Add `use_akasha: bool` (default true for PDF).
2.  **DocumentExtractor**: Update to route PDF extraction to `AkashaExtractor`.
3.  **AkashaExtractor**: New struct/module wrapping `akasha` library calls.
4.  **ExtractedContent**: Add `structural_metadata: Option<Value>` (JSON) field to store Akasha's rich output.

### Technology Stack
- **Rust**: Language.
- **Akasha**: New dependency (local path or crate).
- **Meilisearch**: Storage for raw and chunked indices (no schema change needed as it's schemaless JSON, but we add fields).

## Components and Interfaces

### AkashaExtractor
- **Purpose**: Bridge between `ttrpg-assistant` and `akasha` lib.
- **Interfaces**:
    - `extract(path: &Path, settings: &ExtractionSettings) -> Result<ExtractedContent>`
- **Implementation Notes**:
    - Initialize `akasha::Akasha`.
    - Call `extract_file`.
    - Map `akasha::Document` to `ExtractedContent`.
    - Serialize `akasha::Page` structure (tables, blocks) into `ExtractedContent.pages[i].metadata`.

### DocumentExtractor (Modification)
- **Change**: In `extract()`, check if `use_akasha` is true and file is PDF. If so, delegate to `AkashaExtractor`.

### Chunking Strategy (Update)
- **Current**: Likely text-based splitting.
- **New**: If `structural_metadata` is present, use it.
    - Akasha provides `chunk()` method. We might want to use that *during extraction* or *re-implement* logic to use the stored metadata in Phase 2.
    - **Decision**: To preserve the two-phase architecture (which allows re-chunking without re-extracting), we should store the *rich structure* in Phase 1 (Raw Index). In Phase 2, we parse this structure and generate chunks.
    - Alternatively, Akasha can generate chunks directly. If so, Phase 2 could just "load chunks" if they were pre-calculated. But Phase 2 often applies new chunking rules.
    - **Refined Approach**: Store the "Structure Tree" (Markdown or JSON) in `<slug>-raw`.

## Data Models

### ExtractedContent (Update)
```rust
pub struct ExtractedContent {
    // ... existing fields ...
    pub structural_data: Option<serde_json::Value>, // Akasha's full struct tree
    pub pages: Option<Vec<Page>>,
}

pub struct Page {
    // ... existing fields ...
    pub layout_info: Option<serde_json::Value>, // Per-page layout (bboxes, tables)
}
```

## Testing Strategy
- **Unit Tests**: Test `AkashaExtractor` with sample PDFs.
- **Integration Tests**: Run full ingestion pipeline on a test PDF and verify `<slug>-raw` contains `layout_info`.
- **Manual Verification**: Ingest a complex TTRPG visual page and check if text order is correct.
