# Requirements: Akasha Ingestion Integration

## Introduction
The goal is to integrate the `akasha` library into the `ttrpg-assistant` ingestion pipeline to improve extraction quality, particularly for PDFs, and to enhance semantic chunking. This will replace or augment the existing `kreuzberg` extractor for specific document types, providing richer metadata (confidence scores, layout info) and better preservation of semantic structures (tables, lists).

## Requirements

### Requirement 1: Akasha Integration
**User Story:** As a developer, I want to use `akasha` for document extraction so that I can leverage its high-performance structure-aware capabilities.

#### Acceptance Criteria
1.  **WHEN** a PDF document is ingested **THEN** the system **SHALL** use `akasha` to extract content.
2.  **IF** `akasha` fails to extract content **THEN** the system **SHALL** fallback to `kreuzberg` or existing error handling (optional, defined by design).
3.  **WHERE** `akasha` requires configuration **THEN** the system **SHALL** expose relevant settings (e.g., performance vs quality).

### Requirement 2: Semantic Chunking
**User Story:** As a user, I want ingested documents to be chunked intelligently so that RAG responses don't break mid-sentence or mid-table.

#### Acceptance Criteria
1.  **WHEN** extracting content **THEN** `akasha` **SHALL** identify semantic boundaries (paragraphs, tables, headers).
2.  **WHEN** chunking content **THEN** the system **SHALL** respect these boundaries, preventing splits within tables or semantic blocks where possible.
3.  **IF** a chunk exceeds the token limit **THEN** the system **SHALL** split it using a smart fallback strategy (e.g., sentence boundary).

### Requirement 3: Metadata Enrichment
**User Story:** As a user, I want to know the confidence and source location of extracted information so that I can trust the results.

#### Acceptance Criteria
1.  **WHEN** content is extracted **THEN** the output **SHALL** include confidence scores for text and tables.
2.  **WHEN** content is extracted **THEN** the output **SHALL** include bounding box coordinates and page numbers.
3.  **WHEN** writing to the document index (`<slug>-raw`) **THEN** this metadata **SHALL** be preserved.

### Requirement 4: Ingestion Pipeline Update
**User Story:** As a system, I want the ingestion pipeline to seamlessly handle the new extractor so that existing workflows remain unbroken.

#### Acceptance Criteria
1.  **WHEN** processing a file **THEN** the `ExtractedContent` struct (or equivalent) **SHALL** be populated from `akasha`'s output.
2.  **WHEN** completion occurs **THEN** the system **SHALL** write to the `<slug>-raw` index with the enriched data.

## Non-Functional Requirements
- **Performance**: Akasha extraction **SHALL** be parallelized where possible.
- **Maintainability**: The integration **SHALL** be modular, allowing easy updates to `akasha` or `kreuzberg`.

## Constraints and Assumptions
- Assumes `akasha` library is available locally or via crate.
- Assumes `akasha` supports the target PDF features.
