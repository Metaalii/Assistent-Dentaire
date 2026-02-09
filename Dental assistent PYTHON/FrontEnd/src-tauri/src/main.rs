#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{
    collections::HashMap,
    net::TcpStream,
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};

use tauri::{Manager, RunEvent};
use tauri::api::process::{Command, CommandChild, CommandEvent};
use uuid::Uuid;

struct AppState {
    backend_process: Arc<Mutex<Option<CommandChild>>>,
    api_key: String,
}

/* ---------- API KEY ---------- */

fn generate_api_key() -> String {
    Uuid::new_v4().to_string()
}

/* ---------- BACKEND ---------- */

fn start_backend(api_key: &str) -> CommandChild {
    let mut env_vars = HashMap::new();
    env_vars.insert("APP_API_KEY".to_string(), api_key.to_string());

    let (mut rx, child) = Command::new_sidecar("binaries/dental-backend")
        .expect("Sidecar not found: dental-backend")
        .envs(env_vars)
        .spawn()
        .expect("Failed to start backend sidecar");

    // Optional: log backend output
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stderr(line) => eprintln!("[backend] {line}"),
                CommandEvent::Stdout(line) => println!("[backend] {line}"),
                _ => {}
            }
        }
    });

    child
}

fn wait_for_backend() {
    for _ in 0..40 {
        if TcpStream::connect("127.0.0.1:9000").is_ok() {
            return;
        }
        thread::sleep(Duration::from_millis(250));
    }

    panic!("Backend did not become ready");
}

/* ---------- TAURI COMMAND ---------- */

#[tauri::command]
fn get_api_config(state: tauri::State<AppState>) -> String {
    state.api_key.clone()
}

/* ---------- MAIN ---------- */

fn main() {
    let api_key = generate_api_key();

    let backend_child = start_backend(&api_key);
    wait_for_backend();

    let state = AppState {
        backend_process: Arc::new(Mutex::new(Some(backend_child))),
        api_key,
    };

    tauri::Builder::default()
        .manage(state)
        .invoke_handler(tauri::generate_handler![get_api_config])
        .build(tauri::generate_context!())
        .expect("Tauri build failed")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                let state = app_handle.state::<AppState>();
                let process = state.backend_process.clone();
                drop(state);
                if let Ok(mut guard) = process.lock() {
                    if let Some(child) = guard.take() {
                        let _ = child.kill();
                    }
                };
            }
        });
}
