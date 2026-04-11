"""Persistent per-host favorites (desktop IDs), stored as JSON."""

import json
import logging
from pathlib import Path
from typing import List

from models import App
from utils import get_config_dir

log = logging.getLogger("remote_app_launcher.favorites")


def get_favorites_path(host: str) -> Path:
    return get_config_dir() / f"favorites-{host}.json"


def load_favorite_ids(host: str) -> List[str]:
    """Load ordered favorite desktop IDs from disk. May include stale IDs not in current cache."""
    path = get_favorites_path(host)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not read favorites %s: %s", path, e)
        return []
    if not isinstance(data, list):
        log.warning("Invalid favorites format in %s (expected a list).", path)
        return []
    out: List[str] = []
    seen: set[str] = set()
    for item in data:
        if isinstance(item, str) and item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def save_favorite_ids(host: str, ids: List[str]) -> None:
    path = get_favorites_path(host)
    get_config_dir().mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ids, f, indent=2)
    log.debug("Saved favorites: %s (%d ids)", path, len(ids))


def effective_favorite_order(apps: List[App], stored_ids: List[str]) -> List[str]:
    """Subset of stored_ids that exist in apps, preserving order."""
    app_ids = {a.desktop_id for a in apps}
    return [i for i in stored_ids if i in app_ids]


def toggle_favorite(host: str, desktop_id: str, apps: List[App]) -> None:
    """Add or remove desktop_id in stored favorites; only ids in apps are kept when rewriting."""
    app_ids = {a.desktop_id for a in apps}
    if desktop_id not in app_ids:
        log.warning("Cannot favorite unknown app id %r (not in current list).", desktop_id)
        return
    current = load_favorite_ids(host)
    if desktop_id in current:
        updated = [i for i in current if i != desktop_id]
        log.info("Removed favorite: %s", desktop_id)
    else:
        updated = current + [desktop_id]
        log.info("Added favorite: %s", desktop_id)
    save_favorite_ids(host, updated)
