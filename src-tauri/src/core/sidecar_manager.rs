use std::sync::Arc;
use tokio::sync::Mutex;
use tauri::{
    async_runtime, AppHandle,
};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

pub struct SidecarManager {
    running: Arc<Mutex<bool>>,
}

impl SidecarManager {
    pub fn new() -> Self {
        Self {
            running: Arc::new(Mutex::new(false)),
        }
    }

    pub fn start(&self, app_handle: AppHandle) {
        let running = self.running.clone();
        let app_handle = app_handle.clone();

        async_runtime::spawn(async move {
            let mut lock = running.lock().await;
            if *lock {
                println!("Meilisearch sidecar already running.");
                return;
            }

            // Use shell() extension to create sidecar command
            let sidecar_command = match app_handle.shell().sidecar("meilisearch") {
                Ok(cmd) => cmd,
                Err(e) => {
                    eprintln!("Failed to create meilisearch sidecar command: {}", e);
                    return;
                }
            };

            let (mut rx, child) = match sidecar_command.spawn() {
                Ok(res) => res,
                Err(e) => {
                    eprintln!("Failed to spawn meilisearch sidecar: {}", e);
                    return;
                }
            };

            *lock = true;
            println!("Meilisearch sidecar started with PID: {}", child.pid());

            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(line) => println!("[MEILI] {}", String::from_utf8_lossy(&line)),
                    CommandEvent::Stderr(line) => eprintln!("[MEILI ERR] {}", String::from_utf8_lossy(&line)),
                    CommandEvent::Terminated(payload) => {
                         println!("Meilisearch terminated: {:?}", payload);
                         let mut lock = running.lock().await;
                         *lock = false;
                         break;
                    }
                     _ => {}
                }
            }
        });
    }
}
