"""JSON cache for discovered apps."""

import json
import logging
from typing import List

from models import App
from utils import get_cache_path, get_config_dir

log = logging.getLogger("remote_app_launcher.cache")


def save_cache(host: str, apps: List[App]) -> None:
    cache_path = get_cache_path(host)
    get_config_dir().mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump([app.to_dict() for app in apps], f, indent=2)
    log.debug("Saved cache: %s (%d apps)", cache_path, len(apps))


def load_cache(host: str) -> List[App]:
    cache_path = get_cache_path(host)
    if not cache_path.exists():
        log.debug("Cache not found: %s", cache_path)
        return []
    try:
        with open(cache_path) as f:
            data = json.load(f)
        apps = [App.from_dict(d) for d in data if isinstance(d, dict)]
        log.debug("Loaded cache: %s (%d apps)", cache_path, len(apps))
        return apps
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to load cache %s: %s", cache_path, e)
        return []
