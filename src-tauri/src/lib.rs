use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;

const BACKEND_PORT: &str = "8742";
const HEALTH_URL: &str = "http://127.0.0.1:8742/health";

struct BackendProcess(Mutex<Option<Child>>);

fn backend_dir() -> std::path::PathBuf {
    if let Ok(resource) = std::env::var("TAURI_RESOURCE_DIR") {
        let bundled = std::path::PathBuf::from(resource).join("backend");
        if bundled.exists() {
            return bundled;
        }
    }
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("..")
        .join("backend")
}

fn start_backend() -> Option<Child> {
    let backend = backend_dir();
    if !backend.exists() {
        let dev_backend = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend");
        if dev_backend.exists() {
            return spawn_backend(&dev_backend);
        }
        eprintln!("Backend directory not found");
        return None;
    }
    spawn_backend(&backend)
}

fn spawn_backend(backend: &std::path::Path) -> Option<Child> {
    let mut cmd = Command::new("uv");
    cmd.args([
        "run",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        BACKEND_PORT,
    ]);
    cmd.current_dir(backend);

    if let Ok(ledger) = std::env::var("LEDGER_PATH") {
        cmd.env("LEDGER_PATH", ledger);
    }
    if let Ok(config) = std::env::var("CONFIG_PATH") {
        cmd.env("CONFIG_PATH", config);
    }

    match cmd.spawn() {
        Ok(child) => {
            eprintln!("Started FastAPI backend on 127.0.0.1:{}", BACKEND_PORT);
            Some(child)
        }
        Err(e) => {
            eprintln!("Failed to start backend: {e}");
            None
        }
    }
}

fn wait_for_backend(timeout: Duration) -> bool {
    let client = match reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
    {
        Ok(c) => c,
        Err(_) => return false,
    };
    let start = Instant::now();
    while start.elapsed() < timeout {
        if let Ok(res) = client.get(HEALTH_URL).send() {
            if res.status().is_success() {
                return true;
            }
        }
        std::thread::sleep(Duration::from_millis(300));
    }
    false
}

fn stop_backend(state: &BackendProcess) {
    if let Ok(mut guard) = state.0.lock() {
        if let Some(mut child) = guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[tauri::command]
async fn pick_ledger_file(app: tauri::AppHandle) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let file = app
        .dialog()
        .file()
        .add_filter("Beancount ledger", &["beancount"])
        .blocking_pick_file();
    Ok(file.map(|p| p.to_string()))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![pick_ledger_file])
        .setup(|app| {
            let child = start_backend();
            app.manage(BackendProcess(Mutex::new(child)));

            if !wait_for_backend(Duration::from_secs(30)) {
                eprintln!("Warning: backend health check timed out");
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.app_handle().try_state::<BackendProcess>() {
                    stop_backend(state.inner());
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
