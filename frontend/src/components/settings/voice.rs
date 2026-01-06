use leptos::prelude::*;
use leptos::ev;
use wasm_bindgen_futures::spawn_local;
use gloo_timers::callback::Timeout;
use crate::bindings::{
    configure_voice, get_voice_config, list_elevenlabs_voices, list_openai_tts_models,
    list_openai_voices, list_all_voices, get_popular_piper_voices, download_piper_voice,
    ElevenLabsConfig, OllamaConfig, OpenAIVoiceConfig, Voice, VoiceConfig,
    PiperConfig, CoquiConfig, PopularPiperVoice,
};
use crate::components::design_system::{Card, Input, Select, SelectOption, Button, ButtonVariant};
use crate::services::notification_service::{show_error, show_success};

#[component]
pub fn VoiceSettingsView() -> impl IntoView {
    // Signals
    let selected_voice_provider = RwSignal::new("Disabled".to_string());
    let voice_api_key_or_host = RwSignal::new(String::new());
    let piper_models_dir = RwSignal::new(String::new());
    let voice_model_id = RwSignal::new(String::new());
    let selected_voice_id = RwSignal::new(String::new());

    let available_voices = RwSignal::new(Vec::<Voice>::new());
    let openai_tts_models = RwSignal::new(Vec::<(String, String)>::new());

    let is_loading_voices = RwSignal::new(false);
    let save_status = RwSignal::new(String::new());
    let is_saving = RwSignal::new(false);
    let initial_load = RwSignal::new(true);
    let timeout_handle = StoredValue::new_local(None::<Timeout>);

    // Piper voice download
    let popular_voices = RwSignal::new(Vec::<PopularPiperVoice>::new());
    let downloading_voice = RwSignal::new(Option::<String>::None);
    let download_error = RwSignal::new(Option::<String>::None);

    // Helpers
    let fetch_voices = move |provider: String, api_key: Option<String>| {
        spawn_local(async move {
            is_loading_voices.set(true);
            match provider.as_str() {
                "OpenAI" => {
                    if let Ok(voices) = list_openai_voices().await {
                        available_voices.set(voices);
                    }
                    if let Ok(models) = list_openai_tts_models().await {
                        openai_tts_models.set(models);
                    }
                }
                "ElevenLabs" => {
                    if let Some(key) = api_key {
                        if !key.is_empty() && !key.starts_with('*') {
                            if let Ok(voices) = list_elevenlabs_voices(key).await {
                                available_voices.set(voices);
                            }
                        }
                    }
                }
                "Piper" | "Coqui" => {
                    if let Ok(voices) = list_all_voices().await {
                        let filtered: Vec<Voice> = voices.into_iter()
                            .filter(|v| v.provider.eq_ignore_ascii_case(provider.as_str()))
                            .collect();
                        available_voices.set(filtered);
                    }
                }
                _ => {
                    available_voices.set(Vec::new());
                }
            }
            is_loading_voices.set(false);
        });
    };

    // On Mount - load existing config
    Effect::new(move |_| {
        spawn_local(async move {
            if let Ok(config) = get_voice_config().await {
                let provider_str = match config.provider.as_str() {
                    "ElevenLabs" => "ElevenLabs",
                    "Ollama" => "Ollama",
                    "FishAudio" => "FishAudio",
                    "OpenAI" => "OpenAI",
                    "Piper" => "Piper",
                    "Coqui" => "Coqui",
                    _ => "Disabled",
                };
                selected_voice_provider.set(provider_str.to_string());

                match provider_str {
                    "ElevenLabs" => {
                        if let Some(c) = config.elevenlabs {
                            voice_api_key_or_host.set(c.api_key.clone());
                            voice_model_id.set(c.model_id.unwrap_or_default());
                            if !c.api_key.is_empty() && !c.api_key.starts_with('*') {
                                fetch_voices("ElevenLabs".to_string(), Some(c.api_key));
                            }
                        }
                    }
                    "Ollama" => {
                        if let Some(c) = config.ollama {
                            voice_api_key_or_host.set(c.base_url);
                            voice_model_id.set(c.model);
                        }
                    }
                    "OpenAI" => {
                        if let Some(c) = config.openai {
                            voice_api_key_or_host.set(c.api_key);
                            voice_model_id.set(c.model);
                            selected_voice_id.set(c.voice);
                        }
                        fetch_voices("OpenAI".to_string(), None);
                    }
                    "Piper" => {
                        if let Some(c) = config.piper {
                            piper_models_dir.set(c.models_dir.unwrap_or_default());
                        }
                        fetch_voices("Piper".to_string(), None);
                        // Load popular voices for download
                        if let Ok(voices) = get_popular_piper_voices().await {
                            popular_voices.set(voices);
                        }
                    }
                    "Coqui" => {
                        if let Some(c) = config.coqui {
                            voice_api_key_or_host.set(format!("{}", c.port));
                            voice_model_id.set(c.model);
                        }
                        fetch_voices("Coqui".to_string(), None);
                    }
                    _ => {}
                }
            }
            initial_load.set(false);
        });
    });

    // Auto-Save Effect
    Effect::new(move |_| {
        let provider = selected_voice_provider.get();
        let val = voice_api_key_or_host.get();
        let piper_dir = piper_models_dir.get();
        let model = voice_model_id.get();
        let voice = selected_voice_id.get();

        if initial_load.get_untracked() {
            return;
        }

        // Cancel any pending save
        timeout_handle.update_value(|h| { if let Some(t) = h.take() { t.cancel(); } });

        let perform_save = move || {
            is_saving.set(true);
            save_status.set("Saving...".to_string());

            spawn_local(async move {
                let voice_config = if provider == "Disabled" {
                    VoiceConfig {
                        provider: "Disabled".to_string(),
                        cache_dir: None,
                        default_voice_id: None,
                        elevenlabs: None,
                        fish_audio: None,
                        ollama: None,
                        openai: None,
                        piper: None,
                        coqui: None,
                    }
                } else {
                    let mut base = VoiceConfig {
                        provider: provider.clone(),
                        cache_dir: None,
                        default_voice_id: if !voice.is_empty() { Some(voice.clone()) } else { None },
                        elevenlabs: None,
                        fish_audio: None,
                        ollama: None,
                        openai: None,
                        piper: None,
                        coqui: None,
                    };

                    match provider.as_str() {
                        "ElevenLabs" => {
                            base.elevenlabs = Some(ElevenLabsConfig {
                                api_key: val.clone(),
                                model_id: Some(model.clone()),
                            });
                        }
                        "Ollama" => {
                            base.ollama = Some(OllamaConfig {
                                base_url: val.clone(),
                                model: model.clone(),
                            });
                        }
                        "OpenAI" => {
                            base.openai = Some(OpenAIVoiceConfig {
                                api_key: val.clone(),
                                model: model.clone(),
                                voice: voice.clone(),
                            });
                        }
                        "Piper" => {
                            base.piper = Some(PiperConfig {
                                models_dir: if piper_dir.is_empty() { None } else { Some(piper_dir.clone()) },
                                length_scale: 1.0,
                                noise_scale: 0.667,
                                noise_w: 0.8,
                                sentence_silence: 0.2,
                                speaker_id: 0,
                            });
                        }
                        "Coqui" => {
                            let port: u16 = val.parse().unwrap_or(5002);
                            base.coqui = Some(CoquiConfig {
                                port,
                                model: if model.is_empty() { "tts_models/en/ljspeech/vits".to_string() } else { model.clone() },
                                speaker: None,
                                language: None,
                                speed: 1.0,
                                speaker_wav: None,
                                temperature: 0.8,
                                top_k: 50,
                                top_p: 0.95,
                                repetition_penalty: 2.0,
                            });
                        }
                        _ => {}
                    }
                    base
                };

                match configure_voice(voice_config).await {
                    Ok(_) => {
                        save_status.set("All changes saved".to_string());
                    }
                    Err(e) => {
                        save_status.set(format!("Error: {}", e));
                        show_error("Save Failed", Some(&e), None);
                    }
                }
                is_saving.set(false);
            });
        };

        // Debounce: save after 1 second of no changes
        timeout_handle.set_value(Some(Timeout::new(1000, perform_save)));
    });

    on_cleanup(move || {
        timeout_handle.update_value(|h| { if let Some(t) = h.take() { t.cancel(); } });
    });

    // Provider change handler
    let handle_provider_change = move |val: String| {
        selected_voice_provider.set(val.clone());
        available_voices.set(Vec::new());

        match val.as_str() {
            "Ollama" => {
                voice_api_key_or_host.set("http://localhost:11434".to_string());
                voice_model_id.set("bark".to_string());
            }
            "ElevenLabs" => {
                voice_api_key_or_host.set(String::new());
                voice_model_id.set("eleven_multilingual_v2".to_string());
            }
            "OpenAI" => {
                voice_api_key_or_host.set(String::new());
                voice_model_id.set("tts-1".to_string());
                selected_voice_id.set("alloy".to_string());
                fetch_voices("OpenAI".to_string(), None);
            }
            "Piper" => {
                piper_models_dir.set(String::new());
                voice_model_id.set(String::new());
                fetch_voices("Piper".to_string(), None);
                // Load popular voices for download
                spawn_local(async move {
                    if let Ok(voices) = get_popular_piper_voices().await {
                        popular_voices.set(voices);
                    }
                });
            }
            "Coqui" => {
                voice_api_key_or_host.set("5002".to_string());
                voice_model_id.set("tts_models/en/ljspeech/vits".to_string());
                fetch_voices("Coqui".to_string(), None);
            }
            _ => {
                voice_api_key_or_host.set(String::new());
                voice_model_id.set(String::new());
                piper_models_dir.set(String::new());
            }
        }
    };

    let providers = vec!["Disabled", "Ollama", "ElevenLabs", "OpenAI", "Piper", "Coqui"];

    view! {
        <div class="space-y-8 animate-fade-in pb-20">
            <div class="space-y-2">
                <h3 class="text-xl font-bold text-[var(--text-primary)]">"Voice & Audio"</h3>
                <p class="text-[var(--text-muted)]">"Manage Text-to-Speech engines and voice clones."</p>
            </div>

            <Card class="p-6">
                <div class="grid grid-cols-1 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">"Provider"</label>
                        <Select
                            value=selected_voice_provider.get()
                            on_change=Callback::new(move |val: String| handle_provider_change(val))
                        >
                            {providers.into_iter().map(|p| {
                                view! { <SelectOption value=p.to_string() /> }
                            }).collect::<Vec<_>>()}
                        </Select>
                    </div>

                    {move || {
                        let provider = selected_voice_provider.get();
                        match provider.as_str() {
                            "Disabled" => view! { <div class="text-[var(--text-muted)] italic">"Voice disabled."</div> }.into_any(),
                            _ => {
                                let provider = provider.clone();
                                let is_piper = provider == "Piper";
                                let is_password = provider == "OpenAI" || provider == "ElevenLabs";
                                let label = match provider.as_str() {
                                    "Ollama" => "Base URL",
                                    "ElevenLabs" | "OpenAI" => "API Key",
                                    "Coqui" => "Port",
                                    _ => "Configuration"
                                };
                                let placeholder = match provider.as_str() {
                                    "Ollama" => "http://localhost:11434",
                                    "OpenAI" | "ElevenLabs" => "sk-...",
                                    "Coqui" => "5002",
                                    _ => ""
                                };
                                view! {
                                <div class="space-y-4 border-t border-[var(--border-subtle)] pt-4 animate-fade-in">
                                    <Show when=move || !is_piper>
                                        <div>
                                            <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                                                {label}
                                            </label>
                                            <Input
                                                value=voice_api_key_or_host
                                                r#type=if is_password { "password".to_string() } else { "text".to_string() }
                                                placeholder=placeholder
                                            />
                                        </div>
                                    </Show>

                                    <Show when=move || is_piper>
                                        <div>
                                            <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">"Models Directory (Optional)"</label>
                                            <Input
                                                value=piper_models_dir
                                                placeholder="/path/to/piper/models"
                                            />
                                        </div>
                                    </Show>

                                    <Show when=move || !is_piper>
                                        <div>
                                            <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">"Model ID"</label>
                                            <Input value=voice_model_id />
                                        </div>
                                    </Show>

                                    {
                                        let voices = available_voices.get();
                                        if !voices.is_empty() {
                                            view! {
                                                <div>
                                                    <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">"Voice Persona"</label>
                                                    <Select
                                                        value=selected_voice_id.get()
                                                        on_change=Callback::new(move |val: String| selected_voice_id.set(val))
                                                    >
                                                        {voices.into_iter().map(|v| {
                                                            view! { <SelectOption value=v.id.clone() label=v.name /> }
                                                        }).collect::<Vec<_>>()}
                                                    </Select>
                                                </div>
                                            }.into_any()
                                        } else {
                                            view! { <span/> }.into_any()
                                        }
                                    }
                                </div>
                            }.into_any()
                        }
                    }}}

                    // Status indicator
                    {move || {
                        let status = save_status.get();
                        if !status.is_empty() {
                            let is_error = status.starts_with("Error");
                            let class = if is_error {
                                "text-sm text-red-400"
                            } else if is_saving.get() {
                                "text-sm text-yellow-400"
                            } else {
                                "text-sm text-green-400"
                            };
                            view! { <div class=class>{status}</div> }.into_any()
                        } else {
                            view! { <span/> }.into_any()
                        }
                    }}
                </div>
            </Card>

            // Piper Voice Download Section
            <Show when=move || selected_voice_provider.get() == "Piper">
                <Card class="p-6">
                    <div class="space-y-4">
                        <div class="flex items-center justify-between">
                            <div>
                                <h4 class="text-lg font-semibold text-[var(--text-primary)]">"Download Voices"</h4>
                                <p class="text-sm text-[var(--text-muted)]">"Download high-quality Piper voices from Hugging Face"</p>
                            </div>
                        </div>

                        // Download error
                        {move || download_error.get().map(|err| view! {
                            <div class="p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">
                                {err}
                            </div>
                        })}

                        // Popular voices list
                        <div class="space-y-2">
                            {move || {
                                let voices = popular_voices.get();
                                let installed = available_voices.get();
                                let installed_ids: Vec<String> = installed.iter()
                                    .map(|v| v.id.clone())
                                    .collect();

                                if voices.is_empty() {
                                    view! {
                                        <div class="text-[var(--text-muted)] text-sm italic">
                                            "Loading available voices..."
                                        </div>
                                    }.into_any()
                                } else {
                                    view! {
                                        <div class="grid gap-2">
                                            {voices.into_iter().map(|(key, name, desc)| {
                                                let key_clone = key.clone();
                                                let key_for_check = key.clone();
                                                let key_for_download = key.clone();
                                                let is_installed = installed_ids.iter().any(|id| id.contains(&key_for_check));
                                                let is_downloading = downloading_voice.get().as_ref() == Some(&key_clone);

                                                view! {
                                                    <div class="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)]">
                                                        <div class="flex-1 min-w-0">
                                                            <div class="font-medium text-[var(--text-primary)]">{name}</div>
                                                            <div class="text-xs text-[var(--text-muted)] truncate">{desc}</div>
                                                        </div>
                                                        <div class="ml-3 flex-shrink-0">
                                                            {if is_installed {
                                                                view! {
                                                                    <span class="px-2 py-1 text-xs rounded bg-green-900/30 text-green-400 border border-green-700">
                                                                        "Installed"
                                                                    </span>
                                                                }.into_any()
                                                            } else if is_downloading {
                                                                view! {
                                                                    <span class="px-2 py-1 text-xs rounded bg-blue-900/30 text-blue-400 border border-blue-700 animate-pulse">
                                                                        "Downloading..."
                                                                    </span>
                                                                }.into_any()
                                                            } else {
                                                                view! {
                                                                    <Button
                                                                        variant=ButtonVariant::Secondary
                                                                        on_click=move |_: ev::MouseEvent| {
                                                                            let voice_key = key_for_download.clone();
                                                                            downloading_voice.set(Some(voice_key.clone()));
                                                                            download_error.set(None);

                                                                            spawn_local(async move {
                                                                                match download_piper_voice(voice_key.clone(), None).await {
                                                                                    Ok(_path) => {
                                                                                        show_success("Voice Downloaded", Some(&format!("Downloaded {}", voice_key)));
                                                                                        // Refresh voice list
                                                                                        if let Ok(voices) = list_all_voices().await {
                                                                                            let filtered: Vec<Voice> = voices.into_iter()
                                                                                                .filter(|v| v.provider.eq_ignore_ascii_case("piper"))
                                                                                                .collect();
                                                                                            available_voices.set(filtered);
                                                                                        }
                                                                                    }
                                                                                    Err(e) => {
                                                                                        download_error.set(Some(format!("Failed to download: {}", e)));
                                                                                        show_error("Download Failed", Some(&e), None);
                                                                                    }
                                                                                }
                                                                                downloading_voice.set(None);
                                                                            });
                                                                        }
                                                                    >
                                                                        "Download"
                                                                    </Button>
                                                                }.into_any()
                                                            }}
                                                        </div>
                                                    </div>
                                                }
                                            }).collect::<Vec<_>>()}
                                        </div>
                                    }.into_any()
                                }
                            }}
                        </div>
                    </div>
                </Card>
            </Show>
        </div>
    }
}
