# Tasks: Akasha Extraction Enhancement

## Implementation Overview

This task list extends the existing akasha integration to fully utilize structural metadata for semantic chunking. The work is organized into three phases: async extraction, structure-aware chunking, and UI/settings completion.

## Implementation Plan

### Phase 1: Async Extraction & Configuration

- [ ] 1. Async Extraction Support
- [ ] 1.1 Create AkashaConfig struct
  - Add `src-tauri/src/core/settings/akasha_config.rs`
  - Define `AkashaConfig` with fields: enabled, confidence_threshold, parallel, enable_vision, enable_ocr, enable_formulas, enable_charts, performance_profile
  - Implement `Default`, `Serialize`, `Deserialize`
  - Add `PerformanceProfile` enum (Speed, Balanced, Quality)
  - _Requirements: 3.1, 3.2_

- [ ] 1.2 Integrate AkashaConfig into settings manager
  - Modify `src-tauri/src/core/settings/mod.rs` to include akasha config
  - Add load/save methods for akasha configuration
  - Ensure persistence to disk (JSON or TOML)
  - _Requirements: 3.3_

- [ ] 1.3 Convert AkashaExtractor to async
  - Modify `src-tauri/src/ingestion/akasha_extractor.rs`
  - Add `extract_async(&self, path: PathBuf) -> Result<ExtractedContent>` method
  - Use `tokio::task::spawn_blocking` to wrap synchronous extraction
  - Clone necessary data for blocking closure (path, config)
  - Handle `JoinError` for task cancellation
  - _Requirements: 2.1, 2.4_

- [ ] 1.4 Update DocumentExtractor routing for async
  - Modify `src-tauri/src/ingestion/kreuzberg_extractor.rs`
  - Change PDF routing to use `AkashaExtractor::extract_async()`
  - Maintain fallback logic for akasha failures
  - Update progress callback integration
  - _Requirements: 2.1, 2.2, 3.4_

### Phase 2: Structure-Aware Chunking

- [ ] 2. Document Tree & Parsing
- [ ] 2.1 Define DocumentTree data structures
  - Add structs to `src-tauri/src/ingestion/chunker.rs` or new module
  - Define `DocumentTree`, `TreeNode`, `ElementType`, `ElementMetadata`
  - Add TTRPG-specific element types: StatBlock, SpellBlock, MonsterBlock
  - Implement `BoundingBox` if not already present
  - _Requirements: 5.1_

- [ ] 2.2 Implement structural_data JSON parser
  - Add `fn parse_structure(json: &Value) -> Option<DocumentTree>` to TTRPGChunker
  - Handle akasha's nested structure format
  - Validate required fields (type, content, confidence)
  - Map akasha element types to internal ElementType enum
  - _Requirements: 5.1, 1.4_

- [ ] 3. Structure-Aware Chunking
- [ ] 3.1 Implement chunk_from_structure method
  - Add method to TTRPGChunker in `src-tauri/src/ingestion/chunker.rs`
  - Signature: `fn chunk_from_structure(&self, structural_data: &Value, source_id: &str) -> Vec<ContentChunk>`
  - Check if structural_data is present; if not, delegate to existing text-based chunking
  - _Requirements: 1.1, 1.4_

- [ ] 3.2 Implement tree traversal with boundary respect
  - Add `fn chunk_tree_node(&self, node: &TreeNode, breadcrumb: &[String], chunks: &mut Vec<ContentChunk>)`
  - Depth-first traversal
  - Accumulate breadcrumb path as sections are entered
  - For leaf nodes: create chunk with full context
  - _Requirements: 1.1, 5.2_

- [ ] 3.3 Implement atomic table chunking
  - Tables are never split, regardless of token count
  - If table exceeds max_tokens, emit warning but keep intact
  - Preserve table structure in content (markdown format)
  - Add `chunk_type: "table"` to metadata
  - _Requirements: 1.2_

- [ ] 3.4 Implement TTRPG element detection and preservation
  - Detect stat blocks, spell blocks, monster blocks
  - Use existing classification logic from TTRPGChunker
  - Keep TTRPG elements atomic when possible
  - Add appropriate chunk_type metadata
  - _Requirements: 1.3_

- [ ] 3.5 Implement sentence-boundary splitting for oversized content
  - Add `fn split_at_sentences(&self, content: &str, max_tokens: usize) -> Vec<String>`
  - Use unicode-segmentation or regex for sentence detection
  - Respect sentence boundaries when splitting large paragraphs
  - Handle edge cases: no sentence breaks, single-sentence content
  - _Requirements: 1.5_

- [ ] 3.6 Implement short chunk merging
  - Merge consecutive small paragraphs within same section
  - Respect max_tokens limit after merging
  - Maintain consistent breadcrumb for merged chunks
  - _Requirements: 1.1_

