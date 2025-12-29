//! Voice provider detection service
//!
//! Probes local endpoints to detect which TTS services are available.

use reqwest::Client;
use std::time::Duration;
use chrono::Utc;

use super::types::{ProviderStatus, VoiceProviderDetection, VoiceProviderType};

const DETECTION_TIMEOUT: Duration = Duration::from_secs(2);

/// Detect all available voice providers
pub async fn detect_providers() -> VoiceProviderDetection {
    let client = Client::builder()
        .timeout(DETECTION_TIMEOUT)
        .build()
        .unwrap_or_default();

    let providers_to_check = vec![
        VoiceProviderType::Ollama,
        VoiceProviderType::Chatterbox,
        VoiceProviderType::GptSoVits,
        VoiceProviderType::XttsV2,
        VoiceProviderType::FishSpeech,
        VoiceProviderType::Dia,
    ];

    let mut results = Vec::new();

    for provider in providers_to_check {
        let status = check_provider(&client, &provider).await;
        results.push(status);
    }

    VoiceProviderDetection {
        providers: results,
        detected_at: Some(Utc::now().to_rfc3339()),
    }
}

/// Check a single provider's availability
async fn check_provider(client: &Client, provider: &VoiceProviderType) -> ProviderStatus {
    let endpoint = match provider.default_endpoint() {
        Some(ep) => ep.to_string(),
        None => {
            return ProviderStatus {
                provider: provider.clone(),
                available: false,
                endpoint: None,
                version: None,
                error: Some("No default endpoint".to_string()),
            }
        }
    };

    match provider {
        VoiceProviderType::Ollama => check_ollama(client, &endpoint).await,
        VoiceProviderType::Chatterbox => check_chatterbox(client, &endpoint).await,
        VoiceProviderType::GptSoVits => check_gpt_sovits(client, &endpoint).await,
        VoiceProviderType::XttsV2 => check_xtts_v2(client, &endpoint).await,
        VoiceProviderType::FishSpeech => check_fish_speech(client, &endpoint).await,
        VoiceProviderType::Dia => check_dia(client, &endpoint).await,
        _ => ProviderStatus {
            provider: provider.clone(),
            available: false,
            endpoint: Some(endpoint),
            version: None,
            error: Some("Detection not implemented".to_string()),
        },
    }
}

/// Ollama: GET /api/tags or /api/version
async fn check_ollama(client: &Client, base_url: &str) -> ProviderStatus {
    let url = format!("{}/api/version", base_url);

    match client.get(&url).send().await {
        Ok(resp) if resp.status().is_success() => {
            let version = resp
                .json::<serde_json::Value>()
                .await
                .ok()
                .and_then(|v| v.get("version").and_then(|v| v.as_str()).map(String::from));

            ProviderStatus {
                provider: VoiceProviderType::Ollama,
                available: true,
                endpoint: Some(base_url.to_string()),
                version,
                error: None,
            }
        }
        Ok(resp) => ProviderStatus {
            provider: VoiceProviderType::Ollama,
            available: false,
            endpoint: Some(base_url.to_string()),
            version: None,
            error: Some(format!("HTTP {}", resp.status())),
        },
        Err(e) => ProviderStatus {
            provider: VoiceProviderType::Ollama,
            available: false,
            endpoint: Some(base_url.to_string()),
            version: None,
            error: Some(connection_error(&e)),
        },
    }
}

/// Chatterbox: typically exposes a /health or root endpoint
async fn check_chatterbox(client: &Client, base_url: &str) -> ProviderStatus {
    // Try /health first, then root
    for path in ["/health", "/", "/api/health"] {
        let url = format!("{}{}", base_url, path);
        if let Ok(resp) = client.get(&url).send().await {
            if resp.status().is_success() {
                return ProviderStatus {
                    provider: VoiceProviderType::Chatterbox,
                    available: true,
                    endpoint: Some(base_url.to_string()),
                    version: None,
                    error: None,
                };
            }
        }
    }

    // Try connecting to the port at least
    match client.get(base_url).send().await {
        Ok(_) => ProviderStatus {
            provider: VoiceProviderType::Chatterbox,
            available: true,
            endpoint: Some(base_url.to_string()),
            version: None,
            error: None,
        },
        Err(e) => ProviderStatus {
            provider: VoiceProviderType::Chatterbox,
            available: false,
            endpoint: Some(base_url.to_string()),
            version: None,
            error: Some(connection_error(&e)),
        },
    }
}

