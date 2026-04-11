"""fzf integration and Waypipe launch logic."""

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from models import App
from ui import FZF_DISPLAY_DELIM, format_fzf_line
from utils import run_waypipe_launch

log = logging.getLogger("remote_app_launcher.launcher")

_EXPECT_KEYS = frozenset({"ctrl-r", "ctrl-f", "ctrl-e"})


class FzfAction(Enum):
    LAUNCH = "launch"
    LAUNCH_EDIT = "launch_edit"
    REFRESH = "refresh"
    TOGGLE_FAVORITE = "toggle_favorite"
    CANCEL = "cancel"


@dataclass
class FzfResult:
    action: FzfAction
    app: Optional[App] = None


def parse_desktop_id_from_fzf_line(line: str, delimiter: str = FZF_DISPLAY_DELIM) -> Optional[str]:
    line = line.strip()
    if not line:
        return None
    parts = line.split(delimiter)
    if len(parts) < 3:
        return None
    return parts[-1].strip()


def _parse_fzf_stdout(stdout: str) -> Tuple[Optional[str], Optional[str]]:
    """
    With --expect=ctrl-r,ctrl-f,ctrl-e: first line may be the key name, second the selected row.
    With Enter: single line is the selected row.
    """
    raw = stdout.strip()
    if not raw:
        return None, None
    lines = raw.split("\n")
    first = lines[0].strip()
    if first in _EXPECT_KEYS:
        key = first
        second = lines[1].strip() if len(lines) > 1 else None
        return key, second
    return None, first


def run_fzf(
    ordered_apps: List[Tuple[App, bool]],
    *,
    host: str,
    apps_by_id: Dict[str, App],
) -> FzfResult:
    if not ordered_apps:
        log.warning("No apps to show.")
        return FzfResult(FzfAction.CANCEL)

    lines = [format_fzf_line(app, is_favorite=fav) for app, fav in ordered_apps]
    header = (
        f"remote-app-launcher · {host}\n"
        "Enter launch   Ctrl-E edit cmd   Ctrl-R rescan   Ctrl-F favorite   Esc quit"
    )
    fzf_cmd = [
        "fzf",
        "--reverse",
        "--expect=ctrl-r,ctrl-f,ctrl-e",
        f"--header={header}",
        "--header-first",
        "--info=inline",
        "--no-separator",
    ]
    try:
        proc = subprocess.run(
            fzf_cmd,
            input="\n".join(lines),
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except FileNotFoundError:
        log.error("fzf not found. Install fzf and ensure it is in PATH.")
        return FzfResult(FzfAction.CANCEL)
    except subprocess.TimeoutExpired:
        return FzfResult(FzfAction.CANCEL)

    if proc.returncode == 130:
        return FzfResult(FzfAction.CANCEL)
    if proc.returncode not in (0, 1):
        err = (proc.stderr or "").strip()
        if err:
            log.error("fzf error: %s", err)
        return FzfResult(FzfAction.CANCEL)

    out = proc.stdout or ""
    key, row = _parse_fzf_stdout(out)
    # returncode 1: no selection / Esc (usually empty stdout)
    if proc.returncode == 1 and not key and not row:
        return FzfResult(FzfAction.CANCEL)

    if key == "ctrl-r":
        return FzfResult(FzfAction.REFRESH)

    if key == "ctrl-f":
        if not row:
            log.info("No line selected for favorite toggle.")
            return FzfResult(FzfAction.CANCEL)
        did = parse_desktop_id_from_fzf_line(row)
        if not did:
            log.warning("Could not parse app from selection.")
            return FzfResult(FzfAction.CANCEL)
        app = apps_by_id.get(did)
        if not app:
            log.warning("Unknown desktop id %r.", did)
            return FzfResult(FzfAction.CANCEL)
        return FzfResult(FzfAction.TOGGLE_FAVORITE, app)

    if key == "ctrl-e":
        if not row:
            log.info("No line selected for edit launch.")
            return FzfResult(FzfAction.CANCEL)
        did = parse_desktop_id_from_fzf_line(row)
        if not did:
            log.warning("Could not parse app from selection.")
            return FzfResult(FzfAction.CANCEL)
        app = apps_by_id.get(did)
        if not app:
            log.warning("Unknown desktop id %r.", did)
            return FzfResult(FzfAction.CANCEL)
        return FzfResult(FzfAction.LAUNCH_EDIT, app)

    if not row:
        return FzfResult(FzfAction.CANCEL)

    did = parse_desktop_id_from_fzf_line(row)
    if not did:
        log.warning("Could not parse app from selection.")
        return FzfResult(FzfAction.CANCEL)
    app = apps_by_id.get(did)
    if not app:
        log.warning("Unknown desktop id %r.", did)
        return FzfResult(FzfAction.CANCEL)
    return FzfResult(FzfAction.LAUNCH, app)


def launch_app(host: str, app: App, background: bool = True) -> subprocess.Popen:
    log.debug("Launching %s (%s) on %s via waypipe", app.name, app.desktop_id, host)
    proc = run_waypipe_launch(host, app.desktop_id, detached=background)
    if not background:
        proc.wait()
    return proc
