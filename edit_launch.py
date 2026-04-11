"""Open launch command in $EDITOR (temp file); read back newline-separated body."""

import logging
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger("remote_app_launcher.edit_launch")

_TEMP_HEADER = """# Remote launch command (runs on the HTPC inside sh -c).
# Lines starting with # are ignored (full-line comments only).
# A final line "exec sleep 86400" is appended automatically after you save — do not add it.
# Use one line, e.g. env … gtk-launch id, or multiple lines with export … then the command.
# For scoped env + command in one shot, use: env VAR=val /path/to/app (same line).
#
"""


def prepare_temp_file(default_body: str) -> Path:
    fd, name = tempfile.mkstemp(prefix="remote-app-launcher-", suffix=".sh")
    path = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(_TEMP_HEADER)
            f.write("\n")
            f.write(default_body)
            if not default_body.endswith("\n"):
                f.write("\n")
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return path


def run_editor(path: Path) -> int:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        cmd = shlex.split(editor) + [str(path)]
    else:
        cmd = ["vi", str(path)]
    log.debug("Running editor: %s", cmd)
    return subprocess.run(cmd, check=False).returncode


def read_edited_launch_body(path: Path) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("Could not read edited file: %s", e)
        return None
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        kept.append(stripped)
    if not kept:
        return None
    return "\n".join(kept)
