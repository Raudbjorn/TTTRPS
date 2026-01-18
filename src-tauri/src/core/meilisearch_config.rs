//! Meilisearch Configuration Module
//!
//! Provides smart configuration resolution for Meilisearch connections.
//! Supports reading from system config files, user settings, and defaults.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

// ============================================================================
// Constants
// ============================================================================

/// Default Meilisearch host
pub const DEFAULT_HOST: &str = "127.0.0.1";

/// Default Meilisearch port
pub const DEFAULT_PORT: u16 = 7700;

/// Default master key (fallback only)
pub const DEFAULT_MASTER_KEY: &str = "ttrpg-assistant-dev-key";

/// System config file path (Linux)
pub const SYSTEM_CONFIG_PATH: &str = "/etc/meilisearch.conf";

/// User config filename
pub const USER_CONFIG_FILENAME: &str = "meilisearch_config.json";

// ============================================================================
// Types
// ============================================================================

/// Source of the Meilisearch configuration
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum ConfigSource {
    /// Read from /etc/meilisearch.conf (system service)
    SystemConfig,
    /// User-configured settings in app
    UserSettings,
    /// Hardcoded defaults (fallback)
    #[default]
    Default,
}

impl std::fmt::Display for ConfigSource {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConfigSource::SystemConfig => write!(f, "System Config"),
            ConfigSource::UserSettings => write!(f, "User Settings"),
            ConfigSource::Default => write!(f, "Default"),
        }
    }
}

/// Warning generated during config resolution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigWarning {
    pub message: String,
    pub severity: WarningSeverity,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WarningSeverity {
    Info,
    Warning,
    Error,
}

/// Resolved Meilisearch settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeilisearchSettings {
    pub host: String,
    pub port: u16,
    pub master_key: String,
    pub config_source: ConfigSource,
    #[serde(default)]
    pub warnings: Vec<ConfigWarning>,
}

impl Default for MeilisearchSettings {
    fn default() -> Self {
        Self {
            host: DEFAULT_HOST.to_string(),
            port: DEFAULT_PORT,
            master_key: DEFAULT_MASTER_KEY.to_string(),
            config_source: ConfigSource::Default,
            warnings: vec![ConfigWarning {
                message: "Using default master key - connection may fail if Meilisearch has a different key configured".to_string(),
                severity: WarningSeverity::Warning,
            }],
        }
    }
}

impl MeilisearchSettings {
    /// Get the full URL for Meilisearch
    pub fn url(&self) -> String {
        format!("http://{}:{}", self.host, self.port)
    }
}

/// User-persisted Meilisearch configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeilisearchUserConfig {
    pub host: String,
    pub port: u16,
    /// Note: In production, master_key should be stored in keychain
    /// This field is for UI display (masked) and initial save only
    #[serde(skip_serializing_if = "Option::is_none")]
    pub master_key: Option<String>,
    /// Whether custom settings are enabled
    pub enabled: bool,
}

impl Default for MeilisearchUserConfig {
    fn default() -> Self {
        Self {
            host: DEFAULT_HOST.to_string(),
            port: DEFAULT_PORT,
            master_key: None,
            enabled: false,
        }
    }
}

// ============================================================================
// Config Resolution
// ============================================================================

/// Parse the system Meilisearch config file (/etc/meilisearch.conf)
///
/// This file uses bash-style KEY=VALUE format with optional comments.
pub fn parse_system_config() -> Option<MeilisearchSettings> {
    parse_system_config_from_path(Path::new(SYSTEM_CONFIG_PATH))
}

