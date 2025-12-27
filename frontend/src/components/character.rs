#![allow(non_snake_case)]
use dioxus::prelude::*;
use crate::bindings::{generate_character, get_supported_systems, GenerationOptions, Character};

#[component]
pub fn CharacterCreator() -> Element {
    let mut systems = use_signal(|| Vec::<String>::new());
    let mut selected_system = use_signal(|| "D&D 5e".to_string());
    let mut character_name = use_signal(|| String::new());
    let mut character_type = use_signal(|| String::new());
    let mut character_level = use_signal(|| "1".to_string());
    let mut include_backstory = use_signal(|| true);

    let mut generated_character = use_signal(|| Option::<Character>::None);
    let mut is_generating = use_signal(|| false);
    let mut status_message = use_signal(|| String::new());

    // Load supported systems
    use_effect(move || {
        spawn(async move {
            if let Ok(list) = get_supported_systems().await {
                systems.set(list);
            }
        });
    });

    let handle_generate = move |_: MouseEvent| {
        is_generating.set(true);
        status_message.set("Generating character...".to_string());

        let system = selected_system.read().clone();
        let name = character_name.read().clone();
        let ctype = character_type.read().clone();
        let level: u32 = character_level.read().parse().unwrap_or(1);
        let backstory = *include_backstory.read();

        spawn(async move {
            let options = GenerationOptions {
                system,
                character_type: if ctype.is_empty() { None } else { Some(ctype) },
                level: Some(level),
                name: if name.is_empty() { None } else { Some(name) },
                include_backstory: backstory,
            };

            match generate_character(options).await {
                Ok(character) => {
                    generated_character.set(Some(character));
                    status_message.set("Character generated!".to_string());
                }
                Err(e) => {
                    status_message.set(format!("Error: {}", e));
                }
            }
            is_generating.set(false);
        });
    };

    let clear_character = move |_: MouseEvent| {
        generated_character.set(None);
        character_name.set(String::new());
        character_type.set(String::new());
        status_message.set(String::new());
    };

    let generating = *is_generating.read();
    let status = status_message.read().clone();
    let has_character = generated_character.read().is_some();

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
                        h1 { class: "text-2xl font-bold", "Character Generator" }
                    }
                    if has_character {
                        button {
                            onclick: clear_character,
                            class: "px-4 py-2 bg-gray-600 rounded hover:bg-gray-500",
                            "New Character"
                        }
                    }
                }

                // Status
                if !status.is_empty() {
                    div {
                        class: "mb-4 p-3 bg-gray-800 rounded text-sm",
                        "{status}"
                    }
                }

                div {
                    class: "grid grid-cols-1 lg:grid-cols-2 gap-6",

                    // Generator Form
                    div {
                        class: "bg-gray-800 rounded-lg p-6",
                        h2 { class: "text-xl font-semibold mb-4", "Generation Options" }

                        div {
                            class: "space-y-4",
                            // System selection
                            div {
                                label { class: "block text-sm text-gray-400 mb-1", "Game System" }
                                select {
                                    class: "w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none",
                                    onchange: move |e| selected_system.set(e.value()),
                                    for system in systems.read().iter() {
                                        option {
                                            value: "{system}",
                                            selected: *selected_system.read() == *system,
                                            "{system}"
                                        }
                                    }
                                    if systems.read().is_empty() {
                                        option { value: "D&D 5e", "D&D 5e" }
                                        option { value: "Pathfinder 2e", "Pathfinder 2e" }
                                        option { value: "Call of Cthulhu", "Call of Cthulhu" }
                                    }
                                }
                            }

                            // Character name (optional)
                            div {
                                label { class: "block text-sm text-gray-400 mb-1", "Character Name (optional)" }
                                input {
                                    class: "w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none",
                                    placeholder: "Leave blank for random name",
                                    value: "{character_name}",
                                    oninput: move |e| character_name.set(e.value())
                                }
                            }

                            // Character type/class (optional)
                            div {
                                label { class: "block text-sm text-gray-400 mb-1", "Class/Type (optional)" }
                                input {
                                    class: "w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none",
                                    placeholder: "e.g., Fighter, Wizard, Investigator",
                                    value: "{character_type}",
                                    oninput: move |e| character_type.set(e.value())
                                }
                            }

                            // Level
                            div {
                                label { class: "block text-sm text-gray-400 mb-1", "Level" }
                                input {
                                    class: "w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none",
                                    r#type: "number",
                                    min: "1",
                                    max: "20",
                                    value: "{character_level}",
                                    oninput: move |e| character_level.set(e.value())
                                }
                            }

                            // Backstory toggle
                            div {
                                class: "flex items-center gap-2",
                                input {
                                    r#type: "checkbox",
                                    class: "w-4 h-4",
                                    checked: *include_backstory.read(),
                                    onchange: move |_| {
                                        let current = *include_backstory.read();
                                        include_backstory.set(!current);
                                    }
                                }
                                label { class: "text-sm text-gray-400", "Generate backstory" }
                            }

                            // Generate button
                            button {
                                onclick: handle_generate,
                                disabled: generating,
                                class: if generating {
                                    "w-full py-3 bg-gray-600 rounded cursor-not-allowed mt-4"
                                } else {
                                    "w-full py-3 bg-purple-600 rounded hover:bg-purple-500 mt-4 font-semibold"
                                },
                                if generating { "Generating..." } else { "Generate Character" }
                            }
                        }
                    }

                    // Character Display
                    div {
                        class: "bg-gray-800 rounded-lg p-6",
                        h2 { class: "text-xl font-semibold mb-4", "Generated Character" }

                        if let Some(character) = generated_character.read().as_ref() {
                            div {
                                class: "space-y-4",
                                // Header
                                div {
                                    class: "border-b border-gray-700 pb-4",
                                    h3 { class: "text-2xl font-bold text-purple-400", "{character.name}" }
                                    div {
                                        class: "flex gap-2 mt-2",
                                        span { class: "text-xs px-2 py-1 bg-blue-900 text-blue-300 rounded", "{character.system}" }
                                        span { class: "text-xs px-2 py-1 bg-purple-900 text-purple-300 rounded", "{character.character_type}" }
                                        if let Some(level) = character.level {
                                            span { class: "text-xs px-2 py-1 bg-green-900 text-green-300 rounded", "Level {level}" }
                                        }
                                    }
                                }

                                // Attributes
                                div {
                                    h4 { class: "font-semibold text-gray-300 mb-2", "Attributes" }
                                    div {
                                        class: "grid grid-cols-3 gap-2",
                                        for attr in character.attributes.iter() {
                                            div {
                                                class: "p-2 bg-gray-700 rounded text-center",
                                                div { class: "text-xs text-gray-400", "{attr.name}" }
                                                div { class: "text-lg font-bold", "{attr.value}" }
                                                if let Some(mod_val) = attr.modifier {
                                                    div {
                                                        class: if mod_val >= 0 { "text-xs text-green-400" } else { "text-xs text-red-400" },
                                                        if mod_val >= 0 { "+{mod_val}" } else { "{mod_val}" }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // Skills
                                if !character.skills.is_empty() {
                                    div {
                                        h4 { class: "font-semibold text-gray-300 mb-2", "Skills" }
                                        div {
                                            class: "flex flex-wrap gap-2",
                                            for skill in character.skills.iter() {
                                                span { class: "px-2 py-1 bg-gray-700 rounded text-sm", "{skill}" }
                                            }
                                        }
                                    }
                                }

                                // Backstory
                                if let Some(backstory) = &character.backstory {
                                    div {
                                        h4 { class: "font-semibold text-gray-300 mb-2", "Backstory" }
                                        p { class: "text-gray-400 text-sm whitespace-pre-wrap", "{backstory}" }
                                    }
                                }
                            }
                        } else {
                            div {
                                class: "text-center py-12 text-gray-500",
                                p { "No character generated yet" }
                                p { class: "text-sm mt-2", "Configure options and click Generate" }
                            }
                        }
                    }
                }

                // Tips
                div {
                    class: "mt-6 p-4 bg-gray-800 rounded-lg",
                    h3 { class: "font-semibold mb-2", "Tips" }
                    ul {
                        class: "text-sm text-gray-400 space-y-1",
                        li { "Leave name and class blank for fully random generation" }
                        li { "Generated characters use system-appropriate stats and skills" }
                        li { "Backstories are procedurally generated based on class and system" }
                        li { "You can regenerate as many times as you like" }
                    }
                }
            }
        }
    }
}
