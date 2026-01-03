#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{
    net::TcpStream,
    thread,
    time::Duration,
};
use uuid::Uuid;

struct AppState {
    api_key: String,
}

/* ---------- API KEY ---------- */

fn generate_api_key() -> String {
    Uuid::new_v4().to_string()
}

/* ---------- BACKEND CHECK ---------- */

fn wait_for_backend() -> bool {
    for _ in 0..40 {
        if TcpStream::connect("127.0.0.1:9000").is_ok() {
            return true;
        }
        thread::sleep(Duration::from_millis(250));
    }
    false
}

/* ---------- TAURI COMMAND ---------- */

#[tauri::command]
fn get_api_config(state: tauri::State<AppState>) -> String {
    state.api_key.clone()
}

/* ---------- MAIN ---------- */

fn main() {
    // For MVP dev mode, use a known API key that matches the backend
    // In production, we'd start the backend sidecar with a generated key
    let api_key = std::env::var("APP_API_KEY")
        .unwrap_or_else(|_| "dev-api-key-12345".to_string());

    // Wait for external backend (in dev) or start sidecar (in prod)
    if !wait_for_backend() {
        eprintln!("Warning: Backend not responding on port 9000");
        eprintln!("Please start the backend manually:");
        eprintln!("  APP_API_KEY=\"dev-api-key-12345\" uvicorn main:app --host 127.0.0.1 --port 9000");
    }

    let state = AppState { api_key };

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .manage(state)
        .invoke_handler(tauri::generate_handler![get_api_config])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
