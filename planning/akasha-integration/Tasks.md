# Tasks: Akasha Ingestion Integration

## Implementation Overview
We will introduce `akasha` as a dependency, implement the `AkashaExtractor`, and update the pipeline to use it for PDFs.

## Implementation Plan

## Implementation Plan

### Backend (Rust/Tauri)

- [x] 1. Foundation & Dependency
    - [x] 1.1 Add `akasha` dependency to `src-tauri/Cargo.toml`
        - Point to local path `../planning/akasha-integration/akasha` or git repo.
    - [x] 1.2 Update `ExtractionSettings`
        - Add `use_akasha` flag in `src-tauri/src/ingestion/extraction_settings.rs`.
        - Ensure `ts-rs` export is enabled to regenerate bindings.

- [/] 2. Implement AkashaExtractor
    - [x] 2.1 Create `src-tauri/src/ingestion/akasha_extractor.rs`
        - Implement `extract` function using `akasha::Akasha`.
        - Map output to `ExtractedContent`.
    - [x] 2.2 Detailed `Page` mapping
        - Ensure metadata (tables, bboxes) is serialized into the `Page` struct.

- [x] 3. Integrate into Pipeline
    - [x] 3.1 Modify `DocumentExtractor` in `src-tauri/src/ingestion/kreuzberg_extractor.rs`
        - Add logic to switch to `AkashaExtractor` for PDFs.
    - [x] 3.2 Update `commands.rs` ingestion flow (if needed).

### Frontend (TypeScript/React)

- [x] 4. Settings UI
    - [x] 4.1 Update Bindings
        - Run sync command or manually update `frontend/src/bindings/ExtractionSettings.ts` (or similar) to include `use_akasha`.
    - [x] 4.2 Add Toggle to Settings Page
        - Locate Ingestion/Extraction settings component.
        - Add Switch/Checkbox for `use_akasha`. Optimizations (PDF)".

### Verification

- [x] 5. Verification
    - [x] 5.1 Backend Integration Test `src-tauri/tests/akasha_ingest_test.rs`
    - [x] 5.2 Manual UI Verification
        - Toggle setting in UI, check persistence.
        - Ingest PDF, verify logs show Akasha usage.
