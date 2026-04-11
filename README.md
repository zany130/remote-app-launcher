# remote-app-launcher

Browse and launch desktop applications installed on a remote Linux HTPC from your local laptop. Uses [Waypipe](https://gitlab.freedesktop.org/mstoeckl/waypipe) to forward Wayland windows so they display locally.

## What it does

1. Connects to a remote Linux host over SSH
2. Discovers launchable apps by reading `.desktop` files in `/usr/share/applications` and `~/.local/share/applications`
3. Caches results locally (JSON) for fast startup
4. Shows a searchable list via [fzf](https://github.com/junegunn/fzf), with **favorites** at the top
5. Launches the selected app on the remote host through `waypipe ssh -t host sh -c '…'`, using a small default **remote** environment and `gtk-launch <desktop-id>` (or an edited command)

## v0.3 highlights

- **Edit launch command (Ctrl-E)** – Opens the remote launch snippet in `$VISUAL` / `$EDITOR` (temp file). Save to run that command once. A final `exec sleep 86400` line is **appended automatically** so the Waypipe session stays open (you do not add it in the editor).
- **Default remote env** – Normal launches prefix with `env GDK_BACKEND='wayland,x11' QT_QPA_PLATFORM='wayland;xcb' XDG_SESSION_TYPE=wayland` so GTK/Qt prefer Wayland with fallbacks. No global Electron/Chromium CLI flags; override per app in the editor when needed.

## v0.2 highlights

- **Favorites** – Stored per host in `~/.config/remote-app-launcher/favorites-<host>.json` (ordered list of desktop IDs). Shown with a **★** marker and sorted above other apps. IDs that are not in the current cache are ignored until that app appears again (e.g. after a rescan).
- **Rescan from the launcher** – Press **Ctrl-R** in fzf to SSH-scan the host again, update the cache, and reopen the list (simple relaunch loop; no live fzf mutation).
- **Favorite toggle** – **Ctrl-F** on the highlighted row adds or removes that app from favorites, then the list reopens.
- **Unified entrypoint** – Running `remote-app-launcher` with no subcommand starts the interactive launcher (same as `launch`).
- **Clearer errors** – SSH scan failures are reported explicitly; a failed rescan keeps the previous cache.

## Dependencies

- **Python 3.10+**
- **fzf** – fuzzy finder
- **waypipe** – Wayland proxy for remote display
- **SSH** – remote access

Install on both local and remote hosts. The remote needs `gtk-launch` and a Wayland session.

## Install

```bash
cd remote-app-launcher
pip install -e .
```

After pulling upgrades that add new Python modules, reinstall so your editable install’s import map stays in sync:

```bash
pip install -e /path/to/remote-app-launcher
```

## Usage

```bash
# Interactive launcher (default): fzf, then launch with Enter
remote-app-launcher --host htpc

# Same as above
remote-app-launcher launch --host htpc

# Scan remote host and update cache only
remote-app-launcher refresh --host htpc

# Print cached apps in launcher order (★ = favorite)
remote-app-launcher list --host htpc

# Verbose discovery logs
remote-app-launcher refresh --host htpc -v
```

### fzf keys (launcher)

| Key | Action |
|-----|--------|
| **Enter** | Launch selected app (default remote env + `gtk-launch`) |
| **Ctrl-E** | Edit the **remote** launch command in `$VISUAL` / `$EDITOR`, then run it once |
| **Ctrl-R** | Rescan remote and refresh cache |
| **Ctrl-F** | Toggle favorite for selected row |
| **Esc** | Quit |

### Edit launch (Ctrl-E)

- The temp file is a **newline-separated** shell snippet for the remote `sh -c` script. Full-line `#` comments are stripped; remaining non-empty lines are rejoined with newlines (lines are **not** merged with `;`).
- **`exec sleep 86400` is appended automatically** after your snippet so Waypipe keeps the tunnel open.
- Set `EDITOR` or `VISUAL` (e.g. `EDITOR="cursor --wait"` or `vim`).
- **Multiline env:** use `export` on earlier lines, then the command on a later line. A one-line `env VAR=val /path/to/app` also works. Note: in POSIX `sh`, `env VAR=val` on one line and the program on the **next** line are two separate commands—`env` does not apply to the next line unless you use `export` or put `env … cmd` on one line.

**Example – Cursor / Electron-style Wayland flags** (paths on the **remote** machine; launch body only, no `exec sleep`):

```sh
env GDK_BACKEND='wayland,x11' /usr/bin/cursor \
  --enable-features=UseOzonePlatform \
  --ozone-platform=wayland
```

Or one line:

```sh
env GDK_BACKEND='wayland,x11' /usr/bin/cursor --enable-features=UseOzonePlatform --ozone-platform=wayland
```

### Config file (optional)

```bash
mkdir -p ~/.config/remote-app-launcher
echo '{"host": "htpc"}' > ~/.config/remote-app-launcher/config.json
```

Then you can omit `--host`:

```bash
remote-app-launcher
remote-app-launcher refresh
```

### Local data files

| File | Purpose |
|------|---------|
| `~/.config/remote-app-launcher/config.json` | Default `host` (optional) |
| `~/.config/remote-app-launcher/apps-<host>.json` | Cached app list |
| `~/.config/remote-app-launcher/favorites-<host>.json` | Favorite desktop IDs (array of strings) |

## Filters

- **Terminal apps** – Excluded (Terminal=true)
- **Games** – Excluded if *only* categorized as a game (keeps gaming tools like launchers)
- **NoDisplay** – Excluded

## Troubleshooting

### Waypipe / SSH

1. Install waypipe on both local and remote
2. Add to `~/.ssh/config`:
   ```
   Host htpc
       SetEnv XDG_RUNTIME_DIR=/run/user/1000
   ```
3. Enable `AcceptEnv XDG_RUNTIME_DIR` in remote `/etc/ssh/sshd_config`
4. Remote must run a Wayland compositor (e.g. GNOME, KDE on Wayland)

### "gtk-launch not found" on remote

Install GTK/GLib on the remote host.

### Apps not launching

The waypipe process keeps the session open for 24 hours. To stop it early:

```bash
pkill -f "waypipe ssh"
```

### Rescan fails (e.g. SSH down)

The launcher keeps using the last good cache until the next successful refresh.

### `ModuleNotFoundError` (e.g. `edit_launch`)

Your install metadata is older than the repo (editable installs record which top-level modules exist). Reinstall from the project root:

```bash
pip install -e .
```
