# Design: Unified System Settings Persistence

## 1. Architecture

### 1.1 Storage Layer (Meilisearch)
- **Index**: `sys`
- **Primary Key**: `id`
- **Document**: A single document with `id: "settings"` containing logical groups of configuration.

### 1.2 Backend Service (`SettingsManager`)
- **Location**: `src-tauri/src/core/settings/manager.rs`
- **Responsibility**:
    - Manage the application's configuration state.
    - Handle initialization (fetch from Meilisearch, or seed defaults).
    - Expose methods to update specific sections (LLM, Extraction, etc.).
    - Broadcast changes (optional, using Tauri events).

### 1.3 Data Model
A master struct `UnifiedSettings` will aggregate all sub-settings.

```rust
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct UnifiedSettings {
    pub id: String, // Always "settings"
    pub llm: LLMSettings,
    pub extraction: ExtractionSettings,
    pub voice: VoiceConfig,
    pub ui: UISettings,
}
```

### 1.4 API Endpoints (Commands)
- `get_all_settings() -> UnifiedSettings`
- `update_llm_settings(settings: LLMSettings) -> Result<()>`
- `update_extraction_settings(settings: ExtractionSettings) -> Result<()>`
- `get_settings_metadata() -> SettingsMetadata` (For legal values/descriptions)

## 2. Detailed Data Structures

### 2.1 LLM Settings
Existing `LLMSettings` struct.
- `provider`: String (Enum representation)
- `api_key`: String (Note: Consider security. For now, we may store ref or strict local persistence. If stored in Meilisearch, it's plaintext locally. Acceptable for single-user local app?) -> *Decision: Store in Meilisearch for simplicity, user owns data.*
- `model`: String

### 2.2 Extraction Settings
Existing `ExtractionSettings` struct.
- `ocr_enabled`, `use_akasha`, etc.

### 2.3 Legal Values (Metadata)
To support exportable "legal values", we will implement a `SettingsMetadata` structure that describes valid options for enums.

```rust
pub struct SettingFieldMetadata {
    pub key: String,
    pub label: String,
    pub type: String, // "boolean", "string", "enum", "number"
    pub options: Option<Vec<String>>, // For enums
    pub min: Option<f64>,
    pub max: Option<f64>,
}
```

## 3. Initialization Flow
1. **App Start**: `SettingsManager::new()` called.
2. **Fetch**: Query Meilisearch `sys` index for `id: "settings"`.
3. **Not Found**:
    - Instantiate `UnifiedSettings::default()`.
    - Function `save_to_db()` called to index it.
4. **Found**:
    - Deserialize into `UnifiedSettings`.
    - Apply to global state (Tauri State).

## 4. Exportability
- `export_settings() -> String` (JSON dump of `UnifiedSettings`)
- `import_settings(json: String) -> Result<()>` (Validate and Overwrite)

## 5. Security (API Keys)
- Storing API keys in Meilisearch (local DB) is semi-secure (file permissions).
- Alternative: Keep API keys in system keyring, store everything else in Meilisearch.
- *Decision for MVP*: Store in Meilisearch. Future: Migrate sensitive keys to OS Keyring.

