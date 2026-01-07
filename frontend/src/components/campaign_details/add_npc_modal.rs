//! Add NPC to Campaign Modal
//!
//! Allows adding existing NPCs to a campaign, with options to copy state from previous campaigns.

use leptos::prelude::*;
use leptos::ev;
use wasm_bindgen_futures::spawn_local;
use crate::bindings::{
    NPC, NpcCampaignInfo, get_available_npcs_for_campaign, list_npc_campaigns,
    add_npc_to_campaign,
};
use crate::components::design_system::{Button, ButtonVariant, Modal};
use crate::services::notification_service::{show_success, show_error};

/// Modal for adding an existing NPC to a campaign
#[component]
pub fn AddNpcToCampaignModal(
    /// Whether the modal is open
    is_open: RwSignal<bool>,
    /// Campaign ID to add NPC to
    campaign_id: String,
    /// Campaign name for display
    campaign_name: String,
    /// Callback when NPC is added
    on_add: Callback<String>, // Returns NPC ID
) -> impl IntoView {
    let available_npcs = RwSignal::new(Vec::<NPC>::new());
    let selected_npc = RwSignal::new(Option::<NPC>::None);
    let selected_npc_campaigns = RwSignal::new(Vec::<NpcCampaignInfo>::new());
    let copy_from_campaign = RwSignal::new(Option::<String>::None);
    let is_loading = RwSignal::new(true);
    let is_adding = RwSignal::new(false);
    let search_query = RwSignal::new(String::new());
    let step = RwSignal::new(1); // 1 = select NPC, 2 = configure state

    let campaign_id_signal = RwSignal::new(campaign_id.clone());

    // Load available NPCs when modal opens
    Effect::new(move |_| {
        if !is_open.get() {
            // Reset state when modal closes
            step.set(1);
            selected_npc.set(None);
            copy_from_campaign.set(None);
            return;
        }

        let campaign_id = campaign_id_signal.get();
        is_loading.set(true);

        spawn_local(async move {
            match get_available_npcs_for_campaign(campaign_id).await {
                Ok(npcs) => available_npcs.set(npcs),
                Err(e) => {
                    show_error("Load Error", Some(&format!("Failed to load NPCs: {}", e)), None);
                }
            }
            is_loading.set(false);
        });
    });

    // Load selected NPC's campaign history when selected
    Effect::new(move |_| {
        let npc = selected_npc.get();
        if npc.is_none() {
            selected_npc_campaigns.set(Vec::new());
            return;
        }

        let npc_id = npc.unwrap().id.clone();
        spawn_local(async move {
            match list_npc_campaigns(npc_id).await {
                Ok(campaigns) => selected_npc_campaigns.set(campaigns),
                Err(_) => selected_npc_campaigns.set(Vec::new()),
            }
        });
    });

    // Filter NPCs based on search query
    let filtered_npcs = move || {
        let query = search_query.get().to_lowercase();
        let npcs = available_npcs.get();

        if query.is_empty() {
            npcs
        } else {
            npcs.into_iter()
                .filter(|n| {
                    n.name.to_lowercase().contains(&query)
                        || n.role.to_lowercase().contains(&query)
                        || n.notes.to_lowercase().contains(&query)
                })
                .collect()
        }
    };

    // Select NPC and move to step 2
    let select_npc = move |npc: NPC| {
        selected_npc.set(Some(npc));
        step.set(2);
    };

    // Go back to step 1
    let go_back = move |_: ev::MouseEvent| {
        step.set(1);
        selected_npc.set(None);
        copy_from_campaign.set(None);
    };

    // Store on_add in a signal for repeated access
    let on_add_signal = RwSignal::new(on_add);

    // Add NPC to campaign handler
    let add_npc = Callback::new(move |_: ev::MouseEvent| {
        let npc = selected_npc.get();
        if npc.is_none() {
            return;
        }
        let npc = npc.unwrap();
        let npc_id = npc.id.clone();
        let campaign_id = campaign_id_signal.get();
        let copy_from = copy_from_campaign.get();
        let on_add = on_add_signal.get();

        is_adding.set(true);
        spawn_local(async move {
            match add_npc_to_campaign(npc_id.clone(), campaign_id, copy_from).await {
                Ok(_) => {
                    show_success("NPC Added", Some("NPC has been added to the campaign"));
                    is_open.set(false);
                    on_add.run(npc_id);
                }
                Err(e) => {
                    show_error("Add Error", Some(&e), None);
                }
            }
            is_adding.set(false);
        });
    });

    view! {
        <Modal is_open=is_open title=format!("Add NPC to {}", campaign_name)>
            <div class="min-w-[400px]">
                // Step indicator
                <div class="flex items-center gap-2 mb-4">
                    <StepIndicator step=1 current=step label="Select NPC" />
                    <div class="flex-1 h-px bg-zinc-700"></div>
                    <StepIndicator step=2 current=step label="Configure" />
                </div>

                // Step 1: Select NPC
                <Show when=move || step.get() == 1 fallback=|| ()>
                    <div class="space-y-4">
                        // Search box
                        <input
                            type="text"
                            placeholder="Search NPCs..."
                            class="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
                            prop:value=move || search_query.get()
                            on:input=move |evt| search_query.set(event_target_value(&evt))
                        />

                        // NPC list
                        <div class="max-h-64 overflow-y-auto space-y-2">
                            {move || {
                                if is_loading.get() {
                                    view! {
                                        <div class="flex items-center justify-center py-8 text-zinc-500">
                                            "Loading NPCs..."
                                        </div>
                                    }.into_any()
                                } else {
                                    let npcs = filtered_npcs();
                                    if npcs.is_empty() {
                                        view! {
                                            <div class="flex flex-col items-center justify-center py-8 text-zinc-500">
                                                <p>"No available NPCs"</p>
                                                <p class="text-sm">"All NPCs are already in this campaign, or none exist yet."</p>
                                            </div>
                                        }.into_any()
                                    } else {
                                        view! {
                                            <For
                                                each=move || filtered_npcs()
                                                key=|n| n.id.clone()
                                                children=move |npc| {
                                                    let npc_for_click = npc.clone();
                                                    view! {
                                                        <NpcSelectionCard
                                                            npc=npc
                                                            on_click=move |_| select_npc(npc_for_click.clone())
                                                        />
                                                    }
                                                }
                                            />
                                        }.into_any()
                                    }
                                }
                            }}
                        </div>

                        // Cancel button
                        <div class="flex justify-end pt-4 border-t border-zinc-700">
                            <Button variant=ButtonVariant::Ghost on_click=move |_| is_open.set(false)>
                                "Cancel"
                            </Button>
                        </div>
                    </div>
                </Show>

                // Step 2: Configure state copying
                <Show when=move || step.get() == 2 fallback=|| ()>
                    <div class="space-y-4">
                        {move || selected_npc.get().map(|npc| view! {
                            <div class="bg-zinc-800/50 rounded-lg p-4 border border-zinc-700">
                                <h3 class="font-medium text-white">{npc.name.clone()}</h3>
                                <p class="text-sm text-zinc-500">{npc.role.clone()}</p>
                            </div>
                        })}

                        // Previous campaigns selection
                        <div>
                            <h4 class="text-sm font-medium text-zinc-300 mb-2">"Copy state from previous campaign?"</h4>
                            <p class="text-xs text-zinc-500 mb-3">
                                "If this NPC has appeared in other campaigns, you can copy their memories and experiences."
                            </p>

                            <div class="space-y-2">
                                // Option: Start fresh
                                {
                                    let is_fresh_selected = Signal::derive(move || copy_from_campaign.get().is_none());
                                    let on_select_fresh = Callback::new(move |_: ev::MouseEvent| copy_from_campaign.set(None));
                                    view! {
                                        <CampaignOption
                                            id=None
                                            name="Start Fresh".to_string()
                                            description="NPC will have no prior memories in this campaign".to_string()
                                            is_selected=is_fresh_selected
                                            on_select=on_select_fresh
                                        />
                                    }
                                }

                                // Previous campaigns
                                <For
                                    each=move || selected_npc_campaigns.get()
                                    key=|c| c.campaign_id.clone()
                                    children=move |campaign| {
                                        let cid = campaign.campaign_id.clone();
                                        let is_selected = {
                                            let cid = cid.clone();
                                            Signal::derive(move || copy_from_campaign.get() == Some(cid.clone()))
                                        };
                                        let on_select = {
                                            let cid = cid.clone();
                                            Callback::new(move |_: ev::MouseEvent| copy_from_campaign.set(Some(cid.clone())))
                                        };
                                        view! {
                                            <CampaignOption
                                                id=Some(campaign.campaign_id.clone())
                                                name=campaign.campaign_name.clone()
                                                description=format!("Joined: {}", format_date(&campaign.joined_at))
                                                is_selected=is_selected
                                                on_select=on_select
                                            />
                                        }
                                    }
                                />
                            </div>
                        </div>

                        // Action buttons
                        <div class="flex justify-between pt-4 border-t border-zinc-700">
                            <Button variant=ButtonVariant::Ghost on_click=go_back>
                                "Back"
                            </Button>
                            <div class="flex gap-2">
                                <Button variant=ButtonVariant::Ghost on_click=move |_| is_open.set(false)>
                                    "Cancel"
                                </Button>
                                <Button
                                    variant=ButtonVariant::Primary
                                    on_click=move |e| add_npc.run(e)
                                    disabled=is_adding
                                >
                                    {move || if is_adding.get() { "Adding..." } else { "Add NPC" }}
                                </Button>
                            </div>
                        </div>
                    </div>
                </Show>
            </div>
        </Modal>
    }
}

