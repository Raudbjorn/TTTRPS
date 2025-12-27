//! Tauri Commands
//!
//! All Tauri IPC commands exposed to the frontend.

use tauri::State;
use crate::core::llm::{LLMConfig, LLMClient, ChatMessage, ChatRequest};
use crate::core::voice::{VoiceManager, VoiceConfig, SynthesisRequest, OutputFormat, VoiceProviderType, ElevenLabsConfig, OllamaConfig};
use crate::ingestion::pdf_parser;
use crate::ingestion::character_gen::{Character, CharacterGenerator, TTRPGGenre};
use crate::core::models::Campaign;
use std::sync::Mutex;
use std::path::Path;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use crate::core::vector_store::{VectorStore, VectorStoreConfig};
use crate::core::embedding_pipeline::{EmbeddingPipeline, PipelineConfig};
use std::sync::Arc;

// ============================================================================
// Application State
// ============================================================================

pub struct AppState {
    pub llm_client: Mutex<Option<LLMClient>>,
    pub llm_config: Mutex<Option<LLMConfig>>,
    pub vector_store: Arc<VectorStore>,
}

impl Default for AppState {
    fn default() -> Self {
         // This default is not really used as we initialize with VectorStore in main
         // But to satisfy Default trait if needed (though we likely won't rely on it)
         // We can't easily create a default VectorStore here without async
         panic!("AppState must be initialized with VectorStore");
    }
}

pub struct AppStateInit {
    pub llm_client: Mutex<Option<LLMClient>>,
    pub llm_config: Mutex<Option<LLMConfig>>,
    pub vector_store: Arc<VectorStore>,
}

impl AppStateInit {
    pub fn new(vector_store: VectorStore) -> Self {
        Self {
            llm_client: Mutex::new(None),
            llm_config: Mutex::new(None),
            vector_store: Arc::new(vector_store),
        }
    }
}

