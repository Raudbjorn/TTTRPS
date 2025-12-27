#![allow(non_snake_case)]
use dioxus::prelude::*;
use serde::{Deserialize, Serialize};
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = ["window", "__TAURI__", "core"])]
    async fn invoke(cmd: &str, args: JsValue) -> JsValue;
}

#[derive(Serialize, Deserialize)]
struct ChatRequest {
    message: String,
}

#[derive(Serialize, Deserialize)]
struct ChatResponse {
    content: String,
    model: String,
}

#[derive(Serialize, Deserialize)]
struct SpeakRequest {
    text: String,
}

#[component]
pub fn Chat() -> Element {
    let mut message_input = use_signal(|| String::new());
    let mut messages = use_signal(|| vec![
        ("assistant".to_string(), "Welcome to the Rust-powered TTRPG Assistant! I am ready to help you run your campaign.".to_string())
    ]);

    let play_message = move |text: String| {
        spawn(async move {
            let args = serde_wasm_bindgen::to_value(&SpeakRequest { text }).unwrap();
            let _ = invoke("speak", args).await;
        });
    };

    let send_message = move |_: MouseEvent| {
        let msg = message_input.read().clone();
        if !msg.trim().is_empty() {
            messages.write().push(("user".to_string(), msg.clone()));
            message_input.set(String::new());

            let msg_clone = msg.clone();
            spawn(async move {
                let args = serde_wasm_bindgen::to_value(&ChatRequest { message: msg_clone }).unwrap();
                let result = invoke("chat", args).await;

                let response: Result<ChatResponse, _> = serde_wasm_bindgen::from_value(result);

                if let Ok(resp) = response {
                     messages.write().push(("assistant".to_string(), resp.content));
                } else {
                     messages.write().push(("assistant".to_string(), "Error connecting to LLM.".to_string()));
                }
            });
        }
    };

    rsx! {
        div {
            class: "flex flex-col h-screen bg-theme-primary text-theme-primary font-sans transition-colors duration-300",
            // Header
            div {
                class: "p-4 bg-theme-secondary border-b border-theme flex justify-between items-center",
                h1 { class: "text-xl font-bold", "Sidecar DM" }
                div {
                    class: "flex gap-4",
                    Link { to: crate::Route::Library {}, class: "text-theme-secondary hover:text-theme-primary", "Library" }
                    Link { to: crate::Route::Settings {}, class: "text-theme-secondary hover:text-theme-primary", "Settings" }
                }
            }
            // Message Area
            div {
                class: "flex-1 p-4 overflow-y-auto space-y-4",
                for (role, content) in messages.read().iter() {
                    div {
                        class: if role == "user" { "bg-blue-800 p-3 rounded-lg max-w-3xl ml-auto" } else { "bg-theme-secondary p-3 rounded-lg max-w-3xl group relative border border-theme" },
                        if role == "assistant" {
                            div {
                                class: "absolute -left-10 top-1 opacity-0 group-hover:opacity-100 transition-opacity",
                                button {
                                    class: "p-2 bg-gray-700 rounded-full hover:bg-gray-600 text-gray-300 hover:text-white",
                                    title: "Read Aloud",
                                    onclick: {
                                        let c = content.clone();
                                        move |_| play_message(c.clone())
                                    },
                                    // Simple Play Icon SVG
                                    svg {
                                        class: "w-4 h-4",
                                        view_box: "0 0 24 24",
                                        fill: "none",
                                        stroke: "currentColor",
                                        "stroke-width": "2",
                                        path {
                                            d: "M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                                        }
                                        path {
                                            d: "M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        }
                                    }
                                }
                            }
                        }
                        "{content}"
                    }
                }
            }
            // Input Area
            div {
                class: "p-4 bg-theme-secondary border-t border-theme",
                div {
                    class: "flex gap-2",
                    input {
                        class: "flex-1 p-2 rounded bg-theme-primary text-theme-primary border border-theme focus:border-blue-500 outline-none placeholder-theme-secondary",
                        placeholder: "Ask the DM...",
                        value: "{message_input}",
                        oninput: move |e| message_input.set(e.value()),
                        onkeydown: move |e: KeyboardEvent| {
                            if e.key() == Key::Enter {
                                let msg = message_input.read().clone();
                                if !msg.trim().is_empty() {
                                    messages.write().push(("user".to_string(), msg.clone()));
                                    message_input.set(String::new());

                                    let msg_clone = msg.clone();
                                    spawn(async move {
                                        let args = serde_wasm_bindgen::to_value(&ChatRequest { message: msg_clone }).unwrap();
                                        let result = invoke("chat", args).await;
                                        let response: Result<ChatResponse, _> = serde_wasm_bindgen::from_value(result);

                                        if let Ok(resp) = response {
                                            messages.write().push(("assistant".to_string(), resp.content));
                                        } else {
                                            messages.write().push(("assistant".to_string(), "Error connecting to LLM.".to_string()));
                                        }
                                    });
                                }
                            }
                        }
                    }
                    button {
                        class: "px-4 py-2 bg-blue-600 rounded hover:bg-blue-500 transition-colors",
                        onclick: send_message,
                        "Send"
                    }
                }
            }
        }
    }
}
