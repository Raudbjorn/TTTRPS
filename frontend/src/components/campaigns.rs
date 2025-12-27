#![allow(non_snake_case)]
use dioxus::prelude::*;
use crate::bindings::{list_campaigns, create_campaign, delete_campaign, Campaign};
use crate::components::design_system::{Button, ButtonVariant, Input, Select, Card, CardHeader, CardBody, Badge, BadgeVariant, Modal, LoadingSpinner};

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

    let total_campaigns = campaigns.read().len();
    let total_sessions: u32 = campaigns.read().iter().map(|c| c.session_count).sum();
    let total_players: usize = campaigns.read().iter().map(|c| c.player_count).sum();

    rsx! {
        div {
            class: "p-8 bg-theme-primary text-theme-primary min-h-screen font-sans transition-colors duration-300",
            div {
                class: "max-w-6xl mx-auto space-y-8",

                // Header & Quick Actions
                div {
                    class: "flex flex-col md:flex-row md:items-center justify-between gap-4",
                    div {
                        class: "flex items-center gap-4",
                        Link { to: crate::Route::Chat {}, class: "text-gray-400 hover:text-white transition-colors", "← Back" }
                        h1 { class: "text-3xl font-bold", "Campaign Dashboard" }
                    }
                    div {
                        class: "flex gap-2",
                         Button {
                            variant: ButtonVariant::Secondary,
                            onclick: refresh_campaigns,
                            "Refresh"
                        }
                        Button {
                            variant: ButtonVariant::Primary,
                            onclick: open_create_modal,
                            "+ New Campaign"
                        }
                    }
                }

                // Summary Stats
                div {
                    class: "grid grid-cols-1 md:grid-cols-3 gap-6",
                    Card {
                        CardBody {
                            div { class: "text-gray-400 text-sm", "Total Campaigns" }
                            div { class: "text-3xl font-bold text-white", "{total_campaigns}" }
                        }
                    }
                    Card {
                         CardBody {
                            div { class: "text-gray-400 text-sm", "Total Sessions" }
                            div { class: "text-3xl font-bold text-purple-400", "{total_sessions}" }
                        }
                    }
                    Card {
                         CardBody {
                            div { class: "text-gray-400 text-sm", "Active Players" }
                            div { class: "text-3xl font-bold text-green-400", "{total_players}" }
                        }
                    }
                }

                // Status Message
                if !status.is_empty() {
                     Badge {
                        variant: if status.contains("Error") { BadgeVariant::Error } else { BadgeVariant::Info },
                        "{status}"
                    }
                }

                // Content Area
                if loading {
                    div {
                        class: "flex justify-center py-20",
                        LoadingSpinner { size: "lg" }
                    }
                } else if campaigns.read().is_empty() {
                     div {
                        class: "text-center py-20 bg-theme-secondary rounded-lg border border-theme",
                        h3 { class: "text-xl text-gray-300 mb-2", "No campaigns found" }
                        p { class: "text-gray-500 mb-6", "Start your journey by creating your first campaign." }
                        Button {
                            onclick: open_create_modal,
                            "Create Campaign"
                        }
                    }
                } else {
                    div {
                        class: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6",
                        for campaign in campaigns.read().iter() {
                            Card {
                                key: "{campaign.id}",
                                class: "hover:border-blue-500 transition-colors cursor-pointer group",
                                CardHeader {
                                    div {
                                        class: "flex justify-between items-start",
                                        h3 { class: "text-xl font-bold text-white group-hover:text-blue-300", "{campaign.name}" }
                                        Badge { variant: BadgeVariant::Default, "{campaign.system}" }
                                    }
                                }
                                CardBody {
                                    class: "space-y-4",
                                    if let Some(desc) = &campaign.description {
                                        p { class: "text-gray-400 text-sm line-clamp-2", "{desc}" }
                                    }
                                    div {
                                        class: "flex justify-between text-sm text-gray-500",
                                        span { "Sessions: {campaign.session_count}" }
                                        span { "Players: {campaign.player_count}" }
                                    }
                                    div {
                                        class: "flex gap-2 pt-2",
                                        Link {
                                            to: crate::Route::Session { campaign_id: campaign.id.clone() },
                                            class: "flex-1 px-3 py-2 bg-purple-600 rounded hover:bg-purple-500 text-white text-center text-sm font-medium transition-colors",
                                            "Play Session"
                                        }
                                        Button {
                                            variant: ButtonVariant::Danger,
                                            onclick: handle_delete(campaign.id.clone(), campaign.name.clone()),
                                            "Delete"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Create Modal
            Modal {
                is_open: modal_open,
                onclose: move |_| show_create_modal.set(false),
                title: "Create New Campaign",
                children: rsx! {
                    div {
                        class: "space-y-4",
                        div {
                            label { class: "block text-sm text-gray-400 mb-1", "Campaign Name" }
                            Input {
                                placeholder: "e.g. The Lost Mines",
                                value: "{new_campaign_name}",
                                oninput: move |e| new_campaign_name.set(e)
                            }
                        }
                        div {
                            label { class: "block text-sm text-gray-400 mb-1", "Game System" }
                            Select {
                                value: "{new_campaign_system}",
                                onchange: move |e| new_campaign_system.set(e),
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
                            div {
                                class: "flex justify-end gap-2 mt-6",
                                 Button {
                                    variant: ButtonVariant::Secondary,
                                    onclick: move |_| show_create_modal.set(false),
                                    "Cancel"
                                }
                            Button {
                                onclick: handle_create,
                                "Create Campaign"
                            }
                        }
                    }
                }
            }
        }
    }
}
