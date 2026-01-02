use leptos::prelude::*;


#[component]
pub fn Slider(
    #[prop(into)] value: Signal<f32>,
    #[prop(into)] on_input: Callback<f32>,
    #[prop(default = 0.0)] min: f32,
    #[prop(default = 1.0)] max: f32,
    #[prop(default = 0.01)] step: f32,
    #[prop(optional, into)] label: MaybeProp<String>,
    #[prop(into, default = Signal::derive(|| false))] disabled: Signal<bool>,
) -> impl IntoView {
    let id = format!("slider-{:x}", (js_sys::Math::random() * 1e16) as u64);

    view! {
        <div class="flex flex-col gap-1 w-full">
            {
                let id = id.clone();
                move || label.get().map(|l| view! {
                    <div class="flex justify-between text-xs text-[var(--text-muted)]">
                        <label for={id.clone()}>{l}</label>
                        <span>{format!("{:.0}%", value.get() * 100.0)}</span>
                    </div>
                })
            }
            <input
                id=id
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
