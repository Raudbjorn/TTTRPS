# Requirements: Unified System Settings Persistence

## 1. Overview
The application requires a unified, persistent settings management system. Currently, settings are scattered or not persistently stored in a central location. This feature aims to consolidate all application settings (LLM, Extraction, Voice, etc.) into a single persistent store using Meilisearch, ensuring settings are saved immediately upon change and loaded upon application startup.

## 2. Goals
- **Persistence**: All settings must be saved to the `sys` index in Meilisearch.
- **Auto-Save**: Changes to settings must be persisted immediately.
- **Startup Config**: The application must configure itself using values from Meilisearch on startup.
- **Exportability**: Settings schema, values, and legal values must be structured and exportable.
- **Centralization**: Provide a single source of truth for all system configurations.

## 3. User Stories
- **As a User**, I want my configuration (e.g., LLM provider, extraction rules) to be remembered between sessions so I don't have to re-configure them every time.
- **As a User**, I want my changes to be saved automatically as I make them, without needing to manually click "Save".
- **As a Developer**, I want to be able to export the current settings configuration for debugging or sharing.
- **As a System**, I want to default to sensible values if no settings are found in the persistence store.

## 4. Functional Requirements
- **FR1 - Storage Backend**: Use Meilisearch as the storage engine.
    - Index: `sys`
    - Document ID: `settings` (or unique singleton ID)
- **FR2 - Schema**: Define a comprehensive JSON schema covering:
    - `LLMSettings`: Provider, model, API keys (securely handled or ref'd), parameters.
    - `ExtractionSettings`: OCR, Akasha, chunking strategies.
    - `VoiceConfig`: TTS provider, voice selections.
    - `SystemSettings`: Theme, paths, etc.
- **FR3 - CRUD Operations**: Implement backend API for:
    - `get_all_settings()`
    - `update_setting(key, value)` or `update_settings_group(group_struct)`
    - `reset_to_defaults()`
- **FR4 - Validation**: Ensure settings values are validated against legal values (enums, ranges) before persistence.
- **FR5 - Initialization**: On app launch, attempt to fetch settings. If missing, seed with defaults and persist them.

## 5. Non-Functional Requirements
- **NFR1 - Latency**: Settings retrieval should not block application startup significantly.
- **NFR2 - Robustness**: Failure to read settings (e.g., Meilisearch down) should fall back to in-memory defaults with a warning, not crash.
- **NFR3 - Metadata**: Settings metadata (description, legal values) should be available to the frontend to auto-generate UI.
