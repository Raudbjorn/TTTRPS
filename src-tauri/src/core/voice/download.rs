use std::path::{Path, PathBuf};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::io::AsyncWriteExt;
use tracing::{debug, info};

const PIPER_HF_BASE: &str = "https://huggingface.co/rhasspy/piper-voices/resolve/main";
const PIPER_VOICES_JSON: &str = "https://huggingface.co/rhasspy/piper-voices/raw/main/voices.json";

#[derive(Error, Debug)]
pub enum DownloadError {
    #[error("Network error: {0}")]
    Network(#[from] reqwest::Error),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Voice not found: {0}")]
    VoiceNotFound(String),

    #[error("Parse error: {0}")]
    Parse(String),

    #[error("Download cancelled")]
    Cancelled,
}

pub type DownloadResult<T> = std::result::Result<T, DownloadError>;

/// Available Piper voice from the Hugging Face repository
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AvailablePiperVoice {
    pub key: String,
    pub name: String,
    pub language: PiperLanguage,
    pub quality: String,
    pub num_speakers: u32,
    pub sample_rate: u32,
    pub files: PiperVoiceFiles,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PiperLanguage {
    pub code: String,
    pub family: String,
    pub region: String,
    pub name_native: String,
    pub name_english: String,
    pub country_english: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PiperVoiceFiles {
    pub model: PiperFileInfo,
    pub config: PiperFileInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PiperFileInfo {
    pub size_bytes: u64,
    pub md5_digest: String,
}

/// Download progress callback
pub type ProgressCallback = Box<dyn Fn(u64, u64) + Send + Sync>;

/// Parsed components of a Piper voice key
#[derive(Debug, Clone)]
struct ParsedVoiceKey {
    lang_region: String,  // e.g., "en_US"
    voice_name: String,   // e.g., "lessac"
    quality: String,      // e.g., "medium"
}

impl ParsedVoiceKey {
    /// Parse a voice key like "en_US-lessac-medium"
    fn parse(voice_key: &str, default_quality: Option<&str>) -> Result<Self, DownloadError> {
        let parts: Vec<&str> = voice_key.split('-').collect();
        if parts.len() < 2 {
            return Err(DownloadError::VoiceNotFound(voice_key.to_string()));
        }

        let quality = default_quality
            .or_else(|| parts.get(2).filter(|s| !s.is_empty()).copied())
            .unwrap_or("medium")
            .to_string();

        Ok(Self {
            lang_region: parts[0].to_string(),
            voice_name: parts[1].to_string(),
            quality,
        })
    }

    /// Get the language code (e.g., "en" from "en_US")
    fn lang_code(&self) -> &str {
        self.lang_region.split('_').next().unwrap_or("en")
    }

    /// Construct the HuggingFace path for this voice
    fn hf_base_path(&self) -> String {
        format!(
            "{}/{}/{}/{}",
            self.lang_code(),
            self.lang_region,
            self.voice_name,
            self.quality
        )
    }

    /// Get the model filename (e.g., "en_US-lessac-medium.onnx")
    fn model_filename(&self) -> String {
        format!("{}-{}-{}.onnx", self.lang_region, self.voice_name, self.quality)
    }

    /// Get the config filename (e.g., "en_US-lessac-medium.onnx.json")
    fn config_filename(&self) -> String {
        format!("{}.json", self.model_filename())
    }
}

/// Voice downloader for Piper models from Hugging Face
pub struct VoiceDownloader {
    client: Client,
    models_dir: PathBuf,
}

impl VoiceDownloader {
    pub fn new(models_dir: PathBuf) -> Self {
        Self {
            client: Client::builder()
                .timeout(std::time::Duration::from_secs(300))
                .build()
                .expect("Failed to create HTTP client"),
            models_dir,
        }
    }

    /// List all available Piper voices from Hugging Face
    pub async fn list_available_voices(&self) -> DownloadResult<Vec<AvailablePiperVoice>> {
        info!("Fetching available Piper voices from Hugging Face");

        let response = self.client.get(PIPER_VOICES_JSON).send().await?;

        if !response.status().is_success() {
            return Err(DownloadError::Network(
                response.error_for_status().unwrap_err()
            ));
        }

        let json: serde_json::Value = response.json().await?;

        let mut voices = Vec::new();

        // Parse the voices.json structure
        if let Some(obj) = json.as_object() {
            for (key, value) in obj {
                if let Ok(voice) = self.parse_voice_entry(key, value) {
                    voices.push(voice);
                }
            }
        }

        info!(count = voices.len(), "Found available Piper voices");
        Ok(voices)
    }

    fn parse_voice_entry(&self, key: &str, value: &serde_json::Value) -> DownloadResult<AvailablePiperVoice> {
        let language = value.get("language")
            .ok_or_else(|| DownloadError::Parse("Missing language".to_string()))?;

        let files = value.get("files")
            .and_then(|f| f.as_object())
            .ok_or_else(|| DownloadError::Parse("Missing files".to_string()))?;

        // Get the first available quality variant
        let (quality, file_info) = files.iter().next()
            .ok_or_else(|| DownloadError::Parse("No quality variants".to_string()))?;

        let model_file = file_info.get("model")
            .ok_or_else(|| DownloadError::Parse("Missing model file info".to_string()))?;
        let config_file = file_info.get("config")
            .ok_or_else(|| DownloadError::Parse("Missing config file info".to_string()))?;

        Ok(AvailablePiperVoice {
            key: key.to_string(),
            name: value.get("name")
                .and_then(|n| n.as_str())
                .unwrap_or(key)
                .to_string(),
            language: PiperLanguage {
                code: language.get("code").and_then(|c| c.as_str()).unwrap_or("").to_string(),
                family: language.get("family").and_then(|f| f.as_str()).unwrap_or("").to_string(),
                region: language.get("region").and_then(|r| r.as_str()).unwrap_or("").to_string(),
                name_native: language.get("name_native").and_then(|n| n.as_str()).unwrap_or("").to_string(),
                name_english: language.get("name_english").and_then(|n| n.as_str()).unwrap_or("").to_string(),
                country_english: language.get("country_english").and_then(|c| c.as_str()).unwrap_or("").to_string(),
            },
            quality: quality.clone(),
            num_speakers: value.get("num_speakers").and_then(|n| n.as_u64()).unwrap_or(1) as u32,
            sample_rate: file_info.get("sample_rate").and_then(|s| s.as_u64()).unwrap_or(22050) as u32,
            files: PiperVoiceFiles {
                model: PiperFileInfo {
                    size_bytes: model_file.get("size_bytes").and_then(|s| s.as_u64()).unwrap_or(0),
                    md5_digest: model_file.get("md5_digest").and_then(|m| m.as_str()).unwrap_or("").to_string(),
                },
                config: PiperFileInfo {
                    size_bytes: config_file.get("size_bytes").and_then(|s| s.as_u64()).unwrap_or(0),
                    md5_digest: config_file.get("md5_digest").and_then(|m| m.as_str()).unwrap_or("").to_string(),
                },
            },
        })
    }

    /// Download a Piper voice by key (e.g., "en_US-lessac-medium")
    pub async fn download_voice(
        &self,
        voice_key: &str,
        quality: Option<&str>,
        progress: Option<ProgressCallback>,
    ) -> DownloadResult<PathBuf> {
        info!(voice = voice_key, "Downloading Piper voice");

        // Ensure models directory exists
        tokio::fs::create_dir_all(&self.models_dir).await?;

        // Parse voice key using helper struct
        let parsed = ParsedVoiceKey::parse(voice_key, quality)?;

        // Construct URLs using parsed components
        let model_url = format!(
            "{}/{}/{}",
            PIPER_HF_BASE,
            parsed.hf_base_path(),
            parsed.model_filename()
        );
        let config_url = format!(
            "{}/{}/{}",
            PIPER_HF_BASE,
            parsed.hf_base_path(),
            parsed.config_filename()
        );

        let model_path = self.models_dir.join(parsed.model_filename());
        let config_path = self.models_dir.join(parsed.config_filename());

        // Download model file
        debug!(url = %model_url, "Downloading model file");
        self.download_file(&model_url, &model_path, progress.as_ref()).await?;

        // Download config file
        debug!(url = %config_url, "Downloading config file");
        self.download_file(&config_url, &config_path, None).await?;

        info!(path = ?model_path, "Voice download complete");
        Ok(model_path)
    }

    async fn download_file(
        &self,
        url: &str,
        dest: &Path,
        progress: Option<&ProgressCallback>,
    ) -> DownloadResult<()> {
        let response = self.client.get(url).send().await?;

        if !response.status().is_success() {
            return Err(DownloadError::Network(
                response.error_for_status().unwrap_err()
            ));
        }

        let total_size = response.content_length().unwrap_or(0);
        let mut downloaded: u64 = 0;

        let mut file = tokio::fs::File::create(dest).await?;
        let mut stream = response.bytes_stream();

        use futures_util::StreamExt;
        while let Some(chunk) = stream.next().await {
            let chunk = chunk?;
            file.write_all(&chunk).await?;
            downloaded += chunk.len() as u64;

            if let Some(ref cb) = progress {
                cb(downloaded, total_size);
            }
        }

        file.flush().await?;
        Ok(())
    }

    /// Check if a voice is already downloaded
    pub fn is_voice_downloaded(&self, voice_key: &str) -> bool {
        match ParsedVoiceKey::parse(voice_key, None) {
            Ok(parsed) => {
                let model_path = self.models_dir.join(parsed.model_filename());
                let config_path = self.models_dir.join(parsed.config_filename());
                model_path.exists() && config_path.exists()
            }
            Err(_) => false,
        }
    }

    /// Delete a downloaded voice
    pub async fn delete_voice(&self, voice_key: &str) -> DownloadResult<()> {
        let parsed = ParsedVoiceKey::parse(voice_key, None)?;

        let model_path = self.models_dir.join(parsed.model_filename());
        let config_path = self.models_dir.join(parsed.config_filename());

        if model_path.exists() {
            tokio::fs::remove_file(&model_path).await?;
        }
        if config_path.exists() {
            tokio::fs::remove_file(&config_path).await?;
        }

        info!(voice = voice_key, "Deleted voice files");
        Ok(())
    }

    /// Get the models directory
    pub fn models_dir(&self) -> &Path {
        &self.models_dir
    }
}

/// Popular pre-defined Piper voices for quick access
pub fn popular_piper_voices() -> Vec<(&'static str, &'static str, &'static str)> {
    vec![
        ("en_US-lessac-medium", "Lessac (US English)", "Medium quality, natural sounding"),
        ("en_US-amy-medium", "Amy (US English)", "Female voice, clear enunciation"),
        ("en_US-ryan-medium", "Ryan (US English)", "Male voice, warm tone"),
        ("en_GB-alan-medium", "Alan (British English)", "British male, professional"),
        ("en_GB-alba-medium", "Alba (British English)", "British female, clear"),
        ("de_DE-thorsten-medium", "Thorsten (German)", "German male, natural"),
        ("fr_FR-upmc-medium", "UPMC (French)", "French voice, standard"),
        ("es_ES-davefx-medium", "Davefx (Spanish)", "Spanish male voice"),
        ("it_IT-riccardo-medium", "Riccardo (Italian)", "Italian male voice"),
        ("pl_PL-gosia-medium", "Gosia (Polish)", "Polish female voice"),
    ]
}
