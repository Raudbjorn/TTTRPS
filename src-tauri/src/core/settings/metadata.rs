use serde::Serialize;

#[derive(Serialize)]
pub struct SettingFieldMetadata {
    pub key: String,
    pub label: String,
    #[serde(rename = "type")]
    pub type_: String, // "boolean", "string", "enum", "number", "password"
    pub options: Option<Vec<String>>,
    pub description: Option<String>,
    pub min: Option<f64>,
    pub max: Option<f64>,
}

#[derive(Serialize)]
pub struct UnifiedSettingsMetadata {
    pub llm: Vec<SettingFieldMetadata>,
    pub extraction: Vec<SettingFieldMetadata>,
    pub voice: Vec<SettingFieldMetadata>,
}

impl UnifiedSettingsMetadata {
    pub fn generate() -> Self {
        Self {
            llm: generate_llm_metadata(),
            extraction: generate_extraction_metadata(),
            voice: generate_voice_metadata(),
        }
    }
}

fn generate_llm_metadata() -> Vec<SettingFieldMetadata> {
    vec![
        SettingFieldMetadata {
            key: "provider".to_string(),
            label: "Provider".to_string(),
            type_: "enum".to_string(),
            options: Some(vec![
                "ollama", "openai", "claude", "gemini", "openrouter",
                "mistral", "groq", "together", "cohere", "deepseek",
                "claude-desktop", "claude-code", "gemini-cli"
            ].into_iter().map(String::from).collect()),
            description: Some("AI Service Provider".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "model".to_string(),
            label: "Model".to_string(),
            type_: "string".to_string(),
            options: None,
            description: Some("Model identifier (e.g., gpt-4o, claude-3-5-sonnet)".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "api_key".to_string(),
            label: "API Key".to_string(),
            type_: "password".to_string(),
            options: None,
            description: Some("API Key for the selected provider (stored securely)".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "host".to_string(),
            label: "Host URL".to_string(),
            type_: "string".to_string(),
            options: None,
            description: Some("Custom host URL (for Ollama or compatible endpoints)".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "embedding_model".to_string(),
            label: "Embedding Model".to_string(),
            type_: "string".to_string(),
            options: None,
            description: Some("Model used for generating embeddings".to_string()),
            min: None, max: None,
        },
    ]
}

fn generate_extraction_metadata() -> Vec<SettingFieldMetadata> {
    vec![
        // Chunking Strategy
        SettingFieldMetadata {
            key: "chunking_strategy".to_string(),
            label: "Chunking Strategy".to_string(),
            type_: "enum".to_string(),
            options: Some(vec![
                "recursive", "hierarchical", "semantic", "hybrid"
            ].into_iter().map(String::from).collect()),
            description: Some("Method used to split documents into chunks".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "chunk_size".to_string(),
            label: "Chunk Size".to_string(),
            type_: "number".to_string(),
            options: None,
            description: Some("Target size of each chunk in tokens/characters".to_string()),
            min: Some(128.0), max: Some(8192.0),
        },
        SettingFieldMetadata {
            key: "chunk_overlap".to_string(),
            label: "Chunk Overlap".to_string(),
            type_: "number".to_string(),
            options: None,
            description: Some("Overlap between consecutive chunks".to_string()),
            min: Some(0.0), max: Some(1024.0),
        },
        // OCR & PDF
        SettingFieldMetadata {
            key: "use_akasha".to_string(),
            label: "Enable Akasha Intelligence (PDFs)".to_string(),
            type_: "boolean".to_string(),
            options: None,
            description: Some("Use Akasha engine for PDF processing".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "ocr_enabled".to_string(),
            label: "Enable OCR".to_string(),
            type_: "boolean".to_string(),
            options: None,
            description: Some("Perform OCR on scanned documents".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "ocr_language".to_string(),
            label: "OCR Language".to_string(),
            type_: "string".to_string(),
            options: None,
            description: Some("Language code for OCR (e.g., eng, fra)".to_string()),
            min: None, max: None,
        },
    ]
}

fn generate_voice_metadata() -> Vec<SettingFieldMetadata> {
    vec![
        SettingFieldMetadata {
            key: "provider".to_string(),
            label: "TTS Provider".to_string(),
            type_: "enum".to_string(),
            options: Some(vec![
                "system", "piper", "openai", "elevenlabs"
            ].into_iter().map(String::from).collect()),
            description: Some("Text-to-Speech Engine".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "voice_id".to_string(),
            label: "Voice ID".to_string(),
            type_: "string".to_string(),
            options: None,
            description: Some("Identifier for the selected voice".to_string()),
            min: None, max: None,
        },
        SettingFieldMetadata {
            key: "speed".to_string(),
            label: "Speech Speed".to_string(),
            type_: "number".to_string(),
            options: None,
            description: Some("Speed multiplier for speech playback".to_string()),
            min: Some(0.5), max: Some(2.0),
        },
        SettingFieldMetadata {
            key: "volume".to_string(),
            label: "Volume".to_string(),
            type_: "number".to_string(),
            options: None,
            description: Some("Master volume for TTS".to_string()),
            min: Some(0.0), max: Some(1.0),
        },
    ]
}
