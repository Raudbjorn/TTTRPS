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

/// Transcribe audio file using available transcription provider
///
/// Supports OpenAI Whisper and Groq Whisper. Will use the first available provider
/// based on configured API keys.
#[tauri::command]
pub async fn transcribe_audio(
    path: String,
    state: State<'_, AppState>,
) -> Result<crate::core::transcription::TranscriptionResult, String> {
    use crate::core::transcription::{TranscriptionManagerBuilder, TranscriptionProviderType};

    // Try to get API keys from credentials store
    let openai_key = state.credentials.get_secret("openai_api_key").ok();
    let groq_key = state.credentials.get_secret("groq_api_key").ok();

    // Fall back to LLM config if credentials not available
    let openai_key = openai_key.or_else(|| {
        state.llm_config.read()
            .ok()
            .and_then(|guard| guard.clone())
            .and_then(|config| match config {
                LLMConfig::OpenAI { api_key, .. } if !api_key.is_empty() && !api_key.starts_with('*') => Some(api_key),
                _ => None,
            })
    });

    let groq_key = groq_key.or_else(|| {
        state.llm_config.read()
            .ok()
            .and_then(|guard| guard.clone())
            .and_then(|config| match config {
                LLMConfig::Groq { api_key, .. } if !api_key.is_empty() && !api_key.starts_with('*') => Some(api_key),
                _ => None,
            })
    });

    // Build transcription manager with available providers
    let mut builder = TranscriptionManagerBuilder::new();

    if let Some(key) = openai_key {
        builder = builder.with_openai(key);
    }
    if let Some(key) = groq_key {
        builder = builder.with_groq(key);
    }

    // Default to OpenAI if available, otherwise Groq
    builder = builder.default_provider(TranscriptionProviderType::OpenAI);

    let manager = builder.build();

    if manager.available_providers().is_empty() {
        return Err("No transcription providers available. Configure OpenAI or Groq API keys.".to_string());
    }

    manager.transcribe(Path::new(&path))
        .await
        .map_err(|e| e.to_string())
}
