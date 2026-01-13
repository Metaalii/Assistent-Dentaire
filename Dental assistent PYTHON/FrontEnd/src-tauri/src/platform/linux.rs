//! Linux-specific platform code for Dental Assistant
//!
//! This file contains Linux-specific initialization and utilities.
//! Supports various distributions (Ubuntu, Fedora, Arch, etc.)

use std::process::Command;
use std::path::PathBuf;

/// Linux-specific backend startup
pub fn start_backend_process(api_key: &str) -> Option<std::process::Child> {
    let backend_path = get_backend_path();

    if !backend_path.exists() {
        eprintln!("[Linux] Backend not found at: {:?}", backend_path);
        return None;
    }

    // On Linux, try python3 from various locations
    let python_paths = [
        "python3",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
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

    eprintln!("[Linux] Failed to start backend with any Python interpreter");
    None
}

/// Get the path to the backend directory on Linux
pub fn get_backend_path() -> PathBuf {
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));

    // Check for production path (AppImage or installed)
    let prod_paths = [
        exe_dir.join("backend"),
        exe_dir.join("../share/dental-assistant/backend"),
        exe_dir.join("../lib/dental-assistant/backend"),
    ];

    for path in &prod_paths {
        if path.exists() {
            return path.clone();
        }
    }

    // Dev mode path
    PathBuf::from("../../BackEnd")
}

/// Linux-specific initialization
pub fn platform_init() {
    // Set up Linux-specific environment

    // Ensure XDG directories are set
    if std::env::var("XDG_DATA_HOME").is_err() {
        if let Ok(home) = std::env::var("HOME") {
            std::env::set_var("XDG_DATA_HOME", format!("{}/.local/share", home));
        }
    }

    // Set locale for proper text handling
    if std::env::var("LC_ALL").is_err() {
        std::env::set_var("LC_ALL", "en_US.UTF-8");
    }

    // For Wayland compatibility
    if std::env::var("GDK_BACKEND").is_err() {
        // Let GTK auto-detect, but prefer Wayland if available
        if std::env::var("WAYLAND_DISPLAY").is_ok() {
            std::env::set_var("GDK_BACKEND", "wayland,x11");
        }
    }
}

/// Get platform-specific app data directory on Linux
pub fn get_app_data_dir() -> PathBuf {
    std::env::var("XDG_DATA_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".to_string()))
                .join(".local/share")
        })
        .join("dental-assistant")
}

/// Check if NVIDIA GPU is available on Linux
pub fn has_nvidia_gpu() -> bool {
    Command::new("nvidia-smi")
        .arg("--query-gpu=name")
        .arg("--format=csv,noheader")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

/// Check if running under Wayland
pub fn is_wayland() -> bool {
    std::env::var("WAYLAND_DISPLAY").is_ok()
}
