//! Voice Queue Commands
//!
//! Commands for managing the voice synthesis queue.

use std::sync::Arc;
use tauri::State;
use tokio::sync::RwLock as AsyncRwLock;

use crate::core::voice::{
    VoiceManager, SynthesisRequest, OutputFormat,
    types::{QueuedVoice, VoiceStatus},
};
use crate::commands::AppState;

// ============================================================================
// Voice Queue Commands
// ============================================================================

#[tauri::command]
pub async fn queue_voice(
    text: String,
    voice_id: Option<String>,
    state: State<'_, AppState>,
) -> Result<QueuedVoice, String> {
    // 1. Determine Voice ID
    let vid = voice_id.unwrap_or_else(|| "default".to_string());

    // 2. Add to Queue
    let item = {
        let mut manager = state.voice_manager.write().await;
        manager.add_to_queue(text, vid)
    };

    // 3. Trigger Processing (Background)
    match process_voice_queue(state).await {
        Ok(_) => {},
        Err(e) => eprintln!("Failed to trigger voice queue processing: {}", e),
    }

    Ok(item)
}

#[tauri::command]
pub async fn get_voice_queue(state: State<'_, AppState>) -> Result<Vec<QueuedVoice>, String> {
    let manager = state.voice_manager.read().await;
    Ok(manager.get_queue())
}

#[tauri::command]
pub async fn cancel_voice(queue_id: String, state: State<'_, AppState>) -> Result<(), String> {
    let mut manager = state.voice_manager.write().await;
    manager.remove_from_queue(&queue_id);
    Ok(())
}

/// Internal helper to process the queue
async fn process_voice_queue(state: State<'_, AppState>) -> Result<(), String> {
    let vm_clone = state.voice_manager.clone();

    // Spawn a detached task
    tauri::async_runtime::spawn(async move {
        // We loop until queue is empty or processing fails
        loop {
            // 1. Get next pending (Read Lock)
            let next_item = {
                let manager = vm_clone.read().await;
                if manager.is_playing {
                    None
                } else {
                    manager.get_next_pending()
                }
            };

            if let Some(item) = next_item {
                // 2. Mark Processing
                {
                    let mut manager = vm_clone.write().await;
                    manager.update_status(&item.id, VoiceStatus::Processing);
                }

                // 3. Synthesize
                let req = SynthesisRequest {
                    text: item.text.clone(),
                    voice_id: item.voice_id.clone(),
                    settings: None,
                    output_format: OutputFormat::Mp3, // Default
                };

                // Perform synthesis without holding lock
                let result = {
                    let manager = vm_clone.read().await;
                    manager.synthesize(req).await
                };

                match result {
                    Ok(res) => {
                        // 4. Synthesized. Now Play.
                        // Read file
                        if let Ok(audio_data) = tokio::fs::read(&res.audio_path).await {
                             // Mark Playing
                            {
                                let mut manager = vm_clone.write().await;
                                manager.update_status(&item.id, VoiceStatus::Playing);
                                manager.is_playing = true;
                            }

                            // Play (Blocking for now, inside spawn)
                            let vm_for_clos = vm_clone.clone();
                            let play_result = tokio::task::spawn_blocking(move || {
                                let manager = vm_for_clos.blocking_read();
                                manager.play_audio(audio_data)
                            }).await;

                            let play_result = match play_result {
                                Ok(inner) => inner.map_err(|e| e.to_string()),
                                Err(e) => Err(e.to_string()),
                            };

                            // Mark Completed
                            {
                                let mut manager = vm_clone.write().await;
                                manager.is_playing = false;
                                manager.update_status(&item.id, if play_result.is_ok() {
                                    VoiceStatus::Completed
                                } else {
                                    VoiceStatus::Failed("Playback failed".into())
                                });
                            }
                        } else {
                             // File read failed
                            let mut manager = vm_clone.write().await;
                            manager.update_status(&item.id, VoiceStatus::Failed("Could not read audio file".into()));
                        }
                    }
                    Err(e) => {
                        // Synthesis Failed
                        let mut manager = vm_clone.write().await;
                        manager.update_status(&item.id, VoiceStatus::Failed(e.to_string()));
                    }
                }
            } else {
                // No more items
                break;
            }
        }
    });

    Ok(())
}
