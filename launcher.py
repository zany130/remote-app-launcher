"""fzf integration and Waypipe launch logic."""

import logging
import subprocess
from typing import List, Optional

from models import App
from utils import run_waypipe_launch

log = logging.getLogger("remote_app_launcher.launcher")
FZF_DISPLAY_DELIM = " | "


def parse_fzf_selection(line: str) -> Optional[str]:
    if not line or not line.strip():
        return None
    parts = line.split(FZF_DISPLAY_DELIM)
    return parts[-1].strip() if len(parts) >= 3 else None


def run_fzf(apps: List[App], header: str = "Select app (type to search)") -> Optional[App]:
    if not apps:
        log.warning("No apps in cache. Run 'remote-app-launcher refresh --host <host>' first.")
        return None
    lines = [app.fzf_line(FZF_DISPLAY_DELIM) for app in apps]
    try:
        proc = subprocess.run(
            ["fzf", "--reverse", f"--header={header}"],
            input="\n".join(lines),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        log.error("fzf not found. Install fzf and ensure it's in PATH.")
        return None
    except subprocess.TimeoutExpired:
        return None
    selected = proc.stdout.strip() if proc.stdout else ""
    if not selected:
        return None
    desktop_id = parse_fzf_selection(selected)
    if not desktop_id:
        return None
    for app in apps:
        if app.desktop_id == desktop_id:
            return app
    return None


def launch_app(host: str, app: App, background: bool = True) -> None:
    log.debug("Launching %s (%s) on %s via waypipe", app.name, app.desktop_id, host)
    proc = run_waypipe_launch(host, app.desktop_id, detached=background)
    if not background:
        proc.wait()
