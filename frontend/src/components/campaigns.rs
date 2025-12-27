#![allow(non_snake_case)]
use dioxus::prelude::*;
use crate::bindings::{list_campaigns, create_campaign, delete_campaign, Campaign};

#[component]
pub fn Campaigns() -> Element {
    let mut campaigns = use_signal(|| Vec::<Campaign>::new());
    let mut status_message = use_signal(|| String::new());
    let mut show_create_modal = use_signal(|| false);
    let mut new_campaign_name = use_signal(|| String::new());
    let mut new_campaign_system = use_signal(|| "D&D 5e".to_string());
    let mut is_loading = use_signal(|| true);

    // Load campaigns on mount
    use_effect(move || {
        spawn(async move {
            match list_campaigns().await {
                Ok(list) => {
                    campaigns.set(list);
                }
                Err(e) => {
                    status_message.set(format!("Failed to load campaigns: {}", e));
                }
            }
            is_loading.set(false);
        });
    });

    let refresh_campaigns = move |_: MouseEvent| {
        is_loading.set(true);
        spawn(async move {
            match list_campaigns().await {
                Ok(list) => {
                    campaigns.set(list);
                    status_message.set("Refreshed".to_string());
                }
                Err(e) => {
                    status_message.set(format!("Error: {}", e));
                }
            }
            is_loading.set(false);
        });
    };

    let open_create_modal = move |_: MouseEvent| {
        show_create_modal.set(true);
        new_campaign_name.set(String::new());
        new_campaign_system.set("D&D 5e".to_string());
    };

    let close_modal = move |_: MouseEvent| {
        show_create_modal.set(false);
    };

    let handle_create = move |_: MouseEvent| {
        let name = new_campaign_name.read().clone();
        let system = new_campaign_system.read().clone();

        if name.trim().is_empty() {
            status_message.set("Campaign name is required".to_string());
            return;
        }

        spawn(async move {
            match create_campaign(name, system).await {
                Ok(campaign) => {
                    campaigns.write().push(campaign);
                    show_create_modal.set(false);
                    status_message.set("Campaign created!".to_string());
                }
                Err(e) => {
                    status_message.set(format!("Error: {}", e));
                }
            }
        });
    };

    let handle_delete = move |id: String, name: String| {
        move |_: MouseEvent| {
            let id = id.clone();
            let name = name.clone();
            spawn(async move {
                match delete_campaign(id.clone()).await {
                    Ok(_) => {
                        campaigns.write().retain(|c| c.id != id);
                        status_message.set(format!("Deleted campaign: {}", name));
                    }
                    Err(e) => {
                        status_message.set(format!("Error deleting: {}", e));
                    }
                }
            });
        }
    };

    let loading = *is_loading.read();
    let status = status_message.read().clone();
    let modal_open = *show_create_modal.read();

    rsx! {
        div {
            class: "p-8 bg-gray-900 text-white min-h-screen font-sans",
            div {
                class: "max-w-4xl mx-auto",
                // Header
                div {
                    class: "flex items-center justify-between mb-8",
                    div {
                        class: "flex items-center",
                        Link { to: crate::Route::Chat {}, class: "mr-4 text-gray-400 hover:text-white", "← Chat" }
                        h1 { class: "text-2xl font-bold", "Campaigns" }
                    }
                    div {
                        class: "flex gap-2",
                        button {
                            onclick: refresh_campaigns,
                            class: "px-4 py-2 bg-gray-600 rounded hover:bg-gray-500 transition-colors",
                            "Refresh"
                        }
                        button {
                            onclick: open_create_modal,
                            class: "px-4 py-2 bg-green-600 rounded hover:bg-green-500 transition-colors",
                            "+ New Campaign"
                        }
                    }
                }

                // Status message
                if !status.is_empty() {
                    div {
                        class: "mb-4 p-3 bg-gray-800 rounded text-sm text-gray-300",
                        "{status}"
                    }
                }

                // Campaign list
                div {
                    class: "space-y-4",
                    if loading {
                        div {
                            class: "text-center py-8 text-gray-500",
                            "Loading campaigns..."
                        }
                    } else if campaigns.read().is_empty() {
                        div {
                            class: "text-center py-12 bg-gray-800 rounded-lg",
                            p { class: "text-gray-400 mb-4", "No campaigns yet" }
                            p { class: "text-gray-500 text-sm", "Create your first campaign to get started!" }
                        }
                    } else {
                        for campaign in campaigns.read().iter() {
                            div {
                                key: "{campaign.id}",
                                class: "bg-gray-800 rounded-lg p-6 hover:bg-gray-750 transition-colors",
                                div {
                                    class: "flex justify-between items-start",
                                    div {
                                        class: "flex-1",
                                        div {
                                            class: "flex items-center gap-3 mb-2",
                                            h3 { class: "text-xl font-semibold", "{campaign.name}" }
                                            span {
                                                class: "text-xs px-2 py-1 bg-blue-900 text-blue-300 rounded",
                                                "{campaign.system}"
                                            }
                                        }
                                        if let Some(desc) = &campaign.description {
                                            p { class: "text-gray-400 text-sm mb-3", "{desc}" }
                                        }
                                        div {
                                            class: "flex gap-4 text-sm text-gray-500",
                                            span { "Sessions: {campaign.session_count}" }
                                            span { "Players: {campaign.player_count}" }
                                            span { "Created: {campaign.created_at}" }
                                        }
                                    }
                                    div {
                                        class: "flex gap-2",
                                        Link {
                                            to: crate::Route::Session { campaign_id: campaign.id.clone() },
                                            class: "px-3 py-1 bg-purple-600 rounded hover:bg-purple-500 text-sm",
                                            "Start Session"
                                        }
                                        button {
                                            onclick: handle_delete(campaign.id.clone(), campaign.name.clone()),
                                            class: "px-3 py-1 bg-red-600 rounded hover:bg-red-500 text-sm",
                                            "Delete"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Quick links
                div {
                    class: "mt-8 p-4 bg-gray-800 rounded-lg",
                    h3 { class: "font-semibold mb-3", "Quick Actions" }
                    div {
                        class: "flex gap-4",
                        Link {
                            to: crate::Route::CharacterCreator {},
                            class: "px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 text-sm",
                            "Generate Character"
                        }
                        Link {
                            to: crate::Route::Library {},
                            class: "px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 text-sm",
                            "Manage Library"
                        }
                    }
                }
            }

            // Create Campaign Modal
            if modal_open {
                div {
                    class: "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50",
                    onclick: close_modal,
                    div {
                        class: "bg-gray-800 rounded-lg p-6 w-full max-w-md",
                        onclick: move |e: MouseEvent| e.stop_propagation(),
                        h2 { class: "text-xl font-bold mb-4", "Create New Campaign" }

                        div {
                            class: "space-y-4",
                            div {
                                label { class: "block text-sm text-gray-400 mb-1", "Campaign Name" }
                                input {
                                    class: "w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none",
                                    placeholder: "My Epic Campaign",
                                    value: "{new_campaign_name}",
                                    oninput: move |e| new_campaign_name.set(e.value())
                                }
                            }
                            div {
                                label { class: "block text-sm text-gray-400 mb-1", "Game System" }
                                select {
                                    class: "w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none",
                                    onchange: move |e| new_campaign_system.set(e.value()),
                                    option { value: "D&D 5e", "D&D 5e" }
                                    option { value: "Pathfinder 2e", "Pathfinder 2e" }
                                    option { value: "Call of Cthulhu", "Call of Cthulhu" }
                                    option { value: "Cyberpunk", "Cyberpunk" }
                                    option { value: "Shadowrun", "Shadowrun" }
                                    option { value: "Fate Core", "Fate Core" }
                                    option { value: "World of Darkness", "World of Darkness" }
                                    option { value: "Other", "Other" }
                                }
                            }
                        }

                        div {
                            class: "flex justify-end gap-2 mt-6",
                            button {
                                onclick: close_modal,
                                class: "px-4 py-2 bg-gray-600 rounded hover:bg-gray-500",
                                "Cancel"
                            }
                            button {
                                onclick: handle_create,
                                class: "px-4 py-2 bg-green-600 rounded hover:bg-green-500",
                                "Create"
                            }
                        }
                    }
                }
            }
        }
    }
}
