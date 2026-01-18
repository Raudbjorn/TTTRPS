# Tasks: System Settings Persistence

## Backend (Rust/Tauri)

- [ ] 1. Core Infrastructure
    - [ ] 1.1 Create `SettingsManager` struct in `src-tauri/src/core/settings/mod.rs` (or similar).
    - [ ] 1.2 Implement `UnifiedSettings` struct aggregating `LLMSettings`, `ExtractionSettings`, `VoiceConfig`.
    - [ ] 1.3 Implement `load()` logic:
        - Fetch from Meilisearch `sys` index.
        - Default fallback if missing.
    - [ ] 1.4 Implement `save()` logic:
        - Index document to Meilisearch `sys` index.

- [ ] 2. Migration/Integration
    - [ ] 2.1 Update `ExtractionSettings` handling:
        - Modify `get_extraction_settings` command to pull from `UnifiedSettings`.
        - Modify `save_extraction_settings` command to update `UnifiedSettings` and trigger persist.
    - [ ] 2.2 Update `LLMSettings` handling:
        - Similar usage in `commands.rs`.
    - [ ] 2.3 Update `VoiceConfig` handling:
        - Similar usage.

- [ ] 3. Metadata & Exports
    - [ ] 3.1 Implement `SettingsMetadata` generation (legal values, types).
    - [ ] 3.2 Create `get_settings_metadata` command.
    - [ ] 3.3 Create `export_settings` and `import_settings` commands.

## Frontend (TypeScript/React)

- [ ] 4. Bindings & API
    - [ ] 4.1 Update bindings to include `UnifiedSettings`, `SettingsMetadata`.

- [ ] 5. State Management
    - [ ] 5.1 Create `SettingsContext` or global store (if distinct from current separate stores).
    - [ ] 5.2 Update initialization logic (`App.tsx` or `main.tsx`) to fetch initial settings.

- [ ] 6. UI Updates
    - [ ] 6.1 Create unified "Settings" export/import UI (optional, for "Exportability" requirement).
    - [ ] 6.2 Ensure all settings pages read/write via the new unified API (or existing APIs backed by new manager).

## Verification

- [ ] 7. Testing
    - [ ] 7.1 Verify startup loads defaults (empty DB).
    - [ ] 7.2 Verify changes persist after restart.
    - [ ] 7.3 Verify export produces valid JSON.