/// GPT-SoVITS: API at /tts or /
async fn check_gpt_sovits(client: &Client, base_url: &str) -> ProviderStatus {
    // GPT-SoVITS typically responds on root or has a /tts endpoint
    for path in ["/", "/tts", "/api"] {
        let url = format!("{}{}", base_url, path);
        if let Ok(resp) = client.get(&url).send().await {
            // GPT-SoVITS may return 405 on GET but still indicate it's running
            if resp.status().is_success() || resp.status().as_u16() == 405 {
                return ProviderStatus {
                    provider: VoiceProviderType::GptSoVits,
                    available: true,
                    endpoint: Some(base_url.to_string()),
                    version: None,
                    error: None,
                };
            }
        }
    }

    ProviderStatus {
        provider: VoiceProviderType::GptSoVits,
        available: false,
        endpoint: Some(base_url.to_string()),
        version: None,
        error: Some("Service not responding".to_string()),
    }
}

/// XTTS-v2 (Coqui TTS server): /api/tts or /docs
async fn check_xtts_v2(client: &Client, base_url: &str) -> ProviderStatus {
    // Coqui TTS server exposes OpenAPI docs
    for path in ["/docs", "/", "/api/tts"] {
        let url = format!("{}{}", base_url, path);
        if let Ok(resp) = client.get(&url).send().await {
            if resp.status().is_success() {
                return ProviderStatus {
                    provider: VoiceProviderType::XttsV2,
                    available: true,
                    endpoint: Some(base_url.to_string()),
                    version: None,
                    error: None,
                };
            }
        }
    }

    ProviderStatus {
        provider: VoiceProviderType::XttsV2,
        available: false,
        endpoint: Some(base_url.to_string()),
        version: None,
        error: Some("Service not responding".to_string()),
    }
}

/// Fish Speech: /v1/tts or /health
async fn check_fish_speech(client: &Client, base_url: &str) -> ProviderStatus {
    for path in ["/health", "/v1/health", "/"] {
        let url = format!("{}{}", base_url, path);
        if let Ok(resp) = client.get(&url).send().await {
            if resp.status().is_success() {
                return ProviderStatus {
                    provider: VoiceProviderType::FishSpeech,
                    available: true,
                    endpoint: Some(base_url.to_string()),
                    version: None,
                    error: None,
                };
            }
        }
    }

    ProviderStatus {
        provider: VoiceProviderType::FishSpeech,
        available: false,
        endpoint: Some(base_url.to_string()),
        version: None,
        error: Some("Service not responding".to_string()),
    }
}

/// Dia: /health or /api/health
async fn check_dia(client: &Client, base_url: &str) -> ProviderStatus {
    for path in ["/health", "/", "/api/health"] {
        let url = format!("{}{}", base_url, path);
        if let Ok(resp) = client.get(&url).send().await {
            if resp.status().is_success() {
                return ProviderStatus {
                    provider: VoiceProviderType::Dia,
                    available: true,
                    endpoint: Some(base_url.to_string()),
                    version: None,
                    error: None,
                };
            }
        }
    }

    ProviderStatus {
        provider: VoiceProviderType::Dia,
        available: false,
        endpoint: Some(base_url.to_string()),
        version: None,
        error: Some("Service not responding".to_string()),
    }
}

/// Convert reqwest error to user-friendly message
fn connection_error(e: &reqwest::Error) -> String {
    if e.is_connect() {
        "Not running".to_string()
    } else if e.is_timeout() {
        "Timeout".to_string()
    } else {
        format!("Error: {}", e)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_detect_providers_returns_all() {
        let detection = detect_providers().await;
        // Should return status for all local providers
        assert!(detection.providers.len() >= 5);
        assert!(detection.detected_at.is_some());
    }
}
