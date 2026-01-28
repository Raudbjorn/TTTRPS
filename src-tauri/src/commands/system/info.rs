//! System Information Commands
//!
//! Commands for retrieving application version and system information.

use serde::{Deserialize, Serialize};

/// Application system information
#[derive(Debug, Serialize, Deserialize)]
pub struct AppSystemInfo {
    pub os: String,
    pub arch: String,
    pub version: String,
}

/// Get the application version
#[tauri::command]
pub fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Get application system information including OS, architecture, and version
#[tauri::command]
pub fn get_app_system_info() -> AppSystemInfo {
    AppSystemInfo {
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
    }
}
