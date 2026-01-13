//! Dental Assistant - Tauri Desktop Application
//!
//! This is the main entry point for the Tauri desktop app.
//! Platform-specific code is separated into the `platform` module.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::{
    net::TcpStream,
    thread,
    time::Duration,
};

// Platform-specific modules (only the relevant one is compiled)
mod platform;

/// Application state shared across Tauri commands
struct AppState {
    api_key: String,
}

/* ---------- BACKEND CONNECTIVITY ---------- */

/// Wait for the backend to become available
/// Returns true if backend is responsive, false after timeout
fn wait_for_backend() -> bool {
    const MAX_ATTEMPTS: u32 = 40;
    const RETRY_DELAY_MS: u64 = 250;

    for attempt in 1..=MAX_ATTEMPTS {
        if TcpStream::connect("127.0.0.1:9000").is_ok() {
            println!("[Tauri] Backend connected (attempt {})", attempt);
            return true;
        }
        thread::sleep(Duration::from_millis(RETRY_DELAY_MS));
    }
    false
}

/* ---------- TAURI COMMANDS ---------- */

/// Get the API configuration (called from frontend)
#[tauri::command]
fn get_api_config(state: tauri::State<AppState>) -> String {
    state.api_key.clone()
}

/// Get platform information (called from frontend)
#[tauri::command]
fn get_platform_info() -> String {
    #[cfg(target_os = "windows")]
    return "windows".to_string();

    #[cfg(target_os = "macos")]
    return "macos".to_string();

    #[cfg(target_os = "linux")]
    return "linux".to_string();
}

/* ---------- MAIN ENTRY POINT ---------- */

fn main() {
    // Initialize platform-specific settings
    platform::platform_init();

    // Get API key from environment or use dev default
    let api_key = std::env::var("APP_API_KEY")
        .unwrap_or_else(|_| "dev-api-key-12345".to_string());

    // In production mode, try to start the backend
    #[cfg(not(debug_assertions))]
    {
        if let Some(_child) = platform::start_backend_process(&api_key) {
            println!("[Tauri] Backend process started");
            // Give backend time to initialize
            thread::sleep(Duration::from_secs(2));
        }
    }

    // Wait for backend to be ready
    if !wait_for_backend() {
        eprintln!("[Tauri] Warning: Backend not responding on port 9000");

        #[cfg(debug_assertions)]
        {
            eprintln!("[Tauri] In dev mode, start the backend manually:");
            eprintln!("  APP_API_KEY=\"dev-api-key-12345\" uvicorn main:app --host 127.0.0.1 --port 9000");
        }
    }

    // Create application state
    let state = AppState { api_key };

    // Build and run the Tauri application
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            get_api_config,
            get_platform_info
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
