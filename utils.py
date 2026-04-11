"""Subprocess and helper utilities."""

import json
import logging
import shlex
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


def default_remote_launch_body(desktop_id: str) -> str:
    """
    Remote launch snippet only (no keepalive). Runs on the remote inside sh -c.
    GDK/Qt values are quoted so commas/semicolons are not parsed by the shell.
    """
    qid = shlex.quote(desktop_id)
    return (
        "env GDK_BACKEND='wayland,x11' QT_QPA_PLATFORM='wayland;xcb' "
        f"XDG_SESSION_TYPE=wayland gtk-launch {qid}"
    )


def finalize_remote_inner(launch_body: str) -> str:
    """Append waypipe keepalive after the user or default launch body."""
    return launch_body.rstrip() + "\nexec sleep 86400"


def run_waypipe_remote_inner(host: str, inner: str, detached: bool = True) -> subprocess.Popen:
    """
    Run inner script on remote via waypipe ssh. inner is the full sh -c script body
    (including exec sleep 86400). Passed as one argv to ssh — no local shell.
    """
    remote_cmd = "sh -c " + shlex.quote(inner)
    full_cmd = ["waypipe", "ssh", "-t", host, remote_cmd]
    log.info("Running: waypipe ssh -t %s %s", host, remote_cmd)
    kwargs: dict = {}
    if detached:
        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "start_new_session": True,
        }
    return subprocess.Popen(full_cmd, **kwargs)


def run_waypipe_launch(host: str, desktop_id: str, detached: bool = True) -> subprocess.Popen:
    body = default_remote_launch_body(desktop_id)
    inner = finalize_remote_inner(body)
    return run_waypipe_remote_inner(host, inner, detached=detached)


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
