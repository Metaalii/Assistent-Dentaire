//! macOS-specific platform code for Dental Assistant
//!
//! This file contains macOS-specific initialization and utilities.
//! Optimized for Apple Silicon (M1/M2/M3) and Intel Macs.

use std::process::Command;
use std::path::PathBuf;

/// macOS-specific backend startup
pub fn start_backend_process(api_key: &str) -> Option<std::process::Child> {
    let backend_path = get_backend_path();

    if !backend_path.exists() {
        eprintln!("[macOS] Backend not found at: {:?}", backend_path);
        return None;
    }

    // On macOS, use python3 from PATH or Homebrew
    let python_paths = [
        "python3",
        "/usr/local/bin/python3",      // Intel Homebrew
        "/opt/homebrew/bin/python3",   // Apple Silicon Homebrew
        "/usr/bin/python3",            // System Python
    ];

    for python in &python_paths {
        if let Ok(child) = Command::new(python)
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
            return Some(child);
        }
    }

    eprintln!("[macOS] Failed to start backend with any Python interpreter");
    None
}

/// Get the path to the backend directory on macOS
pub fn get_backend_path() -> PathBuf {
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));

    // Check for production path (inside .app bundle)
    // macOS app bundles: AppName.app/Contents/MacOS/executable
    let bundle_resources = exe_dir
        .parent() // Contents
        .and_then(|p| p.parent()) // AppName.app
        .map(|p| p.join("Contents/Resources/backend"));

    if let Some(ref path) = bundle_resources {
        if path.exists() {
            return path.clone();
        }
    }

    // Dev mode path
    PathBuf::from("../../BackEnd")
}

/// macOS-specific initialization
pub fn platform_init() {
    // Set up macOS-specific environment
    // Ensure Metal is available for GPU acceleration
    std::env::set_var("PYTORCH_ENABLE_MPS_FALLBACK", "1");

    // Set locale for proper text handling
    if std::env::var("LC_ALL").is_err() {
        std::env::set_var("LC_ALL", "en_US.UTF-8");
    }
}

/// Get platform-specific app data directory on macOS
pub fn get_app_data_dir() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".to_string()))
        .join("Library/Application Support/DentalAssistant")
}

/// Check if running on Apple Silicon
pub fn is_apple_silicon() -> bool {
    Command::new("sysctl")
        .args(["-n", "machdep.cpu.brand_string"])
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).contains("Apple"))
        .unwrap_or(false)
}
