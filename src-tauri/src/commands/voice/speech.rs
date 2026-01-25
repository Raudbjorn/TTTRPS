//! Speech Commands
//!
//! Commands for text-to-speech synthesis and audio transcription.

use std::path::Path;
use serde::{Deserialize, Serialize};
use tauri::State;

use crate::commands::AppState;
use crate::core::llm::LLMConfig;
use crate::core::voice::{
    VoiceProviderType, SynthesisRequest, OutputFormat,
};

// ============================================================================
// Types
// ============================================================================

/// Audio data returned from speak command for frontend playback
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpeakResult {
    /// Base64-encoded audio data
    pub audio_data: String,
    /// Audio format (e.g., "wav")
    pub format: String,
}

// ============================================================================
// Speech Commands
// ============================================================================

/// Speak text using configured voice provider
///
/// Uses the VoiceManager from AppState for efficient reuse of the provider connection.
#[tauri::command]
pub async fn speak(
    text: String,
    state: State<'_, AppState>,
) -> Result<Option<SpeakResult>, String> {
    use base64::{engine::general_purpose::STANDARD as BASE64, Engine};

    // Use VoiceManager from state
    let manager = state.voice_manager.read().await;

    // Check if voice is disabled
    if matches!(manager.get_config().provider, VoiceProviderType::Disabled) {
        log::info!("Voice synthesis disabled, skipping speak request");
        return Ok(None);
    }

    // Get the default voice ID from config
    let voice_id = manager.get_config().default_voice_id.clone()
        .unwrap_or_else(|| "default".to_string());

    log::info!("Speaking with provider {:?}, voice_id: '{}', piper_config: {:?}",
        manager.get_config().provider, voice_id, manager.get_config().piper);

    // Synthesize (async)
    let request = SynthesisRequest {
        text,
        voice_id,
        settings: None,
        output_format: OutputFormat::Wav, // Piper outputs WAV natively
    };

    match manager.synthesize(request).await {
        Ok(result) => {
            // Read bytes from file
            let bytes = std::fs::read(&result.audio_path).map_err(|e| e.to_string())?;

            // Return base64-encoded audio for frontend playback
            let audio_data = BASE64.encode(&bytes);
            log::info!("Synthesis complete, returning {} bytes as base64", bytes.len());

            Ok(Some(SpeakResult {
                audio_data,
                format: "wav".to_string(),
            }))
        }
        Err(e) => {
            log::error!("Synthesis failed: {}", e);
            Err(format!("Voice synthesis failed: {}", e))
        }
    }
}

/// Transcribe audio file using OpenAI Whisper
#[tauri::command]
pub async fn transcribe_audio(
    path: String,
    state: State<'_, AppState>,
) -> Result<crate::core::transcription::TranscriptionResult, String> {
    // 1. Check Config for OpenAI API Key
    let api_key = if let Some(config) = state.llm_config.read()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .clone() {
        match config {
            LLMConfig::OpenAI { api_key, .. } => api_key,
            _ => return Err("Transcription requires OpenAI configuration (for now)".to_string()),
        }
    } else {
        return Err("LLM not configured".to_string());
    };

    // Determine effective API key: use credential store if config key is masked or empty
    let effective_key = if api_key.is_empty() || api_key.starts_with('*') {
        // Try getting from credentials if masked/empty
        let creds = state.credentials.get_secret("openai_api_key")
            .map_err(|_| "OpenAI API Key not found/configured".to_string())?;
        if creds.is_empty() {
             return Err("OpenAI API Key is empty".to_string());
        }
        creds
    } else {
        api_key
    };

    // 2. Call Service
    let service = crate::core::transcription::TranscriptionService::new();
    service.transcribe_openai(&effective_key, Path::new(&path))
        .await
        .map_err(|e| e.to_string())
}
