//! Browser Commands
//!
//! Commands for opening URLs in the system browser.

/// Open a URL in the system's default browser
///
/// Uses Tauri's opener plugin to open URLs properly on all platforms.
#[tauri::command]
pub async fn open_url_in_browser(
    url: String,
    app_handle: tauri::AppHandle,
) -> Result<(), String> {
    use tauri_plugin_opener::OpenerExt;

    app_handle.opener().open_url(&url, None::<&str>)
        .map_err(|e| format!("Failed to open URL: {}", e))
}
