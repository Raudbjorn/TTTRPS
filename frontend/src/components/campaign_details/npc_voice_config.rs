//! NPC Voice Configuration Component
//!
//! Allows configuring voice profiles for NPCs, with support for campaign-specific overrides.

use leptos::prelude::*;
use leptos::ev;
use wasm_bindgen_futures::spawn_local;
use crate::bindings::{
    VoiceProfile, VoiceProfileInfo, list_voice_presets, link_voice_profile_to_npc,
    unlink_voice_profile_from_npc, get_effective_npc_voice_profile, set_campaign_npc_voice,
    speak_as_npc,
};
use crate::components::design_system::{Button, ButtonVariant, Modal};
use crate::services::notification_service::{show_success, show_error};
use crate::utils::play_audio_base64;

/// NPC Voice Configuration modal for setting voice profiles
#[component]
pub fn NpcVoiceConfig(
    /// Whether the modal is open
    is_open: RwSignal<bool>,
    /// NPC ID to configure
    npc_id: String,
    /// NPC name for display
    npc_name: String,
    /// Optional campaign ID for campaign-specific override
    campaign_id: Option<String>,
    /// Callback when voice profile is updated
    #[prop(default = None)]
    on_save: Option<Callback<()>>,
) -> impl IntoView {
    let profiles = RwSignal::new(Vec::<VoiceProfile>::new());
    let current_profile = RwSignal::new(Option::<VoiceProfileInfo>::None);
    let selected_profile_id = RwSignal::new(Option::<String>::None);
    let is_loading = RwSignal::new(true);
    let is_saving = RwSignal::new(false);
    let is_previewing = RwSignal::new(false);
    let search_query = RwSignal::new(String::new());

    let npc_id_signal = RwSignal::new(npc_id.clone());
    let campaign_id_signal = RwSignal::new(campaign_id.clone());
    let npc_name_display = npc_name.clone();
    let on_save_signal = RwSignal::new(on_save);

    // Load voice profiles and current assignment on mount
    Effect::new(move |_| {
        if !is_open.get() {
            return;
        }
        let npc_id = npc_id_signal.get();
        let campaign_id = campaign_id_signal.get();

        spawn_local(async move {
            // Load all available profiles
            match list_voice_presets().await {
                Ok(profs) => profiles.set(profs),
                Err(e) => {
                    show_error("Load Error", Some(&format!("Failed to load voice profiles: {}", e)), None);
                }
            }

            // Load current effective profile
            match get_effective_npc_voice_profile(npc_id, campaign_id).await {
                Ok(profile) => {
                    if let Some(ref p) = profile {
                        selected_profile_id.set(Some(p.id.clone()));
                    }
                    current_profile.set(profile);
                }
                Err(e) => {
                    show_error("Load Error", Some(&format!("Failed to get current profile: {}", e)), None);
                }
            }

            is_loading.set(false);
        });
    });

    // Filter profiles based on search query
    let filtered_profiles = move || {
        let query = search_query.get().to_lowercase();
        let all_profiles = profiles.get();

        if query.is_empty() {
            all_profiles
        } else {
            all_profiles
                .into_iter()
                .filter(|p| {
                    p.name.to_lowercase().contains(&query)
                        || p.voice_id.to_lowercase().contains(&query)
                        || format!("{:?}", p.provider).to_lowercase().contains(&query)
                })
                .collect()
        }
    };

    // Preview voice handler
    let preview_voice = Callback::new(move |_: ev::MouseEvent| {
        if is_previewing.get() {
            return;
        }
        let npc_id = npc_id_signal.get();
        let campaign_id = campaign_id_signal.get();
        is_previewing.set(true);

        spawn_local(async move {
            let preview_text = "Hello! This is a preview of how I will sound.".to_string();
            match speak_as_npc(preview_text, npc_id, campaign_id).await {
                Ok(Some(result)) => {
                    if let Err(e) = play_audio_base64(&result.audio_data, &result.format) {
                        show_error("Preview Error", Some(&format!("Failed to play: {}", e)), None);
                    }
                }
                Ok(None) => {
                    show_error("Voice Disabled", Some("Voice synthesis is currently disabled in settings"), None);
                }
                Err(e) => {
                    show_error("Preview Error", Some(&e), None);
                }
            }
            is_previewing.set(false);
        });
    });

    // Save handler
    let save_handler = Callback::new(move |_: ev::MouseEvent| {
        let profile_id = selected_profile_id.get();
        let npc_id = npc_id_signal.get();
        let campaign_id = campaign_id_signal.get();
        let on_save = on_save_signal.get();
        is_saving.set(true);

        spawn_local(async move {
            let result = if let Some(cid) = campaign_id {
                // Set campaign-specific override (None means use global DM voice)
                set_campaign_npc_voice(npc_id, cid, profile_id).await
            } else if let Some(pid) = profile_id {
                // Set NPC's default voice profile
                link_voice_profile_to_npc(pid, npc_id).await
            } else {
                // Unset NPC's default voice profile (revert to global DM voice)
                unlink_voice_profile_from_npc(npc_id).await
            };

            match result {
                Ok(_) => {
                    show_success("Voice Updated", Some("NPC voice profile has been updated"));
                    is_open.set(false);
                    if let Some(cb) = on_save {
                        cb.run(());
                    }
                }
                Err(e) => {
                    show_error("Save Error", Some(&e), None);
                }
            }
            is_saving.set(false);
        });
    });

    view! {
        <Modal is_open=is_open title=format!("Voice Configuration - {}", npc_name_display)>
            <div class="space-y-4">
                // Current voice info
                <div class="bg-zinc-800/50 rounded-lg p-4 border border-zinc-700">
                    <h3 class="text-sm font-medium text-zinc-300 mb-2">"Current Voice"</h3>
                    {move || {
                        if is_loading.get() {
                            view! { <p class="text-zinc-500 text-sm">"Loading..."</p> }.into_any()
                        } else if let Some(profile) = current_profile.get() {
                            view! {
                                <div class="flex items-center justify-between">
                                    <div>
                                        <p class="text-white font-medium">{profile.name}</p>
                                        <p class="text-xs text-zinc-500">
                                            {format!("{} - {}", profile.provider, profile.voice_id)}
                                        </p>
                                    </div>
                                    <Button
                                        variant=ButtonVariant::Ghost
                                        on_click=move |e| preview_voice.run(e)
                                        disabled=is_previewing
                                    >
                                        {move || if is_previewing.get() { "Playing..." } else { "Preview" }}
                                    </Button>
                                </div>
                            }.into_any()
                        } else {
                            view! {
                                <p class="text-zinc-500 text-sm">"No voice profile assigned (using default DM voice)"</p>
                            }.into_any()
                        }
                    }}
                </div>

                // Search box
                <div>
                    <input
                        type="text"
                        placeholder="Search voice profiles..."
                        class="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
                        prop:value=move || search_query.get()
                        on:input=move |evt| search_query.set(event_target_value(&evt))
                    />
                </div>

                // Voice profile list
                <div class="max-h-64 overflow-y-auto space-y-2">
                    // Option to use default (no profile)
                    {
                        let is_default_selected = Signal::derive(move || selected_profile_id.get().is_none());
                        let on_select_default = Callback::new(move |_: ev::MouseEvent| selected_profile_id.set(None));
                        view! {
                            <VoiceProfileOption
                                name="Use Default (DM Voice)".to_string()
                                description="Use the global voice settings".to_string()
                                provider="System".to_string()
                                is_selected=is_default_selected
                                on_select=on_select_default
                            />
                        }
                    }

                    // Available profiles
                    <For
                        each=filtered_profiles
                        key=|p| p.id.clone()
                        children=move |profile| {
                            let profile_id = profile.id.clone();
                            let pid_for_signal = profile_id.clone();
                            let pid_for_callback = profile_id.clone();
                            let is_selected = Signal::derive(move || selected_profile_id.get() == Some(pid_for_signal.clone()));
                            let on_select = Callback::new(move |_: ev::MouseEvent| selected_profile_id.set(Some(pid_for_callback.clone())));
                            view! {
                                <VoiceProfileOption
                                    name=profile.name.clone()
                                    description=profile.voice_id.clone()
                                    provider=format!("{:?}", profile.provider)
                                    is_selected=is_selected
                                    on_select=on_select
                                />
                            }
                        }
                    />
                </div>

                // Campaign-specific note
                {move || campaign_id_signal.get().map(|_| view! {
                    <p class="text-xs text-zinc-500 bg-zinc-800/30 p-2 rounded">
                        "This voice setting will only apply to this campaign. The NPC's default voice in other campaigns will remain unchanged."
                    </p>
                })}

                // Action buttons
                <div class="flex justify-end gap-2 pt-4 border-t border-zinc-700">
                    <Button
                        variant=ButtonVariant::Ghost
                        on_click=move |_| is_open.set(false)
                    >
                        "Cancel"
                    </Button>
                    <Button
                        variant=ButtonVariant::Primary
                        on_click=move |e| save_handler.run(e)
                        disabled=is_saving
                    >
                        {move || if is_saving.get() { "Saving..." } else { "Save" }}
                    </Button>
                </div>
            </div>
        </Modal>
    }
}

/// Individual voice profile option in the selection list
#[component]
fn VoiceProfileOption(
    name: String,
    description: String,
    provider: String,
    is_selected: Signal<bool>,
    on_select: Callback<ev::MouseEvent>,
) -> impl IntoView {
    view! {
        <button
            class=move || format!(
                "w-full text-left p-3 rounded-lg border transition-colors {}",
                if is_selected.get() {
                    "bg-[var(--accent)]/20 border-[var(--accent)]/50"
                } else {
                    "bg-zinc-800/50 border-zinc-700 hover:bg-zinc-700/50"
                }
            )
            on:click=move |e| on_select.run(e)
        >
            <div class="flex items-center justify-between">
                <div>
                    <p class="font-medium text-white">{name}</p>
                    <p class="text-xs text-zinc-500">{description}</p>
                </div>
                <span class="text-xs px-2 py-1 bg-zinc-700 rounded text-zinc-400">
                    {provider}
                </span>
            </div>
        </button>
    }
}
