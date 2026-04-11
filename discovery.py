"""
Discover launchable apps on a remote Linux host by reading .desktop files.
Parses [Desktop Entry] section with configparser (avoids PyXDG's file-path requirement).
"""

import configparser
import io
import logging
from typing import List

from models import App
from utils import run_ssh

log = logging.getLogger("remote_app_launcher.discovery")


class DiscoveryError(Exception):
    """SSH or remote discovery failed (distinct from an empty but successful scan)."""


# Paths to search for .desktop files on the remote host
REMOTE_APPLICATIONS_PATHS = [
    "/usr/share/applications",
    "$HOME/.local/share/applications",
]

_BATCH_MARKER = "@@@PATH:"
_BATCH_END = "@@@END@@@"


def _discover_raw(host: str) -> dict[str, str]:
    """Single SSH call: find all .desktop files and fetch their contents."""
    paths_arg = " ".join(REMOTE_APPLICATIONS_PATHS)
    cmd = f"""find {paths_arg} -name '*.desktop' 2>/dev/null | while IFS= read -r f; do echo '{_BATCH_MARKER}'"$f"; cat "$f" 2>/dev/null; echo '{_BATCH_END}'; done"""
    log.debug("Connecting to %s and running find+cat pipeline...", host)
    result = run_ssh(host, cmd)
    if result.returncode != 0:
        err = (result.stderr or "").strip() or (result.stdout or "").strip() or "no output"
        raise DiscoveryError(f"SSH failed (exit {result.returncode}): {err}")
    out = result.stdout
    path_to_content: dict[str, str] = {}
    current_path: str | None = None
    current_lines: list[str] = []
    for line in out.split("\n"):
        if line.startswith(_BATCH_MARKER):
            if current_path is not None:
                path_to_content[current_path] = "\n".join(current_lines).strip()
            current_path = line[len(_BATCH_MARKER) :].strip()
            current_lines = []
        elif line.strip() == _BATCH_END:
            if current_path is not None:
                path_to_content[current_path] = "\n".join(current_lines).strip()
            current_path = None
            current_lines = []
        elif current_path is not None:
            current_lines.append(line)
    if current_path is not None:
        path_to_content[current_path] = "\n".join(current_lines).strip()
    return path_to_content


def _parse_bool(val: str | None) -> bool:
    """Parse desktop boolean (true/false/1/0)."""
    if not val:
        return False
    return val.strip().lower() in ("true", "1")


# freedesktop.org game-only categories; exclude only when ALL categories are game-related
_GAME_CATEGORIES = frozenset(
    {
        "game", "actiongame", "adventuregame", "arcadegame", "boardgame",
        "blocksgame", "cardgame", "kidsgame", "logicgame", "roleplaying",
        "shooter", "simulation", "sportsgame", "strategygame", "emulator",
    }
)


def _is_solely_game(categories: str) -> bool:
    """True if app is ONLY in game categories (excludes gaming tools with e.g. Utility)."""
    cats = [c.strip().lower() for c in categories.split(";") if c.strip()]
    if not cats:
        return False
    return all(c in _GAME_CATEGORIES for c in cats)


def parse_desktop_entry(content: str, path: str, verbose: bool = False) -> App | None:
    """
    Parse .desktop content using configparser.
    Only [Desktop Entry] section; no file path required.
    """
    try:
        parser = configparser.RawConfigParser()
        parser.read_file(io.StringIO(content))
    except configparser.Error as e:
        if verbose:
            log.debug("  Skip %s: parse error (%s)", path, e)
        return None

    if not parser.has_section("Desktop Entry"):
        if verbose:
            log.debug("  Skip %s: no [Desktop Entry] section", path)
        return None

    section = "Desktop Entry"

    if parser.get(section, "Type", fallback="") != "Application":
        if verbose:
            log.debug("  Skip %s: not Application", path)
        return None

    exec_val = parser.get(section, "Exec", fallback="").strip()
    if not exec_val:
        if verbose:
            log.debug("  Skip %s: no Exec", path)
        return None

    if _parse_bool(parser.get(section, "NoDisplay", fallback="")):
        if verbose:
            log.debug("  Skip %s: NoDisplay=true", path)
        return None

    if _parse_bool(parser.get(section, "Terminal", fallback="")):
        if verbose:
            log.debug("  Skip %s: Terminal=true", path)
        return None

    desktop_id = path.split("/")[-1].removesuffix(".desktop")
    categories = parser.get(section, "Categories", fallback="")
    if _is_solely_game(categories):
        if verbose:
            log.debug("  Skip %s: solely Game category (categories: %s)", path, categories)
        return None
    name = parser.get(section, "Name", fallback=desktop_id) or desktop_id
    icon = parser.get(section, "Icon", fallback="")

    if verbose:
        log.debug("  + %s -> %s (%s)", path, name, desktop_id)

    return App(
        name=name,
        desktop_id=desktop_id,
        desktop_path=path,
        icon=icon,
        categories=categories,
    )


def discover_apps(host: str, verbose: bool = False) -> List[App]:
    """Discover all launchable apps on the remote host."""
    path_to_content = _discover_raw(host)
    log.debug("Received %d .desktop files, parsing...", len(path_to_content))

    apps_by_id: dict[str, App] = {}
    for path, content in path_to_content.items():
        if not content:
            if verbose:
                log.debug("  Skip %s: empty content", path)
            continue
        app = parse_desktop_entry(content, path, verbose=verbose)
        if app:
            apps_by_id[app.desktop_id] = app

    log.debug("Parsed %d launchable apps", len(apps_by_id))
    return sorted(apps_by_id.values(), key=lambda a: a.name.lower())
