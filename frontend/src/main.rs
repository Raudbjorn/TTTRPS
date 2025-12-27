#![allow(non_snake_case)]

use dioxus::prelude::*;

mod components {
    pub mod chat;
    pub mod settings;
    pub mod library;
}
use components::chat::Chat;
use components::settings::Settings;
use components::library::Library;

#[derive(Clone, Routable, Debug, PartialEq)]
pub enum Route {
    #[route("/")]
    Chat {},
    #[route("/settings")]
    Settings {},
    #[route("/library")]
    Library {},
}

fn main() {
    tracing_wasm::set_as_global_default();
    tracing::info!("Starting TTRPG Assistant Frontend");
    launch(App);
}

// Global Theme Signal
pub type ThemeSignal = Signal<String>;

fn App() -> Element {
    // Initialize theme signal
    use_context_provider(|| Signal::new("fantasy".to_string()));
    let mut theme_sig = use_context::<ThemeSignal>();

    // Effect to update body attribute
    use_effect(move || {
        let current_theme = theme_sig.read();
        let _ = document::eval(&format!("document.body.setAttribute('data-theme', '{}')", current_theme));
    });

    rsx! {
        Router::<Route> {}
    }
}