/// Step indicator component
#[component]
fn StepIndicator(
    step: i32,
    current: RwSignal<i32>,
    label: &'static str,
) -> impl IntoView {
    view! {
        <div class="flex items-center gap-2">
            <div class=move || format!(
                "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium {}",
                if current.get() >= step {
                    "bg-[var(--accent)] text-white"
                } else {
                    "bg-zinc-700 text-zinc-400"
                }
            )>
                {step}
            </div>
            <span class=move || format!(
                "text-sm {}",
                if current.get() >= step { "text-white" } else { "text-zinc-500" }
            )>
                {label}
            </span>
        </div>
    }
}

/// NPC selection card
#[component]
fn NpcSelectionCard(
    npc: NPC,
    on_click: impl Fn(ev::MouseEvent) + 'static,
) -> impl IntoView {
    let initial = npc.name.chars().next().unwrap_or('?');

    view! {
        <button
            class="w-full flex items-center gap-3 p-3 rounded-lg border border-zinc-700 bg-zinc-800/50 hover:bg-zinc-700/50 transition-colors text-left"
            on:click=on_click
        >
            <div class="w-10 h-10 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-[var(--accent)] font-bold border border-[var(--accent)]/40">
                {initial.to_string()}
            </div>
            <div class="flex-1 min-w-0">
                <p class="font-medium text-white truncate">{npc.name}</p>
                <p class="text-xs text-zinc-500 truncate">{npc.role}</p>
            </div>
            <svg class="w-5 h-5 text-zinc-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6" />
            </svg>
        </button>
    }
}

/// Campaign option for state copying
#[component]
fn CampaignOption(
    id: Option<String>,
    name: String,
    description: String,
    is_selected: Signal<bool>,
    on_select: Callback<ev::MouseEvent>,
) -> impl IntoView {
    let _ = id; // Unused but kept for future use
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
            <p class="font-medium text-white">{name}</p>
            <p class="text-xs text-zinc-500">{description}</p>
        </button>
    }
}

/// Format ISO date to a readable format
fn format_date(iso: &str) -> String {
    if let Some(date_part) = iso.split('T').next() {
        date_part.to_string()
    } else {
        iso.to_string()
    }
}
