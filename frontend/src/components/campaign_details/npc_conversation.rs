use leptos::prelude::*;
use leptos::ev;
use wasm_bindgen_futures::spawn_local;
use crate::bindings::{
    get_npc_conversation, add_npc_message, mark_npc_read, reply_as_npc,
    speak_as_npc, ConversationMessage,
};
use crate::components::design_system::Markdown;
use crate::services::notification_service::show_error;
use crate::utils::play_audio_base64;

/// NPC Conversation component for chat-style messaging with NPCs
#[component]
pub fn NpcConversation(
    /// NPC ID to load conversation for
    npc_id: String,
    /// NPC name for display
    npc_name: String,
    /// Optional campaign ID for campaign-specific voice
    #[prop(default = None)]
    campaign_id: Option<String>,
    /// Callback when the conversation is closed
    on_close: Callback<()>,
) -> impl IntoView {
    let messages = RwSignal::new(Vec::<ConversationMessage>::new());
    let is_loading = RwSignal::new(true);
    let is_sending = RwSignal::new(false);
    let is_typing = RwSignal::new(false);
    let input_text = RwSignal::new(String::new());
    let error_msg = RwSignal::new(Option::<String>::None);

    let npc_id_signal = RwSignal::new(npc_id.clone());
    let npc_id_for_messages = npc_id.clone();
    let campaign_id_for_messages = campaign_id.clone();
    let npc_name_display = npc_name.clone();
    let npc_name_input = npc_name.clone();
    let npc_initial = npc_name.chars().next().unwrap_or('?');

    // Load conversation on mount
    Effect::new(move |_| {
        let npc_id = npc_id_signal.get();
        spawn_local(async move {
            match get_npc_conversation(npc_id.clone()).await {
                Ok(conv) => {
                    let parsed: Vec<ConversationMessage> =
                        serde_json::from_str(&conv.messages_json).unwrap_or_default();
                    messages.set(parsed);
                    let _ = mark_npc_read(npc_id).await;
                }
                Err(e) => {
                    if !e.contains("not found") {
                        error_msg.set(Some(e));
                    }
                }
            }
            is_loading.set(false);
        });
    });

    let do_send = move || {
        let text = input_text.get().trim().to_string();
        if text.is_empty() || is_sending.get() {
            return;
        }

        input_text.set(String::new());
        is_sending.set(true);
        let npc_id = npc_id_signal.get();

        spawn_local(async move {
            match add_npc_message(npc_id.clone(), text.clone(), "user".to_string(), None).await {
                Ok(msg) => {
                    messages.update(|m| m.push(msg));
                    is_typing.set(true);
                    match reply_as_npc(npc_id.clone()).await {
                        Ok(ai_msg) => {
                            messages.update(|m| m.push(ai_msg));
                        }
                        Err(e) => {
                            web_sys::console::log_1(&format!("NPC failed to reply: {}", e).into());
                        }
                    }
                    is_typing.set(false);
                }
                Err(e) => {
                    error_msg.set(Some(format!("Failed to send: {}", e)));
                }
            }
            is_sending.set(false);
        });
    };

    let handle_click = move |_: ev::MouseEvent| {
        do_send();
    };

    let handle_keydown = move |evt: ev::KeyboardEvent| {
        if evt.key() == "Enter" && !evt.shift_key() {
            evt.prevent_default();
            do_send();
        }
    };

    view! {
        <div class="flex flex-col h-full bg-zinc-950">
            <ConversationHeader
                npc_initial=npc_initial
                npc_name=npc_name_display
                on_close=on_close
            />
            <MessagesArea
                messages=messages
                is_loading=is_loading
                is_typing=is_typing
                error_msg=error_msg
                npc_name=npc_name.clone()
                npc_id=npc_id_for_messages.clone()
                campaign_id=campaign_id_for_messages.clone()
            />
            <InputArea
                input_text=input_text
                is_sending=is_sending
                npc_name=npc_name_input
                on_keydown=handle_keydown
                on_click=handle_click
            />
        </div>
    }
}

#[component]
fn ConversationHeader(
    npc_initial: char,
    npc_name: String,
    on_close: Callback<()>,
) -> impl IntoView {
    view! {
        <div class="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-[var(--accent)] font-bold border border-[var(--accent)]/40">
                    {npc_initial.to_string()}
                </div>
                <div>
                    <h2 class="font-bold text-white">{npc_name}</h2>
                    <p class="text-xs text-zinc-500">"NPC Conversation"</p>
                </div>
            </div>
            <button
                class="p-2 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded transition-colors"
                aria-label="Close conversation"
                on:click=move |_| on_close.run(())
            >
                "×"
            </button>
        </div>
    }
}

