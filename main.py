#!/usr/bin/env python3
"""remote-app-launcher - Browse and launch remote Linux apps via Waypipe."""

import argparse
import logging
import sys

from cache import load_cache, save_cache
from discovery import DiscoveryError, discover_apps
from edit_launch import prepare_temp_file, read_edited_launch_body, run_editor
from favorites import effective_favorite_order, load_favorite_ids, toggle_favorite
from launcher import FzfAction, launch_app, run_fzf
from ui import format_fzf_line, sort_apps_for_display
from utils import (
    configure_logging,
    default_remote_launch_body,
    finalize_remote_inner,
    get_config_dir,
    load_host_from_config,
    run_waypipe_remote_inner,
)

log = logging.getLogger("remote_app_launcher.main")


def resolve_host(cli_host: str | None, config_host: str | None) -> str | None:
    return cli_host or config_host


def _scan_and_cache(host: str, verbose: bool) -> list:
    apps = discover_apps(host, verbose=verbose)
    save_cache(host, apps)
    return apps


def cmd_refresh(host: str, verbose: bool = False) -> int:
    log.info("Scanning apps on %s...", host)
    try:
        apps = _scan_and_cache(host, verbose)
    except DiscoveryError as e:
        log.error("%s", e)
        return 1
    except OSError as e:
        log.error("Error during scan: %s", e)
        return 1
    log.info("Cached %d apps.", len(apps))
    return 0


def cmd_launch(host: str, verbose: bool = False) -> int:
    while True:
        apps = load_cache(host)
        if not apps:
            log.info("No cached apps for %s; scanning…", host)
            try:
                apps = _scan_and_cache(host, verbose)
            except DiscoveryError as e:
                log.error("%s", e)
                return 1
            except OSError as e:
                log.error("Error during scan: %s", e)
                return 1
            if not apps:
                log.error("No launchable apps found on %s.", host)
                return 1

        stored = load_favorite_ids(host)
        fav_order = effective_favorite_order(apps, stored)
        ordered_pairs = sort_apps_for_display(apps, fav_order)
        apps_by_id = {a.desktop_id: a for a in apps}

        result = run_fzf(ordered_pairs, host=host, apps_by_id=apps_by_id)

        if result.action == FzfAction.CANCEL:
            return 0
        if result.action == FzfAction.REFRESH:
            log.info("Rescanning %s…", host)
            try:
                discovered = discover_apps(host, verbose=verbose)
            except DiscoveryError as e:
                log.error("%s", e)
                log.info("Keeping existing cache.")
                continue
            if not discovered:
                log.warning("Rescan returned no apps; keeping previous cache.")
                continue
            save_cache(host, discovered)
            log.info("Updated cache (%d apps).", len(discovered))
            continue
        if result.action == FzfAction.TOGGLE_FAVORITE:
            if result.app:
                toggle_favorite(host, result.app.desktop_id, apps)
            continue
        if result.action == FzfAction.LAUNCH_EDIT and result.app:
            app = result.app
            path = prepare_temp_file(default_remote_launch_body(app.desktop_id))
            body: str | None = None
            try:
                try:
                    rc = run_editor(path)
                except OSError as e:
                    log.error("Could not run editor: %s", e)
                    continue
                if rc != 0:
                    log.info("Editor exited with status %s; returning to list.", rc)
                    continue
                body = read_edited_launch_body(path)
            finally:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            if not body:
                log.info("No launch command after edit; returning to list.")
                continue
            try:
                inner = finalize_remote_inner(body)
                run_waypipe_remote_inner(host, inner, detached=True)
            except OSError as e:
                log.error("Failed to start waypipe: %s", e)
                return 1
            log.info("Launched %s (edited command).", app.name)
            return 0
        if result.action == FzfAction.LAUNCH and result.app:
            try:
                launch_app(host, result.app, background=True)
            except OSError as e:
                log.error("Failed to start waypipe: %s", e)
                return 1
            log.info("Launched %s.", result.app.name)
            return 0

    return 0


def cmd_list(host: str) -> int:
    apps = load_cache(host)
    if not apps:
        log.error("No apps in cache. Run 'remote-app-launcher refresh --host <host>' first.")
        return 1
    stored = load_favorite_ids(host)
    fav_order = effective_favorite_order(apps, stored)
    for app, is_fav in sort_apps_for_display(apps, fav_order):
        print(format_fzf_line(app, is_favorite=is_fav))
    return 0


def main() -> int:
    config_host = load_host_from_config()
    host_parser = argparse.ArgumentParser(add_help=False)
    host_parser.add_argument("--host", help="Remote host (SSH target).")
    host_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed progress.")

    parser = argparse.ArgumentParser(
        description="Browse and launch remote Linux apps via Waypipe.",
        parents=[host_parser],
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("refresh", help="Scan remote host and update cache")
    subparsers.add_parser("launch", help="Pick app via fzf and launch via waypipe")
    subparsers.add_parser("list", help="List cached apps (same order as launcher)")

    parser.set_defaults(command="launch")

    args = parser.parse_args()
    configure_logging(verbose=getattr(args, "verbose", False))
    host = resolve_host(args.host, config_host)

    if not host:
        log.error("--host required (or set in config file).")
        log.error("Create %s/config.json with {\"host\": \"your-htpc\"}", get_config_dir())
        return 1

    command = args.command or "launch"
    if command == "refresh":
        return cmd_refresh(host, verbose=getattr(args, "verbose", False))
    if command == "launch":
        return cmd_launch(host, verbose=getattr(args, "verbose", False))
    if command == "list":
        return cmd_list(host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
