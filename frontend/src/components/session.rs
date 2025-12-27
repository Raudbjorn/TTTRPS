#![allow(non_snake_case)]
use dioxus::prelude::*;
use crate::bindings::{
    get_campaign, get_active_session, start_session, end_session,
    start_combat, end_combat, get_combat, add_combatant, remove_combatant,
    next_turn, damage_combatant, heal_combatant,
    Campaign, GameSession, CombatState
};

#[component]
pub fn Session(campaign_id: String) -> Element {
    let mut campaign = use_signal(|| Option::<Campaign>::None);
    let mut session = use_signal(|| Option::<GameSession>::None);
    let mut combat = use_signal(|| Option::<CombatState>::None);
    let mut status_message = use_signal(|| String::new());
    let mut is_loading = use_signal(|| true);

    // Add combatant form
    let mut new_combatant_name = use_signal(|| String::new());
    let mut new_combatant_init = use_signal(|| "10".to_string());
    let mut new_combatant_type = use_signal(|| "monster".to_string());

    let campaign_id_clone = campaign_id.clone();

    // Load campaign and active session on mount
    use_effect(move || {
        let campaign_id = campaign_id_clone.clone();
        spawn(async move {
            // Load campaign
            if let Ok(Some(c)) = get_campaign(campaign_id.clone()).await {
                campaign.set(Some(c));
            }

            // Check for active session
            if let Ok(Some(s)) = get_active_session(campaign_id.clone()).await {
                session.set(Some(s.clone()));
                // Load combat if session is active
                if let Ok(Some(c)) = get_combat(s.id).await {
                    combat.set(Some(c));
                }
            }

            is_loading.set(false);
        });
    });

    let campaign_id_for_start = campaign_id.clone();
    let handle_start_session = move |_: MouseEvent| {
        let campaign_id = campaign_id_for_start.clone();
        let session_num = campaign.read().as_ref().map(|c| c.session_count + 1).unwrap_or(1);
        spawn(async move {
            match start_session(campaign_id, session_num).await {
                Ok(s) => {
                    session.set(Some(s));
                    status_message.set("Session started!".to_string());
                }
                Err(e) => {
                    status_message.set(format!("Error: {}", e));
                }
            }
        });
    };

    let handle_end_session = move |_: MouseEvent| {
        if let Some(s) = session.read().as_ref() {
            let session_id = s.id.clone();
            spawn(async move {
                match end_session(session_id).await {
                    Ok(_) => {
                        session.set(None);
                        combat.set(None);
                        status_message.set("Session ended!".to_string());
                    }
                    Err(e) => {
                        status_message.set(format!("Error: {}", e));
                    }
                }
            });
        }
    };

    let handle_start_combat = move |_: MouseEvent| {
        if let Some(s) = session.read().as_ref() {
            let session_id = s.id.clone();
            spawn(async move {
                match start_combat(session_id).await {
                    Ok(c) => {
                        combat.set(Some(c));
                        status_message.set("Combat started!".to_string());
                    }
                    Err(e) => {
                        status_message.set(format!("Error: {}", e));
                    }
                }
            });
        }
    };

    let handle_end_combat = move |_: MouseEvent| {
        if let Some(s) = session.read().as_ref() {
            let session_id = s.id.clone();
            spawn(async move {
                match end_combat(session_id).await {
                    Ok(_) => {
                        combat.set(None);
                        status_message.set("Combat ended!".to_string());
                    }
                    Err(e) => {
                        status_message.set(format!("Error: {}", e));
                    }
                }
            });
        }
    };

    let handle_add_combatant = move |_: MouseEvent| {
        if let Some(s) = session.read().as_ref() {
            let session_id = s.id.clone();
            let name = new_combatant_name.read().clone();
            let init: i32 = new_combatant_init.read().parse().unwrap_or(10);
            let ctype = new_combatant_type.read().clone();

            if name.trim().is_empty() {
                status_message.set("Name is required".to_string());
                return;
            }

            spawn(async move {
                match add_combatant(session_id.clone(), name, init, ctype).await {
                    Ok(c) => {
                        if let Some(ref mut combat_state) = *combat.write() {
                            combat_state.combatants.push(c);
                            combat_state.combatants.sort_by(|a, b| b.initiative.cmp(&a.initiative));
                        }
                        new_combatant_name.set(String::new());
                        new_combatant_init.set("10".to_string());
                    }
                    Err(e) => {
                        status_message.set(format!("Error: {}", e));
                    }
                }
            });
        }
    };

    let handle_next_turn = move |_: MouseEvent| {
        if let Some(s) = session.read().as_ref() {
            let session_id = s.id.clone();
            spawn(async move {
                match next_turn(session_id.clone()).await {
                    Ok(_) => {
                        // Refresh combat state
                        if let Ok(Some(c)) = get_combat(session_id).await {
                            combat.set(Some(c));
                        }
                    }
                    Err(e) => {
                        status_message.set(format!("Error: {}", e));
                    }
                }
            });
        }
    };

    let handle_damage = move |combatant_id: String, amount: i32| {
        move |_: MouseEvent| {
            if let Some(s) = session.read().as_ref() {
                let session_id = s.id.clone();
                let cid = combatant_id.clone();
                spawn(async move {
                    match damage_combatant(session_id.clone(), cid.clone(), amount).await {
                        Ok(new_hp) => {
                            if let Some(ref mut combat_state) = *combat.write() {
                                if let Some(c) = combat_state.combatants.iter_mut().find(|c| c.id == cid) {
                                    c.hp_current = new_hp;
                                }
                            }
                        }
                        Err(e) => {
                            status_message.set(format!("Error: {}", e));
                        }
                    }
                });
            }
        }
    };

    let handle_heal = move |combatant_id: String, amount: i32| {
        move |_: MouseEvent| {
            if let Some(s) = session.read().as_ref() {
                let session_id = s.id.clone();
                let cid = combatant_id.clone();
                spawn(async move {
                    match heal_combatant(session_id.clone(), cid.clone(), amount).await {
                        Ok(new_hp) => {
                            if let Some(ref mut combat_state) = *combat.write() {
                                if let Some(c) = combat_state.combatants.iter_mut().find(|c| c.id == cid) {
                                    c.hp_current = new_hp;
                                }
                            }
                        }
                        Err(e) => {
                            status_message.set(format!("Error: {}", e));
                        }
                    }
                });
            }
        }
    };

    let handle_remove = move |combatant_id: String| {
        move |_: MouseEvent| {
            if let Some(s) = session.read().as_ref() {
                let session_id = s.id.clone();
                let cid = combatant_id.clone();
                spawn(async move {
                    match remove_combatant(session_id, cid.clone()).await {
                        Ok(_) => {
                            if let Some(ref mut combat_state) = *combat.write() {
                                combat_state.combatants.retain(|c| c.id != cid);
                            }
                        }
                        Err(e) => {
                            status_message.set(format!("Error: {}", e));
                        }
                    }
                });
            }
        }
    };

    let loading = *is_loading.read();
    let status = status_message.read().clone();
    let has_session = session.read().is_some();
    let has_combat = combat.read().is_some();
    let campaign_name = campaign.read().as_ref().map(|c| c.name.clone()).unwrap_or_else(|| "Loading...".to_string());

    rsx! {
        div {
            class: "p-8 bg-gray-900 text-white min-h-screen font-sans",
            div {
                class: "max-w-6xl mx-auto",
                // Header
                div {
                    class: "flex items-center justify-between mb-8",
                    div {
                        class: "flex items-center",
                        Link { to: crate::Route::Campaigns {}, class: "mr-4 text-gray-400 hover:text-white", "← Campaigns" }
                        h1 { class: "text-2xl font-bold", "{campaign_name}" }
                    }
                    div {
                        class: "flex gap-2",
                        if !has_session {
                            button {
                                onclick: handle_start_session,
                                class: "px-4 py-2 bg-green-600 rounded hover:bg-green-500",
                                "Start Session"
                            }
                        } else {
                            button {
                                onclick: handle_end_session,
                                class: "px-4 py-2 bg-red-600 rounded hover:bg-red-500",
                                "End Session"
                            }
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

                if loading {
                    div {
                        class: "text-center py-8 text-gray-500",
                        "Loading..."
                    }
                } else if !has_session {
                    div {
                        class: "text-center py-12 bg-gray-800 rounded-lg",
                        p { class: "text-gray-400 mb-4", "No active session" }
                        p { class: "text-gray-500 text-sm", "Start a session to begin tracking combat and encounters." }
                    }
                } else {
                    div {
                        class: "grid grid-cols-1 lg:grid-cols-3 gap-6",

                        // Combat Tracker (2/3 width)
                        div {
                            class: "lg:col-span-2 bg-gray-800 rounded-lg p-6",
                            div {
                                class: "flex justify-between items-center mb-4",
                                h2 { class: "text-xl font-semibold", "Combat Tracker" }
                                if !has_combat {
                                    button {
                                        onclick: handle_start_combat,
                                        class: "px-4 py-2 bg-red-600 rounded hover:bg-red-500",
                                        "Start Combat"
                                    }
                                } else {
                                    div {
                                        class: "flex gap-2",
                                        button {
                                            onclick: handle_next_turn,
                                            class: "px-4 py-2 bg-blue-600 rounded hover:bg-blue-500",
                                            "Next Turn"
                                        }
                                        button {
                                            onclick: handle_end_combat,
                                            class: "px-4 py-2 bg-gray-600 rounded hover:bg-gray-500",
                                            "End Combat"
                                        }
                                    }
                                }
                            }

                            if has_combat {
                                // Round indicator
                                if let Some(c) = combat.read().as_ref() {
                                    div {
                                        class: "mb-4 text-center",
                                        span { class: "text-lg font-bold text-yellow-400", "Round {c.round}" }
                                    }
                                }

                                // Combatant list
                                div {
                                    class: "space-y-2",
                                    if let Some(c) = combat.read().as_ref() {
                                        for (idx, combatant) in c.combatants.iter().enumerate() {
                                            div {
                                                key: "{combatant.id}",
                                                class: {
                                                    let is_current = idx == c.current_turn;
                                                    let is_down = combatant.hp_current <= 0;
                                                    if is_current {
                                                        "p-3 bg-yellow-900 border-2 border-yellow-500 rounded flex items-center gap-4"
                                                    } else if is_down {
                                                        "p-3 bg-gray-700 opacity-50 rounded flex items-center gap-4"
                                                    } else {
                                                        "p-3 bg-gray-700 rounded flex items-center gap-4"
                                                    }
                                                },
                                                // Initiative
                                                div {
                                                    class: "w-12 text-center",
                                                    span { class: "text-xl font-bold", "{combatant.initiative}" }
                                                }
                                                // Name and type
                                                div {
                                                    class: "flex-1",
                                                    div { class: "font-semibold", "{combatant.name}" }
                                                    div {
                                                        class: "text-xs text-gray-400",
                                                        "{combatant.combatant_type}"
                                                        if !combatant.conditions.is_empty() {
                                                            " - "
                                                            for cond in combatant.conditions.iter() {
                                                                span { class: "text-yellow-400", "{cond} " }
                                                            }
                                                        }
                                                    }
                                                }
                                                // HP
                                                div {
                                                    class: "flex items-center gap-2",
                                                    button {
                                                        onclick: handle_damage(combatant.id.clone(), 1),
                                                        class: "px-2 py-1 bg-red-700 rounded text-sm hover:bg-red-600",
                                                        "-1"
                                                    }
                                                    span {
                                                        class: if combatant.hp_current <= 0 { "text-red-400 font-bold" } else { "font-bold" },
                                                        "{combatant.hp_current}/{combatant.hp_max}"
                                                    }
                                                    button {
                                                        onclick: handle_heal(combatant.id.clone(), 1),
                                                        class: "px-2 py-1 bg-green-700 rounded text-sm hover:bg-green-600",
                                                        "+1"
                                                    }
                                                }
                                                // Remove button
                                                button {
                                                    onclick: handle_remove(combatant.id.clone()),
                                                    class: "px-2 py-1 text-red-400 hover:text-red-300",
                                                    "X"
                                                }
                                            }
                                        }
                                    }
                                }

                                // Add combatant form
                                div {
                                    class: "mt-4 pt-4 border-t border-gray-700",
                                    h3 { class: "text-sm font-semibold mb-2 text-gray-400", "Add Combatant" }
                                    div {
                                        class: "flex gap-2",
                                        input {
                                            class: "flex-1 p-2 bg-gray-700 rounded border border-gray-600 text-sm",
                                            placeholder: "Name",
                                            value: "{new_combatant_name}",
                                            oninput: move |e| new_combatant_name.set(e.value())
                                        }
                                        input {
                                            class: "w-16 p-2 bg-gray-700 rounded border border-gray-600 text-sm text-center",
                                            placeholder: "Init",
                                            value: "{new_combatant_init}",
                                            oninput: move |e| new_combatant_init.set(e.value())
                                        }
                                        select {
                                            class: "p-2 bg-gray-700 rounded border border-gray-600 text-sm",
                                            onchange: move |e| new_combatant_type.set(e.value()),
                                            option { value: "player", "Player" }
                                            option { value: "npc", "NPC" }
                                            option { value: "monster", selected: true, "Monster" }
                                            option { value: "ally", "Ally" }
                                        }
                                        button {
                                            onclick: handle_add_combatant,
                                            class: "px-4 py-2 bg-blue-600 rounded hover:bg-blue-500 text-sm",
                                            "Add"
                                        }
                                    }
                                }
                            } else {
                                div {
                                    class: "text-center py-8 text-gray-500",
                                    "Start combat to track initiative and HP"
                                }
                            }
                        }

                        // Session Info (1/3 width)
                        div {
                            class: "bg-gray-800 rounded-lg p-6",
                            h2 { class: "text-xl font-semibold mb-4", "Session Info" }
                            if let Some(s) = session.read().as_ref() {
                                div {
                                    class: "space-y-3",
                                    div {
                                        span { class: "text-gray-400", "Session #" }
                                        span { class: "ml-2 font-bold", "{s.session_number}" }
                                    }
                                    div {
                                        span { class: "text-gray-400", "Status: " }
                                        span { class: "ml-2 text-green-400", "{s.status}" }
                                    }
                                    div {
                                        span { class: "text-gray-400", "Started: " }
                                        span { class: "ml-2 text-sm", "{s.started_at}" }
                                    }
                                }
                            }

                            div {
                                class: "mt-6 pt-4 border-t border-gray-700",
                                h3 { class: "font-semibold mb-3", "Quick Actions" }
                                div {
                                    class: "space-y-2",
                                    Link {
                                        to: crate::Route::Chat {},
                                        class: "block w-full px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 text-center text-sm",
                                        "Ask the GM"
                                    }
                                    Link {
                                        to: crate::Route::CharacterCreator {},
                                        class: "block w-full px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 text-center text-sm",
                                        "Generate NPC"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
