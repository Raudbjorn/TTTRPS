use meilisearch_sdk::client::Client;
use meilisearch_sdk::indexes::Index;
use meilisearch_sdk::settings::Settings;
use std::sync::Arc;
use tokio::sync::RwLock;

pub struct SearchClient {
    client: Client,
}

impl SearchClient {
    pub fn new(host: &str, api_key: Option<&str>) -> Self {
        Self {
            client: Client::new(host, api_key).expect("Failed to create Meilisearch client"),
        }
    }

    pub async fn health_check(&self) -> bool {
        self.client.is_healthy().await
    }

    pub async fn wait_for_health(&self, timeout_secs: u64) -> bool {
        let start = std::time::Instant::now();
        let duration = std::time::Duration::from_secs(timeout_secs);
        while start.elapsed() < duration {
            if self.health_check().await {
                return true;
            }
            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
        }
        false
    }

    pub async fn get_index(&self, name: &str) -> Index {
        self.client.index(name)
    }

    pub async fn ensure_index(&self, name: &str, primary_key: Option<&str>) -> Result<Index, String> {
        let task = self.client.create_index(name, primary_key)
            .await
            .map_err(|e| e.to_string())?;

        // Wait for task completion? create_index returns a TaskInfo which we can wait on
        // But for "ensure", checking if it exists first might be better, or just ignoring "already exists" error?
        // Meilisearch create_index returns TaskInfo.
        // We probably want to just return the Index object wrapper.

        // Actually, we should check if it exists.
        match self.client.get_index(name).await {
            Ok(idx) => Ok(idx),
            Err(_) => {
                 // Try creating
                 let task = self.client.create_index(name, primary_key).await.map_err(|e| e.to_string())?;
                 let _ = task.wait_for_completion(&self.client, None, None).await;
                 Ok(self.client.index(name))
            }
        }
    }

    pub async fn update_settings(&self, index_name: &str, settings: &Settings) -> Result<(), String> {
        let index = self.client.index(index_name);
        let task = index.set_settings(settings).await.map_err(|e| e.to_string())?;
        task.wait_for_completion(&self.client, None, None).await
            .map_err(|e| e.to_string())?;
        Ok(())
    }
}
