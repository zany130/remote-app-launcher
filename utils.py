"""Subprocess and helper utilities."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger("remote_app_launcher.utils")


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(message)s"))
    app_logger = logging.getLogger("remote_app_launcher")
    app_logger.setLevel(level)
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.propagate = False


def run_ssh(host: str, command: str, capture: bool = True) -> subprocess.CompletedProcess:
    full_cmd = ["ssh", host, command]
    return subprocess.run(full_cmd, capture_output=capture, text=True, check=False)


def run_waypipe_launch(host: str, desktop_id: str, detached: bool = True) -> subprocess.Popen:
    # gtk-launch spawns the app and exits; we must keep the session alive or waypipe
    # tears down the Wayland tunnel. Pass the entire remote command as ONE argument to
    # ssh so the semicolon isn't split by the remote shell; otherwise "sh -c" only
    # gets "gtk-launch" and the desktop_id is lost (gtk-launch: missing application name).
    remote_cmd = f"sh -c 'gtk-launch {desktop_id}; exec sleep 86400'"
    full_cmd = ["waypipe", "ssh", "-t", host, remote_cmd]
    log.info("Running: waypipe ssh -t %s %s", host, remote_cmd)
    kwargs = {}
    if detached:
        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "start_new_session": True,
        }
    return subprocess.Popen(full_cmd, **kwargs)


def get_config_dir() -> Path:
    return Path.home() / ".config" / "remote-app-launcher"


def get_cache_path(host: str) -> Path:
    return get_config_dir() / f"apps-{host}.json"


def load_host_from_config() -> Optional[str]:
    config_file = get_config_dir() / "config.json"
    if not config_file.exists():
        return None
    try:
        with open(config_file) as f:
            return json.load(f).get("host")
    except (json.JSONDecodeError, OSError):
        return None
