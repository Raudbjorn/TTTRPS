//! Audio playback utilities

use wasm_bindgen::JsCast;

/// Play base64-encoded audio using the browser's Audio API
pub fn play_audio_base64(audio_data: &str, format: &str) -> Result<(), String> {
    let window = web_sys::window().ok_or("No window object")?;
    let document = window.document().ok_or("No document object")?;

    let mime_type = match format {
        "wav" => "audio/wav",
        "mp3" => "audio/mpeg",
        "ogg" => "audio/ogg",
        _ => "audio/wav",
    };
    let data_url = format!("data:{};base64,{}", mime_type, audio_data);

    let audio: web_sys::HtmlAudioElement = document
        .create_element("audio")
        .map_err(|e| format!("Failed to create audio element: {:?}", e))?
        .dyn_into()
        .map_err(|_| "Failed to cast to HtmlAudioElement")?;

    audio.set_src(&data_url);
    let _ = audio.play().map_err(|e| format!("Failed to play: {:?}", e))?;

    Ok(())
}
