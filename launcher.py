"""fzf integration and Waypipe launch logic."""

import logging
import subprocess
from typing import List, Optional

from models import App
from utils import run_waypipe_launch

log = logging.getLogger("remote_app_launcher.launcher")
FZF_DISPLAY_DELIM = " | "


class FzfError(Exception):
    """Raised when fzf cannot be invoked due to a hard error (not user cancellation)."""


def parse_fzf_selection(line: str) -> Optional[str]:
    if not line or not line.strip():
        return None
    parts = line.split(FZF_DISPLAY_DELIM)
    if len(parts) < 3:
        return None
    desktop_id = parts[-1].strip()
    return desktop_id if desktop_id else None


def run_fzf(apps: List[App], header: str = "Select app (type to search)") -> Optional[App]:
    """Run fzf and return the selected App, or None if the user cancelled.

    Raises FzfError on hard failures (missing fzf binary, no /dev/tty, timeout).
    """
    if not apps:
        log.warning("No apps in cache. Run 'remote-app-launcher refresh --host <host>' first.")
        return None
    lines = [app.fzf_line(FZF_DISPLAY_DELIM) for app in apps]

    # Open /dev/tty explicitly so fzf can render its TUI on the controlling
    # terminal even when stdout is captured.  Without this, environments such
    # as ChromeOS Crostini may see an invisible fzf UI because capture_output
    # (stderr=PIPE) can suppress the terminal draw path fzf falls back to
    # when it cannot render via /dev/tty.  If /dev/tty is genuinely absent
    # (e.g. launched from a non-terminal context) we raise FzfError so the
    # caller can propagate a non-zero exit status.
    try:
        tty = open("/dev/tty", "rb+", buffering=0)  # noqa: WPS515
    except OSError as e:
        raise FzfError(
            f"Cannot open /dev/tty for fzf TUI ({e}). "
            "Run 'remote-app-launcher launch' from an interactive terminal."
        ) from e

    input_text = "\n".join(lines)
    try:
        try:
            proc = subprocess.Popen(
                ["fzf", "--reverse", f"--header={header}"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=tty,
                text=True,
            )
        except FileNotFoundError as e:
            raise FzfError("fzf not found. Install fzf and ensure it's in PATH.") from e

        try:
            stdout, _ = proc.communicate(input=input_text, timeout=300)
        except subprocess.TimeoutExpired as e:
            proc.kill()
            proc.communicate()
            raise FzfError("fzf timed out waiting for a selection.") from e
    finally:
        tty.close()

    selected = (stdout or "").strip()
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
