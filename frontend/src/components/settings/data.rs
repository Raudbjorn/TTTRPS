use leptos::prelude::*;
use crate::components::design_system::{Card, Button, ButtonVariant};
use wasm_bindgen_futures::spawn_local;
use crate::bindings::{
    reindex_library, get_meilisearch_config, save_meilisearch_config,
    test_meilisearch_connection, get_meilisearch_master_key,
    MeilisearchConfigInfo, MeilisearchConfigSource, ConfigWarningSeverity,
};
use crate::services::notification_service::{show_success, show_error};

#[component]
pub fn DataSettingsView() -> impl IntoView {
    let reindex_status = RwSignal::new(String::new());
    let is_reindexing = RwSignal::new(false);

    // Meilisearch config state
    let config_info = RwSignal::new(Option::<MeilisearchConfigInfo>::None);
    let is_loading_config = RwSignal::new(true);
    let show_advanced = RwSignal::new(false);

    // Form fields for advanced config
    let edit_host = RwSignal::new(String::new());
    let edit_port = RwSignal::new(String::new());
    let edit_master_key = RwSignal::new(String::new());
    let edit_enabled = RwSignal::new(false);

    // UI state
    let is_testing = RwSignal::new(false);
    let is_saving = RwSignal::new(false);
    let test_result = RwSignal::new(Option::<Result<(), String>>::None);

    // Derived signals for button disabled states
    let test_btn_disabled = Signal::derive(move || is_testing.get() || !edit_enabled.get());
    let save_btn_disabled = Signal::derive(move || is_saving.get());

    // Load config on mount
    Effect::new(move || {
        spawn_local(async move {
            match get_meilisearch_config().await {
                Ok(info) => {
                    // Populate form fields
                    edit_host.set(info.host.clone());
                    edit_port.set(info.port.to_string());
                    edit_enabled.set(info.user_config.as_ref().map(|c| c.enabled).unwrap_or(false));

                    config_info.set(Some(info));

                    // Try to load master key from keychain
                    if let Ok(Some(key)) = get_meilisearch_master_key().await {
                        // Show masked key (first 4 chars + asterisks)
                        let masked = if key.len() > 4 {
                            format!("{}****", &key[..4])
                        } else {
                            "****".to_string()
                        };
                        edit_master_key.set(masked);
                    }
                }
                Err(e) => {
                    show_error("Failed to load config", Some(&e), None);
                }
            }
            is_loading_config.set(false);
        });
    });

    let handle_reindex = move |_: web_sys::MouseEvent| {
        is_reindexing.set(true);
        reindex_status.set("Re-indexing...".to_string());
        spawn_local(async move {
            match reindex_library(None).await {
                Ok(msg) => {
                    reindex_status.set(msg.clone());
                    show_success("Re-indexing complete", Some(&msg));
                }
                Err(e) => {
                    reindex_status.set(format!("Error: {}", e));
                    show_error("Re-indexing Failed", Some(&e), None);
                }
            }
            is_reindexing.set(false);
        });
    };

    let handle_test_connection = move |_: web_sys::MouseEvent| {
        is_testing.set(true);
        test_result.set(None);

        let host = edit_host.get();
        let port: u16 = edit_port.get().parse().unwrap_or(7700);
        let key = edit_master_key.get();

        // If key is masked, we need the real key from keychain
        spawn_local(async move {
            let actual_key = if key.contains('*') {
                // Key is masked, get from keychain
                match get_meilisearch_master_key().await {
                    Ok(Some(k)) => k,
                    _ => key
                }
            } else {
                key
            };

            match test_meilisearch_connection(host, port, actual_key).await {
                Ok(true) => {
                    test_result.set(Some(Ok(())));
                    show_success("Connection successful", None);
                }
                Ok(false) => {
                    test_result.set(Some(Err("Connection failed".to_string())));
                    show_error("Connection failed", None, None);
                }
                Err(e) => {
                    test_result.set(Some(Err(e.clone())));
                    show_error("Connection test failed", Some(&e), None);
                }
            }
            is_testing.set(false);
        });
    };

    let handle_save = move |_: web_sys::MouseEvent| {
        is_saving.set(true);

        let host = edit_host.get();
        let port: u16 = edit_port.get().parse().unwrap_or(7700);
        let key = edit_master_key.get();
        let enabled = edit_enabled.get();

        // Only send key if it's not masked (i.e., user entered a new one)
        let key_to_save = if key.contains('*') {
            None  // Keep existing keychain value
        } else {
            Some(key)
        };

        spawn_local(async move {
            match save_meilisearch_config(host, port, key_to_save, enabled).await {
                Ok(()) => {
                    show_success("Configuration saved", Some("Restart the app to apply changes."));
                    // Reload config
                    if let Ok(info) = get_meilisearch_config().await {
                        config_info.set(Some(info));
                    }
                }
                Err(e) => {
                    show_error("Failed to save config", Some(&e), None);
                }
            }
            is_saving.set(false);
        });
    };

    view! {
         <div class="space-y-8 animate-fade-in">
            <div class="space-y-2">
                <h3 class="text-xl font-bold text-[var(--text-primary)]">"Data & Storage"</h3>
                <p class="text-[var(--text-muted)]">"Manage your local library, search index, and Meilisearch connection."</p>
            </div>

            // Search Engine Configuration Section
            <Card class="p-6">
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <div>
                            <h4 class="font-bold text-[var(--text-primary)]">"Search Engine"</h4>
                            <p class="text-sm text-[var(--text-muted)]">"Meilisearch connection and configuration"</p>
                        </div>
                        {move || {
                            let info = config_info.get();
                            view! {
                                <div class="flex items-center gap-3">
                                    // Connection status indicator
                                    <div class="flex items-center gap-2">
                                        <div class={
                                            if info.as_ref().map(|i| i.is_connected).unwrap_or(false) {
                                                "w-2 h-2 rounded-full bg-green-500"
                                            } else {
                                                "w-2 h-2 rounded-full bg-red-500"
                                            }
                                        }></div>
                                        <span class="text-sm text-[var(--text-muted)]">
                                            {if info.as_ref().map(|i| i.is_connected).unwrap_or(false) {
                                                "Connected"
                                            } else {
                                                "Disconnected"
                                            }}
                                        </span>
                                    </div>
                                    // Config source badge
                                    <span class={format!(
                                        "px-2 py-1 text-xs rounded {}",
                                        match info.as_ref().map(|i| i.config_source) {
                                            Some(MeilisearchConfigSource::SystemConfig) => "bg-blue-500/20 text-blue-400",
                                            Some(MeilisearchConfigSource::UserSettings) => "bg-purple-500/20 text-purple-400",
                                            Some(MeilisearchConfigSource::Default) | None => "bg-yellow-500/20 text-yellow-400",
                                        }
                                    )}>
                                        {match info.as_ref().map(|i| i.config_source) {
                                            Some(MeilisearchConfigSource::SystemConfig) => "System Config",
                                            Some(MeilisearchConfigSource::UserSettings) => "User Settings",
                                            Some(MeilisearchConfigSource::Default) | None => "Default",
                                        }}
                                    </span>
                                </div>
                            }
                        }}
                    </div>

                    // Warnings banner
                    {move || {
                        let info = config_info.get();
                        let warnings: Vec<_> = info.as_ref()
                            .map(|i| i.warnings.clone())
                            .unwrap_or_default()
                            .into_iter()
                            .filter(|w| matches!(w.severity, ConfigWarningSeverity::Warning | ConfigWarningSeverity::Error))
                            .collect();

                        if !warnings.is_empty() {
                            view! {
                                <div class="p-3 rounded bg-yellow-500/10 border border-yellow-500/30">
                                    <div class="flex items-start gap-2">
                                        <svg class="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                                        </svg>
                                        <div class="text-sm text-yellow-400">
                                            {warnings.into_iter().map(|w| view! {
                                                <p>{w.message}</p>
                                            }).collect_view()}
                                        </div>
                                    </div>
                                </div>
                            }.into_any()
                        } else {
                            view! { <div></div> }.into_any()
                        }
                    }}

                    // Current config display
                    {move || {
                        let info = config_info.get();
                        view! {
                            <div class="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span class="text-[var(--text-muted)]">"Host: "</span>
                                    <span class="text-[var(--text-primary)] font-mono">
                                        {info.as_ref().map(|i| i.host.clone()).unwrap_or_else(|| "...".to_string())}
                                    </span>
                                </div>
                                <div>
                                    <span class="text-[var(--text-muted)]">"Port: "</span>
                                    <span class="text-[var(--text-primary)] font-mono">
                                        {info.as_ref().map(|i| i.port.to_string()).unwrap_or_else(|| "...".to_string())}
                                    </span>
                                </div>
                            </div>
                        }
                    }}

                    // Advanced configuration toggle
                    <button
                        class="flex items-center gap-2 text-sm text-[var(--accent-primary)] hover:text-[var(--accent-secondary)] transition-colors"
                        on:click=move |_| show_advanced.update(|v| *v = !*v)
                    >
                        <svg
                            class={move || format!("w-4 h-4 transition-transform {}", if show_advanced.get() { "rotate-90" } else { "" })}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                        </svg>
                        "Advanced Configuration"
                    </button>

                    // Advanced configuration panel
                    {move || {
                        if show_advanced.get() {
                            view! {
                                <div class="space-y-4 p-4 rounded bg-[var(--bg-tertiary)] border border-[var(--border-primary)]">
                                    // Enable custom settings toggle
                                    <label class="flex items-center gap-3 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            class="w-4 h-4 rounded border-[var(--border-primary)] bg-[var(--bg-secondary)]"
                                            prop:checked=edit_enabled
                                            on:change=move |ev| {
                                                let checked = event_target_checked(&ev);
                                                edit_enabled.set(checked);
                                            }
                                        />
                                        <span class="text-sm text-[var(--text-primary)]">"Use custom settings"</span>
                                    </label>

                                    // Host input
                                    <div class="space-y-1">
                                        <label class="text-sm text-[var(--text-muted)]">"Host"</label>
                                        <input
                                            type="text"
                                            class="w-full px-3 py-2 rounded bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] font-mono text-sm focus:outline-none focus:border-[var(--accent-primary)]"
                                            placeholder="127.0.0.1"
                                            prop:value=edit_host
                                            prop:disabled=move || !edit_enabled.get()
                                            on:input=move |ev| edit_host.set(event_target_value(&ev))
                                        />
                                    </div>

                                    // Port input
                                    <div class="space-y-1">
                                        <label class="text-sm text-[var(--text-muted)]">"Port"</label>
                                        <input
                                            type="number"
                                            class="w-full px-3 py-2 rounded bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] font-mono text-sm focus:outline-none focus:border-[var(--accent-primary)]"
                                            placeholder="7700"
                                            prop:value=edit_port
                                            prop:disabled=move || !edit_enabled.get()
                                            on:input=move |ev| edit_port.set(event_target_value(&ev))
                                        />
                                    </div>

                                    // Master key input
                                    <div class="space-y-1">
                                        <label class="text-sm text-[var(--text-muted)]">"Master Key"</label>
                                        <input
                                            type="password"
                                            class="w-full px-3 py-2 rounded bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] font-mono text-sm focus:outline-none focus:border-[var(--accent-primary)]"
                                            placeholder="Enter master key"
                                            prop:value=edit_master_key
                                            prop:disabled=move || !edit_enabled.get()
                                            on:input=move |ev| edit_master_key.set(event_target_value(&ev))
                                        />
                                        <p class="text-xs text-[var(--text-muted)]">"Stored securely in system keychain"</p>
                                    </div>

                                    // Test result indicator
                                    {move || {
                                        match test_result.get() {
                                            Some(Ok(())) => view! {
                                                <p class="text-sm text-green-400">"Connection test successful"</p>
                                            }.into_any(),
                                            Some(Err(e)) => view! {
                                                <p class="text-sm text-red-400">{format!("Connection failed: {}", e)}</p>
                                            }.into_any(),
                                            None => view! { <div></div> }.into_any(),
                                        }
                                    }}

                                    // Action buttons
                                    <div class="flex gap-3 pt-2">
                                        <Button
                                            variant=ButtonVariant::Outline
                                            on_click=handle_test_connection
                                            disabled=test_btn_disabled
                                            loading=is_testing
                                        >
                                            "Test Connection"
                                        </Button>
                                        <Button
                                            variant=ButtonVariant::Primary
                                            on_click=handle_save
                                            disabled=save_btn_disabled
                                            loading=is_saving
                                        >
                                            "Save"
                                        </Button>
                                    </div>
                                </div>
                            }.into_any()
                        } else {
                            view! { <div></div> }.into_any()
                        }
                    }}
                </div>
            </Card>

            // Search Index Card
            <Card class="p-6">
                <div class="flex justify-between items-center">
                    <div>
                        <h4 class="font-bold text-[var(--text-primary)]">"Search Index"</h4>
                        <p class="text-sm text-[var(--text-muted)]">"Rebuild the Meilisearch index if search results are incorrect."</p>
                         <p class="text-xs text-[var(--accent-primary)] mt-1">{move || reindex_status.get()}</p>
                    </div>
                    <Button
                        variant=ButtonVariant::Outline
                        on_click=handle_reindex
                        disabled=is_reindexing.get()
                        loading=is_reindexing.get()
                    >
                        "Re-index Library"
                    </Button>
                </div>
            </Card>
        </div>
    }
}
