use dioxus::prelude::*;
use crate::components::design_system::{Card, CardHeader, CardBody};

#[component]
pub fn ThemeSettings() -> Element {
    // Current weights
    let mut fantasy = use_signal(|| 100);
    let mut cosmic = use_signal(|| 0);
    let mut terminal = use_signal(|| 0);
    let mut noir = use_signal(|| 0);
    let mut neon = use_signal(|| 0);

    // Derived total for normalization display
    let total = use_memo(move || {
        fantasy() + cosmic() + terminal() + noir() + neon()
    });



    rsx! {
        Card {
            CardHeader { h2 { class: "text-lg font-semibold", "Theme Blending" } }
            CardBody { class: "space-y-6",
                div { class: "grid gap-6",
                    // Fantasy Slider
                    div {
                        div { class: "flex justify-between mb-2",
                            label { class: "text-sm font-medium text-theme-secondary", "Fantasy (Arcane)" }
                            span { class: "text-sm text-theme-primary", "{fantasy}%" }
                        }
                        input {
                            r#type: "range",
                            min: "0", max: "100",
                            class: "w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500",
                            value: "{fantasy}",
                            oninput: move |e| fantasy.set(e.value().parse().unwrap_or(0))
                        }
                    }

                    // Cosmic Slider
                    div {
                        div { class: "flex justify-between mb-2",
                            label { class: "text-sm font-medium text-theme-secondary", "Cosmic (Eldritch)" }
                            span { class: "text-sm text-theme-primary", "{cosmic}%" }
                        }
                        input {
                            r#type: "range",
                            min: "0", max: "100",
                            class: "w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-indigo-500",
                            value: "{cosmic}",
                            oninput: move |e| cosmic.set(e.value().parse().unwrap_or(0))
                        }
                    }

                    // Terminal Slider
                    div {
                        div { class: "flex justify-between mb-2",
                            label { class: "text-sm font-medium text-theme-secondary", "Terminal (Retro)" }
                            span { class: "text-sm text-theme-primary", "{terminal}%" }
                        }
                        input {
                            r#type: "range",
                            min: "0", max: "100",
                            class: "w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500",
                            value: "{terminal}",
                            oninput: move |e| terminal.set(e.value().parse().unwrap_or(0))
                        }
                    }

                    // Noir Slider
                    div {
                        div { class: "flex justify-between mb-2",
                            label { class: "text-sm font-medium text-theme-secondary", "Noir (Detective)" }
                            span { class: "text-sm text-theme-primary", "{noir}%" }
                        }
                        input {
                            r#type: "range",
                            min: "0", max: "100",
                            class: "w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-gray-400",
                            value: "{noir}",
                            oninput: move |e| noir.set(e.value().parse().unwrap_or(0))
                        }
                    }

                    // Neon Slider
                    div {
                        div { class: "flex justify-between mb-2",
                            label { class: "text-sm font-medium text-theme-secondary", "Neon (Cyberpunk)" }
                            span { class: "text-sm text-theme-primary", "{neon}%" }
                        }
                        input {
                            r#type: "range",
                            min: "0", max: "100",
                            class: "w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-pink-500",
                            value: "{neon}",
                            oninput: move |e| neon.set(e.value().parse().unwrap_or(0))
                        }
                    }
                }

                // Preview / Status
                div { class: "bg-black/20 p-4 rounded text-center text-sm text-zinc-400",
                    if total() != 100 {
                         div { class: "text-yellow-500 mb-1", "⚠ Total weight: {total()}% (Should be 100%)" }
                    }
                    "Live preview enabled. Adjust sliders to blend themes."
                }
            }
        }
    }
}
