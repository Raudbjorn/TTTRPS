use dioxus::prelude::*;
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;

#[component]
pub fn CommandPalette() -> Element {
    let mut is_open = use_signal(|| false);
    let mut search_query = use_signal(|| String::new());

    // Toggle on Ctrl+K or Cmd+K
    // We utilize use_effect to attach the listener once. The closure must be 'static or handled carefully.
    // For simplicity in Dioxus 0.5 with signals, we can wrap the state update in a spawn or just use the closure.
    // However, attaching to window requires web_sys.
    use_effect(move || {
        let mut handle_keydown = Closure::wrap(Box::new(move |e: web_sys::KeyboardEvent| {
             if (e.ctrl_key() || e.meta_key()) && e.key() == "k" {
                 e.prevent_default();
                 let current = is_open();
                 is_open.set(!current);
             }
             if e.key() == "Escape" {
                 is_open.set(false);
             }
        }) as Box<dyn FnMut(_)>);

        if let Some(window) = web_sys::window() {
            let _ = window.add_event_listener_with_callback("keydown", handle_keydown.as_ref().unchecked_ref());
        }

        // We need to keep the closure alive. In a real app we'd store it and remove on unmount.
        // For now, leaking it is acceptable for a root component.
        handle_keydown.forget();
    });

    if !is_open() {
        return rsx! {};
    }

    rsx! {
        div {
            class: "fixed inset-0 z-[100] flex items-start justify-center pt-[20vh] bg-black/50 backdrop-blur-sm",
            onclick: move |_| is_open.set(false),
            div {
                class: "w-full max-w-2xl bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100",
                onclick: |e| e.stop_propagation(),
                // Input
                div { class: "flex items-center px-4 py-3 border-b border-zinc-800",
                    svg { class: "w-5 h-5 text-zinc-500 mr-3", view_box: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "2", path { d: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" } }
                    input {
                        class: "w-full bg-transparent border-none text-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-0",
                        placeholder: "Type a command or search...",
                        value: "{search_query}",
                        oninput: move |e| search_query.set(e.value()),
                        autofocus: true,
                    }
                }
                // Results (Static for now)
                div { class: "max-h-[60vh] overflow-y-auto p-2",
                    div { class: "px-2 py-1 text-xs font-semibold text-zinc-500", "SUGGESTIONS" }
                    button { class: "w-full text-left px-3 py-2 rounded-md hover:bg-zinc-800 text-zinc-300 flex items-center gap-3",
                        span { class: "p-1 bg-zinc-800 rounded bg-blue-500/20 text-blue-400 font-mono text-xs", "NPC" }
                        "Generate new NPC"
                    }
                    button { class: "w-full text-left px-3 py-2 rounded-md hover:bg-zinc-800 text-zinc-300 flex items-center gap-3",
                        span { class: "p-1 bg-zinc-800 rounded bg-green-500/20 text-green-400 font-mono text-xs", "SESSION" }
                        "Start new session"
                    }
                     button { class: "w-full text-left px-3 py-2 rounded-md hover:bg-zinc-800 text-zinc-300 flex items-center gap-3",
                        span { class: "p-1 bg-zinc-800 rounded bg-purple-500/20 text-purple-400 font-mono text-xs", "THEME" }
                        "Change Theme: Cyberpunk"
                    }
                }
                div { class: "border-t border-zinc-800 px-4 py-2 flex justify-between items-center text-xs text-zinc-500",
                    div { class: "flex gap-4",
                        span { class: "flex items-center gap-1", kbd { class: "px-1 bg-zinc-800 rounded text-zinc-400", "↑↓" } " navigate" }
                        span { class: "flex items-center gap-1", kbd { class: "px-1 bg-zinc-800 rounded text-zinc-400", "↵" } " select" }
                    }
                    span { class: "flex items-center gap-1", kbd { class: "px-1 bg-zinc-800 rounded text-zinc-400", "esc" } " close" }
                }
            }
        }
    }
}
