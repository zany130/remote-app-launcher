#!/usr/bin/env python3
"""remote-app-launcher - Browse and launch remote Linux apps via Waypipe."""

import argparse
import logging
import sys

from cache import load_cache, save_cache
from discovery import discover_apps
from launcher import FzfError, launch_app, run_fzf
from utils import configure_logging, get_config_dir, load_host_from_config

log = logging.getLogger("remote_app_launcher.main")


def resolve_host(cli_host: str | None, config_host: str | None) -> str | None:
    return cli_host or config_host


def cmd_refresh(host: str, verbose: bool = False) -> int:
    log.info("Scanning apps on %s...", host)
    try:
        apps = discover_apps(host, verbose=verbose)
    except Exception as e:
        log.error("Error discovering apps: %s", e)
        return 1
    save_cache(host, apps)
    log.info("Cached %d apps.", len(apps))
    return 0


def cmd_launch(host: str) -> int:
    apps = load_cache(host)
    try:
        selected = run_fzf(apps, header=f"Select app on {host} (type to search)")
    except FzfError as e:
        log.error("%s", e)
        return 1
    if not selected:
        return 0
    launch_app(host, selected, background=True)
    log.info("Launched %s.", selected.name)
    return 0


def cmd_list(host: str) -> int:
    apps = load_cache(host)
    if not apps:
        log.error("No apps in cache. Run 'remote-app-launcher refresh --host <host>' first.")
        return 1
    for app in apps:
        print(app.fzf_line())
    return 0


def main() -> int:
    config_host = load_host_from_config()
    host_parser = argparse.ArgumentParser(add_help=False)
    host_parser.add_argument("--host", help="Remote host (SSH target).")
    host_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed progress.")

    parser = argparse.ArgumentParser(description="Browse and launch remote Linux apps via Waypipe.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("refresh", parents=[host_parser], help="Scan remote host and update cache")
    subparsers.add_parser("launch", parents=[host_parser], help="Pick app via fzf and launch via waypipe")
    subparsers.add_parser("list", parents=[host_parser], help="List cached apps")

    args = parser.parse_args()
    configure_logging(verbose=getattr(args, "verbose", False))
    host = resolve_host(args.host, config_host)

    if not host:
        log.error("--host required (or set in config file).")
        log.error("Create %s/config.json with {\"host\": \"your-htpc\"}", get_config_dir())
        return 1

    if args.command == "refresh":
        return cmd_refresh(host, verbose=getattr(args, "verbose", False))
    if args.command == "launch":
        return cmd_launch(host)
    if args.command == "list":
        return cmd_list(host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
