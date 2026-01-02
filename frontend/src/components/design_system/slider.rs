use leptos::prelude::*;


#[component]
pub fn Slider(
    #[prop(into)] value: Signal<f32>,
    #[prop(into)] on_input: Callback<f32>,
    #[prop(default = 0.0)] min: f32,
    #[prop(default = 1.0)] max: f32,
    #[prop(default = 0.01)] step: f32,
    #[prop(optional, into)] label: Option<String>,
    #[prop(optional, into)] disabled: Signal<bool>,
) -> impl IntoView {
    view! {
        <div class="flex flex-col gap-1 w-full">
            {move || label.clone().map(|l| view! {
                <div class="flex justify-between text-xs text-[var(--text-muted)]">
                    <span>{l}</span>
                    <span>{format!("{:.0}%", value.get() * 100.0)}</span>
                </div>
            })}
            <input
                type="range"
                min=min.to_string()
                max=max.to_string()
                step=step.to_string()
                class="w-full h-2 bg-[var(--bg-elevated)] rounded-lg appearance-none cursor-pointer accent-[var(--accent)] disabled:opacity-50 disabled:cursor-not-allowed"
                prop:value=move || value.get().to_string()
                prop:disabled=move || disabled.get()
                on:input=move |e| {
                    if let Ok(val) = event_target_value(&e).parse::<f32>() {
                        on_input.run(val);
                    }
                }
            />
        </div>
    }
}
