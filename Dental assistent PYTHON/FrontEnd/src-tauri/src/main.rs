#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Spawn the Python backend as a sidecar process
            let sidecar_command = app.shell().sidecar("dental-backend").unwrap();
            let (mut _rx, mut _child) = sidecar_command.spawn().expect("Failed to spawn sidecar");

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