/// Parse a config file from a specific path (for testing)
pub fn parse_system_config_from_path(path: &Path) -> Option<MeilisearchSettings> {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(e) => {
            log::debug!("Could not read {}: {}", path.display(), e);
            return None;
        }
    };

    let mut host = DEFAULT_HOST.to_string();
    let mut port = DEFAULT_PORT;
    let mut master_key: Option<String> = None;

    for line in content.lines() {
        let line = line.trim();

        // Skip empty lines and comments
        if line.is_empty() || line.starts_with('#') {
            continue;
        }

        // Parse KEY=VALUE
        if let Some((key, value)) = line.split_once('=') {
            let key = key.trim();
            let value = value.trim().trim_matches('"').trim_matches('\'');

            match key {
                "MEILI_MASTER_KEY" => {
                    if !value.is_empty() {
                        master_key = Some(value.to_string());
                    }
                }
                "MEILI_HTTP_ADDR" => {
                    // Parse host:port format
                    if let Some((h, p)) = value.rsplit_once(':') {
                        host = h.to_string();
                        if let Ok(parsed_port) = p.parse::<u16>() {
                            port = parsed_port;
                        }
                    } else {
                        host = value.to_string();
                    }
                }
                _ => {} // Ignore other keys
            }
        }
    }

    // Only return if we found a master key
    master_key.map(|key| {
        log::info!("Loaded Meilisearch config from {}", path.display());
        MeilisearchSettings {
            host,
            port,
            master_key: key,
            config_source: ConfigSource::SystemConfig,
            warnings: vec![],
        }
    })
}

/// Load user settings from the app data directory
pub fn load_user_settings(app_data_dir: &Path) -> Option<MeilisearchUserConfig> {
    let config_path = app_data_dir.join(USER_CONFIG_FILENAME);

    match fs::read_to_string(&config_path) {
        Ok(content) => {
            match serde_json::from_str::<MeilisearchUserConfig>(&content) {
                Ok(config) => {
                    log::debug!("Loaded user Meilisearch config from {}", config_path.display());
                    Some(config)
                }
                Err(e) => {
                    log::warn!("Failed to parse {}: {}", config_path.display(), e);
                    None
                }
            }
        }
        Err(_) => None,
    }
}

/// Save user settings to the app data directory
pub fn save_user_settings(app_data_dir: &Path, config: &MeilisearchUserConfig) -> Result<(), String> {
    let config_path = app_data_dir.join(USER_CONFIG_FILENAME);

    // Ensure directory exists
    if let Some(parent) = config_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create config directory: {}", e))?;
    }

    let content = serde_json::to_string_pretty(config)
        .map_err(|e| format!("Failed to serialize config: {}", e))?;

    fs::write(&config_path, content)
        .map_err(|e| format!("Failed to write config: {}", e))?;

    log::info!("Saved Meilisearch user config to {}", config_path.display());
    Ok(())
}

/// Resolve the Meilisearch configuration using the priority chain.
///
/// Priority for external Meilisearch (already running):
/// 1. System config (/etc/meilisearch.conf)
/// 2. User settings
/// 3. Default (with warning)
///
/// Priority for embedded/sidecar:
/// 1. User settings
/// 2. Default (with warning)
pub fn resolve_config(
    app_data_dir: Option<&Path>,
    is_external_instance: bool,
) -> MeilisearchSettings {
    let mut warnings = Vec::new();

    // For external instances, try system config first
    if is_external_instance {
        if let Some(settings) = parse_system_config() {
            log::info!("Using system Meilisearch config from /etc/meilisearch.conf");
            return settings;
        } else {
            warnings.push(ConfigWarning {
                message: "Could not read /etc/meilisearch.conf - trying user settings".to_string(),
                severity: WarningSeverity::Info,
            });
        }
    }

    // Try user settings
    if let Some(app_dir) = app_data_dir {
        if let Some(user_config) = load_user_settings(app_dir) {
            if user_config.enabled {
                log::info!("Using user-configured Meilisearch settings");
                return MeilisearchSettings {
                    host: user_config.host,
                    port: user_config.port,
                    master_key: user_config.master_key.unwrap_or_else(|| DEFAULT_MASTER_KEY.to_string()),
                    config_source: ConfigSource::UserSettings,
                    warnings: vec![],
                };
            }
        }
    }

    // Fall back to defaults with warning
    log::warn!("Using default Meilisearch configuration - connection may fail");
    warnings.push(ConfigWarning {
        message: "Using default master key - connection may fail if Meilisearch has a different key configured".to_string(),
        severity: WarningSeverity::Warning,
    });

    MeilisearchSettings {
        host: DEFAULT_HOST.to_string(),
        port: DEFAULT_PORT,
        master_key: DEFAULT_MASTER_KEY.to_string(),
        config_source: ConfigSource::Default,
        warnings,
    }
}

