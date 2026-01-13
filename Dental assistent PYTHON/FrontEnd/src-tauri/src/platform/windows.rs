//! Windows-specific platform code for Dental Assistant
//!
//! This file contains Windows-specific initialization and utilities.

use std::process::Command;
use std::path::PathBuf;

/// Windows-specific backend startup
/// Uses CreateProcess to start the Python backend without a console window
pub fn start_backend_process(api_key: &str) -> Option<std::process::Child> {
    let backend_path = get_backend_path();

    if !backend_path.exists() {
        eprintln!("[Windows] Backend not found at: {:?}", backend_path);
        return None;
    }

    // On Windows, use pythonw.exe to avoid console window
    match Command::new("pythonw")
        .arg("-m")
        .arg("uvicorn")
        .arg("main:app")
        .arg("--host")
        .arg("127.0.0.1")
        .arg("--port")
        .arg("9000")
        .env("APP_API_KEY", api_key)
        .current_dir(&backend_path)
        .spawn()
    {
        Ok(child) => Some(child),
        Err(e) => {
            eprintln!("[Windows] Failed to start backend: {}", e);
            // Fallback to regular python
            Command::new("python")
                .arg("-m")
                .arg("uvicorn")
                .arg("main:app")
                .arg("--host")
                .arg("127.0.0.1")
                .arg("--port")
                .arg("9000")
                .env("APP_API_KEY", api_key)
                .current_dir(&backend_path)
                .spawn()
                .ok()
        }
    }
}

/// Get the path to the backend directory on Windows
pub fn get_backend_path() -> PathBuf {
    // In production, backend would be bundled as a sidecar
    // In dev mode, it's relative to the frontend
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));

    // Check for production path (bundled)
    let prod_path = exe_dir.join("backend");
    if prod_path.exists() {
        return prod_path;
    }

    // Dev mode path
    PathBuf::from("../../BackEnd")
}

/// Windows-specific initialization
pub fn platform_init() {
    // Enable ANSI colors in Windows console
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // Enable virtual terminal processing for colored output
        let _ = Command::new("cmd")
            .args(["/C", ""])
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .output();
    }
}

/// Get platform-specific app data directory on Windows
pub fn get_app_data_dir() -> PathBuf {
    std::env::var("APPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            PathBuf::from(std::env::var("USERPROFILE").unwrap_or_else(|_| ".".to_string()))
                .join("AppData/Roaming")
        })
        .join("DentalAssistant")
}
