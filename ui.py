"""Sort and format apps for the fzf list."""

from typing import List, Tuple

from models import App

FZF_DISPLAY_DELIM = " | "
# Align favorite column (★ vs space) for a cleaner list
_FAV_PREFIX_FAV = "★ "
_FAV_PREFIX_NONE = "  "


def sort_apps_for_display(apps: List[App], favorite_order: List[str]) -> List[Tuple[App, bool]]:
    """
    Favorites first (order from favorite_order), then remaining apps by name.
    favorite_order should already be restricted to ids present in apps.
    """
    by_id = {a.desktop_id: a for a in apps}
    seen: set[str] = set()
    ordered: List[Tuple[App, bool]] = []
    for fid in favorite_order:
        app = by_id.get(fid)
        if app and fid not in seen:
            ordered.append((app, True))
            seen.add(fid)
    rest = sorted((a for a in apps if a.desktop_id not in seen), key=lambda a: a.name.lower())
    for app in rest:
        ordered.append((app, False))
    return ordered


def format_fzf_line(app: App, *, is_favorite: bool, delimiter: str = FZF_DISPLAY_DELIM) -> str:
    prefix = _FAV_PREFIX_FAV if is_favorite else _FAV_PREFIX_NONE
    cats = app.categories.replace(";", ", ").strip(", ") if app.categories else ""
    return f"{prefix}{app.name}{delimiter}{cats}{delimiter}{app.desktop_id}"