- [ ] 4. ContentChunk Enhancement
- [ ] 4.1 Extend ContentChunk struct
  - Add fields: breadcrumb (Vec<String>), confidence (f64), element_type (String), bbox (Option<BoundingBox>), related_chunks (Vec<String>)
  - Update serialization for Meilisearch storage
  - Ensure backward compatibility with existing chunks
  - _Requirements: 4.1, 4.3, 5.2_

- [ ] 4.2 Integrate confidence scoring into chunks
  - Extract confidence from structural_data per element
  - Propagate to ContentChunk
  - Add overall document confidence tracking
  - _Requirements: 4.1, 4.2_

### Phase 3: Pipeline Integration & UI

- [ ] 5. Pipeline Integration
- [ ] 5.1 Update chunk_from_raw in meilisearch_pipeline.rs
  - Modify `src-tauri/src/core/meilisearch_pipeline.rs`
  - Check for structural_data presence in raw document
  - If present: use `TTRPGChunker::chunk_from_structure()`
  - If absent: use existing text-based chunking
  - _Requirements: 1.1, 1.4_

- [ ] 5.2 Update Meilisearch chunk schema
  - Add new fields to chunk documents: breadcrumb, confidence, element_type, bbox
  - Update search queries to utilize confidence for ranking
  - Ensure searchable/filterable attributes are configured
  - _Requirements: 4.4, 5.3_

- [ ] 6. Frontend & Settings UI
- [ ] 6.1 Add akasha toggle to settings UI
  - Locate settings component in `frontend/src/components/settings/`
  - Add checkbox/switch for `use_akasha` (may already exist but be hidden)
  - Wire to `AkashaConfig.enabled`
  - _Requirements: 3.1_

- [ ] 6.2 Add advanced akasha configuration UI
  - Add collapsible "Advanced" section for akasha settings
  - Include: confidence threshold slider, feature toggles, performance profile selector
  - Bind to `AkashaConfig` fields
  - _Requirements: 3.2_

- [ ] 6.3 Display extraction confidence in UI
  - Show document-level confidence after ingestion
  - Highlight low-confidence documents in library view
  - Display chunk confidence in search results (optional)
  - _Requirements: 4.2_

- [ ] 6.4 Add breadcrumb display in search results
  - Show breadcrumb path for each search result
  - Format as clickable trail or static text
  - Help users understand document context
  - _Requirements: 5.3_

### Phase 4: Testing & Validation

- [ ] 7. Unit Tests
- [ ] 7.1 Test DocumentTree parsing
  - Create `tests/chunker_structure_tests.rs` or add to existing test module
  - Test parsing valid structural_data JSON
  - Test handling of malformed JSON (graceful failure)
  - Test mapping of element types
  - _Requirements: 6.1_

- [ ] 7.2 Test boundary preservation
  - Test section boundaries not crossed
  - Test tables kept atomic
  - Test TTRPG elements preserved
  - _Requirements: 6.2_

- [ ] 7.3 Test sentence splitting
  - Test oversized paragraphs split correctly
  - Test edge cases: no sentences, single sentence, very long sentence
  - _Requirements: 6.2_

- [ ] 7.4 Test breadcrumb generation
  - Test nested section breadcrumbs
  - Test flat document breadcrumbs
  - Test empty/missing sections
  - _Requirements: 6.2_

- [ ] 8. Integration Tests
- [ ] 8.1 Create test PDF fixtures
  - Add to `src-tauri/tests/fixtures/` or similar
  - Include: simple.pdf, tables.pdf, ttrpg_statblock.pdf, multicolumn.pdf
  - Document expected structure for each fixture
  - _Requirements: 6.1_

- [ ] 8.2 End-to-end akasha extraction test
  - Test full extraction with real PDF
  - Verify structural_data is populated
  - Verify pages have layout_info
  - Verify metadata extraction
  - _Requirements: 6.1_

- [ ] 8.3 End-to-end chunking test
  - Test extraction + chunking pipeline
  - Verify chunks have breadcrumbs
  - Verify tables are atomic
  - Verify confidence is propagated
  - _Requirements: 6.2_

- [ ] 8.4 Fallback behavior test
  - Test with use_akasha = false
  - Test with akasha extraction failure (mock or force error)
  - Verify graceful degradation to kreuzberg
  - _Requirements: 6.3_

### Phase 5: Documentation & Cleanup

- [ ] 9. Code Cleanup
- [ ] 9.1 Remove unused imports (per diagnostic warnings)
  - Fix warnings in unified.rs, lattice.rs, text.rs, lib.rs
  - Remove unused variables: text, model_manager, ocr_strategy, pdf, lines
  - Remove unused mut qualifiers
  - _N/A: Code hygiene_

- [ ] 9.2 Add documentation
  - Document AkashaExtractor public API
  - Document TTRPGChunker structure-aware methods
  - Document AkashaConfig options
  - _N/A: Code hygiene_

- [ ] 9.3 Update CLAUDE.md if needed
  - Document new akasha configuration options
  - Update architecture section if structure changed significantly
  - _N/A: Documentation_
