"""CloakBrowser Manager — local desktop application.

Usage:
    python desktop_app.py
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

FROZEN = bool(getattr(sys, "frozen", False))


def _resource_dir() -> Path:
    if FROZEN:
        return Path(sys.executable).resolve().parents[1] / "Resources"
    return Path(__file__).resolve().parent


def _root_dir() -> Path:
    if FROZEN:
        app_path = Path(sys.executable).resolve().parents[2]
        repo_root = app_path.parent.parent
        if (repo_root / "desktop-app-settings.json").exists():
            return repo_root
        return Path.home() / ".cloakbrowser-manager"
    return Path(__file__).resolve().parent


RESOURCE_DIR = _resource_dir()
ROOT_DIR = _root_dir()
SETTINGS_FILE = ROOT_DIR / "desktop-app-settings.json"
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "desktop-app.log"
APP_ICON = RESOURCE_DIR / "app-icon.icns" if FROZEN else ROOT_DIR / "assets" / "app-icon.icns"

DEFAULT_SETTINGS = {
    "data_dir": "data",
    "cache_dir": "cloakbrowser-cache",
    "tmp_dir": "tmp",
    "binary_path": "",
    "host": "127.0.0.1",
}

BACKEND_WAIT_TIMEOUT = 20
BACKEND_POLL_INTERVAL = 0.5

logger = logging.getLogger("desktop_app")


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(str(LOG_FILE)),
            logging.StreamHandler(sys.stderr),
        ],
    )


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            settings = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(settings)
        logger.info("Loaded settings from %s", SETTINGS_FILE)
        return merged
    SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2) + "\n")
    logger.info("Created default settings at %s", SETTINGS_FILE)
    return dict(DEFAULT_SETTINGS)


def resolve_path(root: Path, path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (root / p).resolve()


def ensure_dirs(root: Path, settings: dict) -> None:
    for key in ("data_dir", "cache_dir", "tmp_dir"):
        d = resolve_path(root, settings[key])
        d.mkdir(parents=True, exist_ok=True)
        logger.info("Ensured directory %s = %s", key, d)


def build_env(root: Path, settings: dict) -> dict:
    env = os.environ.copy()
    env["DATA_DIR"] = str(resolve_path(root, settings["data_dir"]))
    env["CLOAKBROWSER_CACHE_DIR"] = str(resolve_path(root, settings["cache_dir"]))
    env["TMPDIR"] = str(resolve_path(root, settings["tmp_dir"]))
    env["FRONTEND_DIR"] = str(RESOURCE_DIR / "frontend" / "dist" if FROZEN else root / "frontend" / "dist")
    env["DISABLE_PROFILE_AUTO_LAUNCH"] = "1"

    binary_path = settings.get("binary_path", "")
    if binary_path:
        bp = Path(binary_path)
        if not bp.is_absolute():
            bp = (root / bp).resolve()
        if not bp.exists():
            logger.error(
                "CLOAKBROWSER_BINARY_PATH set to '%s' but file does not exist", bp
            )
            sys.exit(
                f"CLOAKBROWSER_BINARY_PATH set to '{bp}' but file does not exist"
            )
        env["CLOAKBROWSER_BINARY_PATH"] = str(bp)
        logger.info("Using custom binary path: %s", bp)

    return env


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        logger.info("Allocated dynamic port: %d", port)
        return port


def start_backend(root: Path, env: dict, port: int, host: str) -> subprocess.Popen:
    if FROZEN:
        backend_args = [sys.executable, "--backend", host, str(port)]
    else:
        backend_args = [sys.executable, str(Path(__file__).resolve()), "--backend", host, str(port)]

    log_fh = open(LOG_FILE, "a")
    log_fh.write(
        f"\n--- desktop_app started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n"
    )
    log_fh.flush()

    proc = subprocess.Popen(
        backend_args,
        cwd=str(root),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    logger.info("Started uvicorn (pid=%d, port=%d)", proc.pid, port)
    return proc


def run_backend(host: str, port: int) -> None:
    import uvicorn
    from backend.main import app

    uvicorn.run(app, host=host, port=port, log_level="info")


def wait_until_ready(port: int, host: str, timeout: int = BACKEND_WAIT_TIMEOUT) -> bool:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            resp = httpx.get(f"http://{host}:{port}/api/status", timeout=2)
            if resp.status_code == 200:
                elapsed = time.monotonic() - start
                logger.info("Backend ready after %.1fs", elapsed)
                return True
        except (httpx.RequestError, httpx.TimeoutException):
            pass
        time.sleep(BACKEND_POLL_INTERVAL)
    return False


def stop_backend(proc: subprocess.Popen, timeout: int = 10) -> None:
    if proc.poll() is not None:
        logger.info("Backend already exited (rc=%d)", proc.returncode)
        return

    logger.info("Stopping backend (pid=%d)...", proc.pid)
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
        logger.info("Backend terminated gracefully")
    except subprocess.TimeoutExpired:
        logger.warning("Backend did not exit within %ds, sending SIGKILL", timeout)
        proc.kill()
        proc.wait()
        logger.info("Backend killed")


def main() -> None:
    setup_logging()
    root = ROOT_DIR
    logger.info("Starting CloakBrowser Manager desktop app")
    logger.info("Project root: %s", root)
    if not APP_ICON.is_file():
        sys.exit(f"App icon not found: {APP_ICON}")

    settings = load_settings()
    ensure_dirs(root, settings)
    env = build_env(root, settings)
    port = find_free_port()

    host = settings.get("host", "127.0.0.1")
    proc = start_backend(root, env, port, host)

    if not wait_until_ready(port, host):
        stop_backend(proc)
        logger.error(
            "Backend did not become ready within %ds", BACKEND_WAIT_TIMEOUT
        )
        sys.exit(
            f"Backend did not become ready within {BACKEND_WAIT_TIMEOUT}s.\n"
            f"See log: {LOG_FILE}"
        )

    try:
        import webview

        logger.info("Opening pywebview window at http://%s:%d", host, port)
        webview.create_window(
            "CloakBrowser Manager",
            f"http://{host}:{port}",
            width=1280,
            height=800,
        )
        webview.start(icon=str(APP_ICON))
    except ImportError:
        logger.warning("pywebview not installed, opening browser instead")
        import webbrowser

        webbrowser.open(f"http://{host}:{port}")
        logger.info("Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
                if proc.poll() is not None:
                    break
        except KeyboardInterrupt:
            pass

    stop_backend(proc)
    logger.info("Desktop app shut down")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--backend":
        run_backend(sys.argv[2], int(sys.argv[3]))
    else:
        main()
