//! Extraction provider settings component.
//!
//! This module provides UI for configuring text extraction providers,
//! including Kreuzberg (default) and Claude Gate.

use leptos::prelude::*;
use wasm_bindgen_futures::spawn_local;

use crate::bindings::{
    claude_gate_get_status, claude_gate_start_oauth, claude_gate_logout,
    ClaudeGateStatus,
};
use crate::components::design_system::{Card, Badge, BadgeVariant};
use crate::services::notification_service::{show_error, show_success};

/// Extraction provider options
#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum ExtractionProvider {
    /// Kreuzberg - local extraction with bundled pdfium
    #[default]
    Kreuzberg,
    /// Claude Gate - uses Claude API for extraction
    ClaudeGate,
}

impl std::fmt::Display for ExtractionProvider {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ExtractionProvider::Kreuzberg => write!(f, "Kreuzberg"),
            ExtractionProvider::ClaudeGate => write!(f, "Claude Gate"),
        }
    }
}

/// Settings view for text extraction providers.
#[component]
pub fn ExtractionSettingsView() -> impl IntoView {
    // State
    let selected_provider = RwSignal::new(ExtractionProvider::Kreuzberg);
    let claude_gate_status = RwSignal::new(ClaudeGateStatus::default());
    let is_loading = RwSignal::new(false);

    // Refresh Claude Gate status
    let refresh_status = move || {
        is_loading.set(true);
        spawn_local(async move {
            match claude_gate_get_status().await {
                Ok(status) => claude_gate_status.set(status),
                Err(e) => show_error("Claude Gate Status", Some(&e), None),
            }
            is_loading.set(false);
        });
    };

    // Initial load
    Effect::new(move |_| {
        refresh_status();
    });

    view! {
        <div class="space-y-8 animate-fade-in pb-20">
            <div class="space-y-2">
                <h3 class="text-xl font-bold text-[var(--text-primary)]">"Text Extraction"</h3>
                <p class="text-[var(--text-muted)]">"Configure how documents are extracted and processed."</p>
            </div>

            // Provider Selection
            <Card class="p-6 space-y-6">
                <h4 class="font-semibold text-[var(--text-secondary)]">"Extraction Provider"</h4>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    // Kreuzberg Option
                    <button
                        class=move || format!(
                            "relative p-4 rounded-xl border-2 text-left transition-all duration-300 hover:scale-[1.02] group {}",
                            if selected_provider.get() == ExtractionProvider::Kreuzberg {
                                "border-[var(--accent-primary)] bg-[var(--bg-elevated)] ring-2 ring-[var(--accent-primary)]/20 shadow-lg"
                            } else {
                                "border-[var(--border-subtle)] hover:border-[var(--border-strong)] bg-[var(--bg-surface)] hover:bg-[var(--bg-elevated)]"
                            }
                        )
                        on:click=move |_| selected_provider.set(ExtractionProvider::Kreuzberg)
                    >
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-medium text-[var(--text-primary)] group-hover:text-[var(--accent-primary)] transition-colors">
                                "Kreuzberg"
                            </span>
                            <Badge variant=BadgeVariant::Info>"Default"</Badge>
                        </div>
                        <p class="text-sm text-[var(--text-muted)]">
                            "Local extraction using bundled pdfium. Fast, private, no API costs."
                        </p>
                        <div class="mt-3 flex flex-wrap gap-2">
                            <span class="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">"PDF"</span>
                            <span class="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">"EPUB"</span>
                            <span class="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">"DOCX"</span>
                            <span class="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">"Images"</span>
                        </div>

                        // Active indicator
                        {move || if selected_provider.get() == ExtractionProvider::Kreuzberg {
                            view! {
                                <div class="absolute top-3 right-3 text-[var(--accent-primary)] animate-fade-in">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                                        <path d="m9 12 2 2 4-4"/>
                                    </svg>
                                </div>
                            }.into_any()
                        } else {
                            view! { <span/> }.into_any()
                        }}
                    </button>

                    // Claude Gate Option
                    <button
                        class=move || format!(
                            "relative p-4 rounded-xl border-2 text-left transition-all duration-300 hover:scale-[1.02] group {}",
                            if selected_provider.get() == ExtractionProvider::ClaudeGate {
                                "border-orange-400 bg-[var(--bg-elevated)] ring-2 ring-orange-400/20 shadow-lg"
                            } else {
                                "border-[var(--border-subtle)] hover:border-[var(--border-strong)] bg-[var(--bg-surface)] hover:bg-[var(--bg-elevated)]"
                            }
                        )
                        on:click=move |_| selected_provider.set(ExtractionProvider::ClaudeGate)
                    >
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-medium text-[var(--text-primary)] group-hover:text-orange-400 transition-colors">
                                "Claude Gate"
                            </span>
                            {move || if claude_gate_status.get().authenticated {
                                view! { <Badge variant=BadgeVariant::Success>"Authenticated"</Badge> }.into_any()
                            } else {
                                view! { <Badge variant=BadgeVariant::Warning>"Not Authenticated"</Badge> }.into_any()
                            }}
                        </div>
                        <p class="text-sm text-[var(--text-muted)]">
                            "Uses Claude API for intelligent extraction. Better for complex layouts."
                        </p>
                        <div class="mt-3 flex flex-wrap gap-2">
                            <span class="text-xs px-2 py-1 bg-orange-500/20 text-orange-400 rounded-full">"PDF"</span>
                            <span class="text-xs px-2 py-1 bg-orange-500/20 text-orange-400 rounded-full">"Images"</span>
                            <span class="text-xs px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full">"API Costs"</span>
                        </div>

                        // Active indicator
                        {move || if selected_provider.get() == ExtractionProvider::ClaudeGate {
                            view! {
                                <div class="absolute top-3 right-3 text-orange-400 animate-fade-in">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/>
                                        <path d="m9 12 2 2 4-4"/>
                                    </svg>
                                </div>
                            }.into_any()
                        } else {
                            view! { <span/> }.into_any()
                        }}
                    </button>
                </div>
            </Card>

            // Claude Gate Authentication Section (shown when Claude Gate is selected)
            {move || if selected_provider.get() == ExtractionProvider::ClaudeGate {
                let status = claude_gate_status.get();
                view! {
                    <Card class="p-6 space-y-4 border-orange-400/30">
                        <div class="flex items-center justify-between">
                            <h4 class="font-semibold text-orange-400">"Claude Gate Authentication"</h4>
                            {if status.authenticated {
                                view! {
                                    <Badge variant=BadgeVariant::Success>
                                        {status.expires_in_human.clone().unwrap_or_else(|| "Authenticated".to_string())}
                                    </Badge>
                                }.into_any()
                            } else {
                                view! {
                                    <Badge variant=BadgeVariant::Warning>"Login Required"</Badge>
                                }.into_any()
                            }}
                        </div>

                        <p class="text-sm text-[var(--text-muted)]">
                            "Claude Gate requires OAuth authentication with your Anthropic account."
                        </p>

                        // Status info
                        <div class="flex flex-wrap gap-2">
                            <div class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400">
                                {format!("Storage: {}", status.storage_backend)}
                            </div>
                            {status.error.map(|e| view! {
                                <div class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400">
                                    {format!("Error: {}", e)}
                                </div>
                            })}
                        </div>

                        // Action buttons
                        <div class="flex gap-3 pt-2">
                            {move || {
                                let loading = is_loading.get();
                                let authenticated = claude_gate_status.get().authenticated;
                                if !authenticated {
                                    view! {
                                        <button
                                            class="px-4 py-2 text-sm font-medium rounded-lg bg-orange-500 text-white hover:bg-orange-600 transition-colors disabled:opacity-50"
                                            disabled=loading
                                            on:click=move |_| {
                                                spawn_local(async move {
                                                    is_loading.set(true);
                                                    match claude_gate_start_oauth().await {
                                                        Ok(url) => {
                                                            if let Some(window) = web_sys::window() {
                                                                if window.open_with_url(&url).is_err() {
                                                                    show_error("Browser Open Failed", Some("Could not open the authentication URL."), None);
                                                                } else {
                                                                    show_success("Login Started", Some("Complete authentication in your browser"));
                                                                }
                                                            } else {
                                                                show_error("Browser Open Failed", Some("Could not access browser window."), None);
                                                            }
                                                        }
                                                        Err(e) => show_error("OAuth Failed", Some(&e), None),
                                                    }
                                                    is_loading.set(false);
                                                });
                                            }
                                        >
                                            "Login with Claude"
                                        </button>
                                    }.into_any()
                                } else {
                                    view! {
                                        <button
                                            class="px-4 py-2 text-sm font-medium rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
                                            disabled=loading
                                            on:click=move |_| {
                                                spawn_local(async move {
                                                    is_loading.set(true);
                                                    match claude_gate_logout().await {
                                                        Ok(_) => {
                                                            show_success("Logged Out", None);
                                                            refresh_status();
                                                        }
                                                        Err(e) => show_error("Logout Failed", Some(&e), None),
                                                    }
                                                    is_loading.set(false);
                                                });
                                            }
                                        >
                                            "Logout"
                                        </button>
                                    }.into_any()
                                }
                            }}

                            <button
                                class="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] transition-colors disabled:opacity-50"
                                disabled=move || is_loading.get()
                                on:click=move |_| refresh_status()
                            >
                                {move || if is_loading.get() { "Checking..." } else { "Refresh Status" }}
                            </button>
                        </div>
                    </Card>
                }.into_any()
            } else {
                view! { <span/> }.into_any()
            }}

            // Additional extraction settings note
            <Card class="p-6">
                <div class="flex items-start gap-4">
                    <div class="p-2 rounded-lg bg-blue-500/20">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-400">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M12 16v-4"/>
                            <path d="M12 8h.01"/>
                        </svg>
                    </div>
                    <div>
                        <h4 class="font-semibold text-[var(--text-secondary)]">"OCR Settings"</h4>
                        <p class="text-sm text-[var(--text-muted)]">
                            "For scanned documents and images, OCR settings can be configured in the Data & Library section. "
                            "Both providers support OCR fallback for documents without extractable text."
                        </p>
                    </div>
                </div>
            </Card>
        </div>
    }
}