#[component]
fn MessagesArea(
    messages: RwSignal<Vec<ConversationMessage>>,
    is_loading: RwSignal<bool>,
    is_typing: RwSignal<bool>,
    error_msg: RwSignal<Option<String>>,
    npc_name: String,
    npc_id: String,
    campaign_id: Option<String>,
) -> impl IntoView {
    let npc_id_signal = RwSignal::new(npc_id);
    let campaign_id_signal = RwSignal::new(campaign_id);

    view! {
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
            {move || {
                let npc_id = npc_id_signal.get();
                let campaign_id = campaign_id_signal.get();
                if is_loading.get() {
                    view! {
                        <div class="flex items-center justify-center h-full text-zinc-500">
                            "Loading conversation..."
                        </div>
                    }.into_any()
                } else if let Some(err) = error_msg.get() {
                    view! {
                        <div class="flex items-center justify-center h-full text-red-400">
                            {err}
                        </div>
                    }.into_any()
                } else if messages.get().is_empty() {
                    let name = npc_name.clone();
                    view! {
                        <div class="flex flex-col items-center justify-center h-full text-zinc-500">
                            <p>"No messages yet"</p>
                            <p class="text-sm">{format!("Start a conversation with {}", name)}</p>
                        </div>
                    }.into_any()
                } else {
                    view! {
                        <For
                            each=move || messages.get()
                            key=|msg| msg.id.clone()
                            children={
                                let npc_id = npc_id.clone();
                                let campaign_id = campaign_id.clone();
                                move |msg| {
                                    view! {
                                        <MessageBubble
                                            msg=msg
                                            npc_id=npc_id.clone()
                                            campaign_id=campaign_id.clone()
                                        />
                                    }
                                }
                            }
                        />
                    }.into_any()
                }
            }}
            <Show when=move || is_typing.get() fallback=|| ()>
                <div class="flex justify-start">
                    <div class="bg-zinc-800 border border-zinc-700 rounded-lg p-3">
                        <span class="text-xs text-zinc-500">"Typing..."</span>
                    </div>
                </div>
            </Show>
        </div>
    }
}

#[component]
fn MessageBubble(
    msg: ConversationMessage,
    npc_id: String,
    campaign_id: Option<String>,
) -> impl IntoView {
    let is_user = msg.role == "user";
    let msg_content = msg.content.clone();
    let msg_content_for_play = msg.content.clone();
    let timestamp = msg.created_at.clone();
    let is_playing = RwSignal::new(false);

    let outer_class = if is_user { "flex justify-end" } else { "flex justify-start" };
    let bubble_class = if is_user {
        "max-w-[80%] bg-[var(--accent)]/20 border border-[var(--accent)]/30 rounded-lg p-3"
    } else {
        "max-w-[80%] bg-zinc-800 border border-zinc-700 rounded-lg p-3 group"
    };

    // Play button handler for NPC messages
    let play_handler = move |_: ev::MouseEvent| {
        if is_playing.get() {
            return;
        }
        // Clone values once here before moving into async block
        let npc_id = npc_id.clone();
        let campaign_id = campaign_id.clone();
        let content = msg_content_for_play.clone();
        is_playing.set(true);

        spawn_local(async move {
            match speak_as_npc(content, npc_id, campaign_id).await {
                Ok(Some(result)) => {
                    if let Err(e) = play_audio_base64(&result.audio_data, &result.format) {
                        show_error("Voice Error", Some(&format!("Failed to play audio: {}", e)), None);
                    }
                }
                Ok(None) => {
                    // Voice is disabled, silently ignore
                }
                Err(e) => {
                    show_error("Voice Error", Some(&e), None);
                }
            }
            is_playing.set(false);
        });
    };

    // Play button only for NPC messages (not user messages)
    let play_button = if !is_user {
        Some(view! {
            <button
                class="p-1 rounded hover:bg-zinc-700 text-zinc-500 hover:text-green-400 transition-colors opacity-0 group-hover:opacity-100"
                title="Read aloud"
                disabled=move || is_playing.get()
                on:click=play_handler
            >
                {move || if is_playing.get() {
                    view! {
                        <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10" stroke-opacity="0.25" />
                            <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round" />
                        </svg>
                    }.into_any()
                } else {
                    view! {
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8 5v14l11-7z" />
                        </svg>
                    }.into_any()
                }}
            </button>
        })
    } else {
        None
    };

    view! {
        <div class=outer_class>
            <div class=bubble_class>
                {if is_user {
                    view! { <p class="text-zinc-100 whitespace-pre-wrap">{msg_content}</p> }.into_any()
                } else {
                    view! { <Markdown content=msg_content /> }.into_any()
                }}
                <div class="flex items-center justify-between mt-2">
                    <p class="text-xs text-zinc-500">{format_timestamp(&timestamp)}</p>
                    {play_button}
                </div>
            </div>
        </div>
    }
}

#[component]
fn InputArea(
    input_text: RwSignal<String>,
    is_sending: RwSignal<bool>,
    npc_name: String,
    on_keydown: impl Fn(ev::KeyboardEvent) + 'static,
    on_click: impl Fn(ev::MouseEvent) + 'static,
) -> impl IntoView {
    view! {
        <div class="p-4 border-t border-zinc-900 bg-zinc-900">
            <div class="flex gap-2">
                <textarea
                    class="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white placeholder-zinc-500 resize-none focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
                    placeholder=format!("Message {}...", npc_name)
                    rows="1"
                    prop:value=move || input_text.get()
                    prop:disabled=move || is_sending.get()
                    on:input=move |evt| input_text.set(event_target_value(&evt))
                    on:keydown=on_keydown
                />
                <button
                    class="px-4 py-2 bg-[var(--accent)] hover:brightness-110 text-white rounded-lg font-medium transition-all disabled:opacity-50"
                    prop:disabled=move || input_text.get().trim().is_empty() || is_sending.get()
                    on:click=on_click
                >
                    {move || if is_sending.get() { "..." } else { "Send" }}
                </button>
            </div>
            <p class="text-xs text-zinc-600 mt-2">"Press Enter to send, Shift+Enter for new line"</p>
        </div>
    }
}

fn format_timestamp(iso: &str) -> String {
    if let Some(time_part) = iso.split('T').nth(1) {
        if let Some(hm) = time_part.get(0..5) {
            return hm.to_string();
        }
    }
    iso.to_string()
}