// ============================================================================
// Validation
// ============================================================================

/// Validate a Meilisearch URL/host configuration
pub fn validate_config(host: &str, port: u16) -> Result<(), String> {
    // Validate host
    if host.is_empty() {
        return Err("Host cannot be empty".to_string());
    }

    // Check for valid IP address or hostname format
    // Allow localhost, IPv4, IPv6, and valid hostnames
    let is_valid_host = host == "localhost"
        || host.parse::<std::net::Ipv4Addr>().is_ok()
        || host.parse::<std::net::Ipv6Addr>().is_ok()
        || is_valid_hostname(host);

    if !is_valid_host {
        return Err(format!("Invalid host format: {}", host));
    }

    // Validate port
    if port == 0 {
        return Err("Port cannot be 0".to_string());
    }

    Ok(())
}

/// Check if a string is a valid hostname
fn is_valid_hostname(s: &str) -> bool {
    // Basic hostname validation
    if s.is_empty() || s.len() > 253 {
        return false;
    }

    for label in s.split('.') {
        if label.is_empty() || label.len() > 63 {
            return false;
        }
        if !label.chars().all(|c| c.is_ascii_alphanumeric() || c == '-') {
            return false;
        }
        if label.starts_with('-') || label.ends_with('-') {
            return false;
        }
    }

    true
}

/// Test connection to a Meilisearch instance
pub async fn test_connection(host: &str, port: u16, master_key: &str) -> Result<(), String> {
    let url = format!("http://{}:{}/health", host, port);

    let client = reqwest::Client::new();
    let response = client
        .get(&url)
        .header("Authorization", format!("Bearer {}", master_key))
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
        .map_err(|e| format!("Connection failed: {}", e))?;

    if response.status().is_success() {
        Ok(())
    } else {
        Err(format!("Meilisearch returned status: {}", response.status()))
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_parse_system_config() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "# Meilisearch configuration").unwrap();
        writeln!(file, "MEILI_HTTP_ADDR=127.0.0.1:7700").unwrap();
        writeln!(file, "MEILI_MASTER_KEY=my-secret-key").unwrap();
        writeln!(file, "MEILI_ENV=development").unwrap();

        let settings = parse_system_config_from_path(file.path()).unwrap();
        assert_eq!(settings.host, "127.0.0.1");
        assert_eq!(settings.port, 7700);
        assert_eq!(settings.master_key, "my-secret-key");
        assert_eq!(settings.config_source, ConfigSource::SystemConfig);
    }

    #[test]
    fn test_parse_system_config_no_key() {
        let mut file = NamedTempFile::new().unwrap();
        writeln!(file, "MEILI_HTTP_ADDR=127.0.0.1:7700").unwrap();
        // No master key

        let settings = parse_system_config_from_path(file.path());
        assert!(settings.is_none());
    }

    #[test]
    fn test_validate_config() {
        assert!(validate_config("127.0.0.1", 7700).is_ok());
        assert!(validate_config("localhost", 7700).is_ok());
        assert!(validate_config("meilisearch.example.com", 7700).is_ok());
        assert!(validate_config("", 7700).is_err());
        assert!(validate_config("127.0.0.1", 0).is_err());
    }

    #[test]
    fn test_hostname_validation() {
        assert!(is_valid_hostname("localhost"));
        assert!(is_valid_hostname("example.com"));
        assert!(is_valid_hostname("sub.example.com"));
        assert!(is_valid_hostname("my-server"));
        assert!(!is_valid_hostname(""));
        assert!(!is_valid_hostname("-invalid"));
        assert!(!is_valid_hostname("invalid-"));
    }
}
