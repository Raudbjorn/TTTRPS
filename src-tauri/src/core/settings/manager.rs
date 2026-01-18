use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
// use std::sync::Arc;
use meilisearch_sdk::client::Client;

use crate::commands::LLMSettings;
use crate::ingestion::ExtractionSettings;
use crate::core::voice::VoiceConfig;

const SETTINGS_INDEX: &str = "sys";
const SETTINGS_DOC_ID: &str = "settings";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedSettings {
    pub id: String,
    pub llm: Option<LLMSettings>, // Option to handle partial updates or missing initial state cleanly
    pub extraction: ExtractionSettings,
    pub voice: VoiceConfig,
}

impl Default for UnifiedSettings {
    fn default() -> Self {
        Self {
            id: SETTINGS_DOC_ID.to_string(),
            llm: None, // Starts unconfigured
            extraction: ExtractionSettings::default(),
            voice: VoiceConfig::default(),
        }
    }
}

pub struct SettingsManager {
    settings: RwLock<UnifiedSettings>,
    client: Client,
}

impl SettingsManager {
    pub fn new(url: &str, key: &str) -> Self {
        let client = Client::new(url, Some(key)).expect("Invalid Meilisearch URL or Key");
        Self {
            settings: RwLock::new(UnifiedSettings::default()),
            client,
        }
    }

    pub async fn load(&self) -> Result<UnifiedSettings, String> {
        let index = self.client.index(SETTINGS_INDEX);

        // Ensure index exists (lazy creation)
        let _ = self.client.create_index(SETTINGS_INDEX, Some("id")).await;

        match index.get_document::<UnifiedSettings>(SETTINGS_DOC_ID).await {
            Ok(settings) => {
                let mut guard = self.settings.write().await;
                *guard = settings.clone();
                Ok(settings)
            }
            Err(_) => {
                // Not found, try to persist default
                let default_settings = UnifiedSettings::default();
                self.save(&default_settings).await?;
                Ok(default_settings)
            }
        }
    }

    pub async fn save(&self, new_settings: &UnifiedSettings) -> Result<(), String> {
        let index = self.client.index(SETTINGS_INDEX);

        let mut settings_to_save = new_settings.clone();
        settings_to_save.id = SETTINGS_DOC_ID.to_string(); // Force ID

        match index.add_documents(&[settings_to_save.clone()], Some("id")).await {
            Ok(_) => {
                let mut guard = self.settings.write().await;
                *guard = settings_to_save;
                Ok(())
            }
            Err(e) => Err(format!("Failed to persist settings: {}", e)),
        }
    }

    pub async fn get_settings(&self) -> UnifiedSettings {
        self.settings.read().await.clone()
    }

    pub async fn update_llm(&self, llm: LLMSettings) -> Result<(), String> {
        let mut current = self.get_settings().await;
        current.llm = Some(llm);
        self.save(&current).await
    }

    pub async fn update_extraction(&self, extraction: ExtractionSettings) -> Result<(), String> {
        let mut current = self.get_settings().await;
        current.extraction = extraction;
        self.save(&current).await
    }

    pub async fn update_voice(&self, voice: VoiceConfig) -> Result<(), String> {
        let mut current = self.get_settings().await;
        current.voice = voice;
        self.save(&current).await
    }

    pub async fn reset_to_defaults(&self) -> Result<UnifiedSettings, String> {
        let default = UnifiedSettings::default();
        self.save(&default).await?;
        Ok(default)
    }
}