// ============================================================================
// Request/Response Types
// ============================================================================

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequestPayload {
    pub message: String,
    pub system_prompt: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponsePayload {
    pub content: String,
    pub model: String,
    pub input_tokens: Option<u32>,
    pub output_tokens: Option<u32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LLMSettings {
    pub provider: String,
    pub api_key: Option<String>,
    pub host: Option<String>,
    pub model: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthStatus {
    pub provider: String,
    pub healthy: bool,
    pub message: String,
}

// ============================================================================
// LLM Commands
// ============================================================================

#[tauri::command]
pub fn configure_llm(
    settings: LLMSettings,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let config = match settings.provider.as_str() {
        "ollama" => LLMConfig::Ollama {
            host: settings.host.unwrap_or_else(|| "http://localhost:11434".to_string()),
            model: settings.model,
            embedding_model: Some("nomic-embed-text".to_string()),
        },
        "claude" => LLMConfig::Claude {
            api_key: settings.api_key.ok_or("Claude requires an API key")?,
            model: settings.model,
            max_tokens: 4096,
        },
        "gemini" => LLMConfig::Gemini {
            api_key: settings.api_key.ok_or("Gemini requires an API key")?,
            model: settings.model,
        },
        _ => return Err(format!("Unknown provider: {}", settings.provider)),
    };

    let client = LLMClient::new(config.clone());
    let provider_name = client.provider_name().to_string();

    // Store both config and client
    {
        let mut config_guard = state.llm_config.lock().map_err(|e| e.to_string())?;
        *config_guard = Some(config);
    }
    {
        let mut client_guard = state.llm_client.lock().map_err(|e| e.to_string())?;
        *client_guard = Some(client);
    }

    Ok(format!("Configured {} provider successfully", provider_name))
}

#[tauri::command]
pub async fn chat(
    payload: ChatRequestPayload,
    state: State<'_, AppState>,
) -> Result<ChatResponsePayload, String> {
    // Get config and create client in a sync block to avoid holding lock across await
    let config = {
        let config_guard = state.llm_config.lock().map_err(|e| e.to_string())?;
        config_guard.clone().ok_or("LLM not configured. Please configure in Settings.")?
    };

    let client = LLMClient::new(config);

    let request = ChatRequest::new(vec![ChatMessage::user(&payload.message)])
        .with_system(payload.system_prompt.unwrap_or_else(|| {
            "You are a helpful TTRPG Game Master assistant. Help the user with their tabletop RPG questions, \
             provide rules clarifications, generate content, and assist with running their campaign.".to_string()
        }));

    let response = client.chat(request).await.map_err(|e| e.to_string())?;

    Ok(ChatResponsePayload {
        content: response.content,
        model: response.model,
        input_tokens: response.usage.as_ref().map(|u| u.input_tokens),
        output_tokens: response.usage.as_ref().map(|u| u.output_tokens),
    })
}

#[tauri::command]
pub async fn check_llm_health(state: State<'_, AppState>) -> Result<HealthStatus, String> {
    // Get config in a sync block to avoid holding lock across await
    let config_opt = {
        let config_guard = state.llm_config.lock().map_err(|e| e.to_string())?;
        config_guard.clone()
    };

    match config_opt {
        Some(config) => {
            let client = LLMClient::new(config);
            let provider = client.provider_name().to_string();

            match client.health_check().await {
                Ok(healthy) => Ok(HealthStatus {
                    provider: provider.clone(),
                    healthy,
                    message: if healthy {
                        format!("{} is available", provider)
                    } else {
                        format!("{} is not responding", provider)
                    },
                }),
                Err(e) => Ok(HealthStatus {
                    provider,
                    healthy: false,
                    message: e.to_string(),
                }),
            }
        }
        None => Ok(HealthStatus {
            provider: "none".to_string(),
            healthy: false,
            message: "No LLM configured".to_string(),
        }),
    }
}

#[tauri::command]
pub fn get_llm_config(state: State<'_, AppState>) -> Result<Option<LLMSettings>, String> {
    let config_guard = state.llm_config.lock().map_err(|e| e.to_string())?;

    Ok(config_guard.as_ref().map(|config| match config {
        LLMConfig::Ollama { host, model, .. } => LLMSettings {
            provider: "ollama".to_string(),
            api_key: None,
            host: Some(host.clone()),
            model: model.clone(),
        },
        LLMConfig::Claude { model, .. } => LLMSettings {
            provider: "claude".to_string(),
            api_key: Some("********".to_string()), // Mask the key
            host: None,
            model: model.clone(),
        },
        LLMConfig::Gemini { model, .. } => LLMSettings {
            provider: "gemini".to_string(),
            api_key: Some("********".to_string()), // Mask the key
            host: None,
            model: model.clone(),
        },
    }))
}

// ============================================================================
// Document Ingestion Commands
// ============================================================================

#[tauri::command]
pub async fn ingest_document(
    path: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let path_obj = Path::new(&path);
    if !path_obj.exists() {
        return Err(format!("File not found: {}", path));
    }

    // Get LLM config
    let llm_config = {
        let guard = state.llm_config.lock().map_err(|e| e.to_string())?;
        guard.clone().ok_or("LLM not configured. Please configure in Settings.")?
    };

    // Create pipeline
    // Note: VectorStore clone is cheap (Arc internally or we wrap it)
    // Actually VectorStore struct in vector_store.rs seems to hold Connection which might be cloneable?
    // Let's check vector_store.rs. It has `conn: Connection` which is lancedb::connection::Connection.
    // lancedb Connection is usually cheaply cloneable or we can wrap VectorStore in Arc.
    // In AppState we wrapped it in Arc.

    // We need to create a NEW VectorStore instance or pass the Arc?
    // EmbeddingPipeline takes VectorStore by value.
    // We should probably change EmbeddingPipeline to take Arc<VectorStore> or clone the internal connection if possible.
    // Checking vector_store.rs... `conn` is `lancedb::connection::Connection`.
    // lancedb::Connection seems to be a wrapper around an inner Arc, so it might be cloneable.
    // But `VectorStore` struct definition doesn't derive Clone.
    // We will assume for now we need to change EmbeddingPipeline or perform a workaround.
    // Workaround: Modify EmbeddingPipeline to accept a potentially shared VectorStore,
    // OR just instantiate a new VectorStore connection here since it's just a connection to DB.

    // Let's create a fresh VectorStore connection for the pipeline to avoid ownership issues for now,
    // assuming VectorStore::new is relatively cheap (just opening DB).
    let vector_store = VectorStore::new(VectorStoreConfig::default()).await
        .map_err(|e| format!("Failed to connect to vector store: {}", e))?;

    let pipeline = EmbeddingPipeline::new(
        llm_config,
        vector_store,
        PipelineConfig::default(),
    );

    let result = pipeline.process_file(path_obj, "user_upload").await
        .map_err(|e| format!("Ingestion failed: {}", e))?;

    Ok(format!(
        "Ingested {}: {}/{} chunks stored ({} failed)",
        result.source, result.stored_chunks, result.total_chunks, result.failed_chunks
    ))
}

// ============================================================================
// Search Commands
// ============================================================================

#[tauri::command]
pub async fn search(
    query: String,
    state: State<'_, AppState>,
) -> Result<Vec<String>, String> {
    // 1. Get embedding for query
    let (client, config) = {
        let client_guard = state.llm_client.lock().map_err(|e| e.to_string())?;
        let config_guard = state.llm_config.lock().map_err(|e| e.to_string())?;

        // We need both client and config info (embedded dim)
        let client = client_guard.as_ref().ok_or("LLM client not initialized")?;
        // We can't clone client easily if it doesn't derive Clone?
        // reqwest::Client is cloneable. LLMClient struct definition?
        // Let's check LLMClient in llm.rs...
        // `pub struct LLMClient { client: Client, config: LLMConfig }`
        // It doesn't derive Clone. We might need to construct a new one or make it Clone.
        // For now, let's construct a temp one from config, it's safer.
        let config = config_guard.clone().ok_or("LLM not configured")?;
        (LLMClient::new(config.clone()), config)
    };

    let embedding_resp = client.embed(&query).await
        .map_err(|e| format!("Failed to generate embedding: {}", e))?;

    // 2. Search vector store
    let results = state.vector_store.search(
        &embedding_resp.embedding,
        5, // limit
        None, // no source filter
    ).await.map_err(|e| format!("Search failed: {}", e))?;

    // 3. Format results
    let formatted: Vec<String> = results.into_iter()
        .map(|r| format!(
            "[{:.2}] {}...\n(Source: {} p.{})",
            r.score,
            r.document.content.chars().take(100).collect::<String>(),
            r.document.source,
            r.document.page_number.unwrap_or(0)
        ))
        .collect();

    Ok(formatted)
}

// ============================================================================
// Character Generation Commands
// ============================================================================

#[tauri::command]
pub fn generate_character(
    system: String,
    level: u32,
    genre: Option<String>,
) -> Result<Character, String> {
    let genre_enum = match genre.as_deref() {
        Some("scifi") | Some("SciFi") => Some(TTRPGGenre::SciFi),
        Some("cyberpunk") | Some("Cyberpunk") => Some(TTRPGGenre::Cyberpunk),
        Some("horror") | Some("Horror") | Some("CosmicHorror") => Some(TTRPGGenre::CosmicHorror),
        Some("postapoc") | Some("PostApocalyptic") => Some(TTRPGGenre::PostApocalyptic),
        Some("superhero") | Some("Superhero") => Some(TTRPGGenre::Superhero),
        Some("western") | Some("Western") => Some(TTRPGGenre::Western),
        _ => Some(TTRPGGenre::Fantasy),
    };

    let character = CharacterGenerator::generate(&system, level as i32, genre_enum);
    Ok(character)
}

// ============================================================================
// Campaign Commands
// ============================================================================

#[tauri::command]
pub fn list_campaigns() -> Result<Vec<Campaign>, String> {
    // Placeholder - will be implemented with SQLite
    Ok(vec![])
}

#[tauri::command]
pub fn create_campaign(
    name: String,
    system: String,
    description: Option<String>,
) -> Result<Campaign, String> {
    Ok(Campaign {
        id: uuid::Uuid::new_v4().to_string(),
        name,
        system,
        description,
        current_date: "Session 1".to_string(),
        notes: vec![],
        created_at: Utc::now().to_rfc3339(),
        updated_at: Utc::now().to_rfc3339(),
        settings: Default::default(),
    })
}

#[tauri::command]
pub fn get_campaign(id: String) -> Result<Option<Campaign>, String> {
    // Placeholder - will be implemented with SQLite
    let _ = id;
    Ok(None)
}

#[tauri::command]
pub fn delete_campaign(id: String) -> Result<bool, String> {
    // Placeholder - will be implemented with SQLite
    let _ = id;
    Ok(true)
}

// ============================================================================
// Voice Commands
// ============================================================================

#[tauri::command]
pub async fn speak(text: String, state: State<'_, AppState>) -> Result<(), String> {
    // 1. Determine config
    let config = {
        let config_guard = state.llm_config.lock().map_err(|e| e.to_string())?;

        if let Some(c) = config_guard.as_ref() {
            match c {
                LLMConfig::Ollama { host, .. } => VoiceConfig {
                    provider: VoiceProviderType::Ollama,
                    ollama: Some(OllamaConfig {
                        base_url: host.clone(),
                        model: "bark".to_string(), // Default placeholder
                    }),
                    ..Default::default()
                },
                LLMConfig::Claude { api_key, .. } => VoiceConfig {
                    provider: VoiceProviderType::ElevenLabs,
                    elevenlabs: Some(ElevenLabsConfig {
                        api_key: api_key.clone(),
                        model_id: None,
                    }),
                    ..Default::default()
                },
                LLMConfig::Gemini { .. } => VoiceConfig::default(),
            }
        } else {
             VoiceConfig::default()
        }
    };

    let manager = VoiceManager::new(config);

    // 2. Synthesize (async)
    let request = SynthesisRequest {
        text,
        voice_id: "default".to_string(),
        settings: None,
        output_format: OutputFormat::Mp3,
    };

    if let Ok(result) = manager.synthesize(request).await {
         // Read bytes from file (or implementation could return bytes directly if we changed it, but manager returns result with path)
         let bytes = std::fs::read(&result.audio_path).map_err(|e| e.to_string())?;

         // 3. Play
         tauri::async_runtime::spawn_blocking(move || {
             if let Err(e) = manager.play_audio(bytes) {
                 log::error!("Playback failed: {}", e);
             }
         }).await.map_err(|e| e.to_string())?;

         Ok(())
    } else {
        log::info!("Speak request received (synthesis skipped/failed)");
        Ok(())
    }
}
