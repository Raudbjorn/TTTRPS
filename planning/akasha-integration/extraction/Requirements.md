# Requirements: Akasha Extraction Enhancement

## Introduction

The current akasha integration provides basic PDF extraction with structural metadata, but the extracted semantic structure is not utilized downstream. This enhancement aims to leverage akasha's ML-powered layout analysis and structure-aware chunking capabilities to improve RAG quality for TTRPG documents.

Akasha provides ML models for semantic boundary detection (LayoutLMv3-small for layout analysis, YOLOv8-nano for table detection) that identify headings, paragraphs, lists, tables, figures, and reading order. This structural intelligence is currently extracted and stored but not consumed by the chunking phase.

## Requirements

### Requirement 1: Structure-Aware Chunking Integration
**User Story:** As a Game Master, I want documents chunked at natural semantic boundaries so that RAG responses don't break mid-sentence, mid-table, or mid-stat-block.

#### Acceptance Criteria
1. WHEN structural_data is present in raw index THEN the chunker SHALL use semantic boundaries from akasha's layout analysis
2. WHEN a table is detected THEN the chunker SHALL preserve the table as an atomic unit (never split table cells or rows)
3. WHEN a stat-block or game element is detected THEN the chunker SHALL keep it intact up to max_tokens limit
4. IF structural_data is absent THEN the chunker SHALL fall back to existing text-based chunking
5. WHEN a chunk exceeds max_tokens THEN the system SHALL split at sentence boundaries rather than arbitrary positions

### Requirement 2: Async Extraction Pipeline
**User Story:** As a user, I want PDF extraction to not freeze the application UI so that I can continue working during ingestion.

#### Acceptance Criteria
1. WHEN a PDF is submitted for extraction THEN the system SHALL process it asynchronously without blocking the main event loop
2. WHILE extraction is in progress THEN the system SHALL report progress to the frontend via callbacks
3. IF extraction takes longer than 30 seconds THEN the system SHALL provide intermediate status updates
4. WHEN extraction completes THEN the system SHALL notify the frontend with results

### Requirement 3: Akasha Configuration Exposure
**User Story:** As a power user, I want to tune akasha's extraction parameters so that I can optimize for my specific document types.

#### Acceptance Criteria
1. WHEN the settings UI loads THEN the system SHALL display a toggle for enabling/disabling akasha extraction
2. WHERE akasha is enabled THEN the system SHALL allow configuration of:
   - Confidence threshold (0.0-1.0)
   - Feature toggles (vision, OCR, formulas, charts)
   - Performance profile (speed vs quality)
3. WHEN settings are changed THEN the system SHALL persist them across sessions
4. IF akasha is disabled THEN the system SHALL use kreuzberg for all extractions

### Requirement 4: Confidence-Based Quality Feedback
**User Story:** As a user, I want to know when extraction quality is low so that I can review problematic documents manually.

#### Acceptance Criteria
1. WHEN content is extracted THEN the system SHALL preserve confidence scores per block/element
2. WHEN overall confidence falls below threshold THEN the system SHALL flag the document for review
3. WHEN chunks are created THEN each chunk SHALL include its source confidence score
4. WHEN displaying search results THEN the system SHALL use confidence to weight relevance

### Requirement 5: Breadcrumb Context Preservation
**User Story:** As a Game Master, I want to know the document structure context for each chunk so that I understand where information came from.

#### Acceptance Criteria
1. WHEN akasha extracts document structure THEN the system SHALL build a hierarchical section tree
2. WHEN creating chunks THEN each chunk SHALL include a breadcrumb path (e.g., "Chapter 3 > Combat > Actions > Attack")
3. WHEN displaying RAG results THEN the system SHALL show the breadcrumb context
4. IF document has no clear hierarchy THEN the system SHALL use page/position as breadcrumb

### Requirement 6: Integration Test Coverage
**User Story:** As a developer, I want comprehensive tests for the akasha integration so that regressions are caught early.

#### Acceptance Criteria
1. WHEN running tests THEN the system SHALL include end-to-end PDF extraction tests with real files
2. WHEN testing chunking THEN tests SHALL verify structural boundaries are respected
3. WHEN testing fallback THEN tests SHALL verify graceful degradation when akasha fails
4. WHEN testing metadata THEN tests SHALL verify confidence scores and bounding boxes are preserved

## Non-Functional Requirements

- **Performance**: Async extraction SHALL not increase total extraction time by more than 10%
- **Memory**: Structural metadata storage SHALL not exceed 20% of document size
- **Compatibility**: Existing documents without structural_data SHALL continue to work

## Constraints and Assumptions

- Akasha is available as a local dependency at `../planning/akasha-integration/akasha/akasha-core`
- Akasha's ML models (LayoutLMv3-small, YOLOv8-nano) are embedded or available for download
- The two-phase ingestion architecture (Extract -> Chunk) will be preserved
- Leptos/Tauri architecture for frontend/backend communication
