# remote-app-launcher

Browse and launch desktop applications installed on a remote Linux HTPC from your local laptop. Uses [Waypipe](https://gitlab.freedesktop.org/mstoeckl/waypipe) to forward Wayland windows so they display locally.

## What it does

1. Connects to a remote Linux host over SSH
2. Discovers launchable apps by reading `.desktop` files in `/usr/share/applications` and `~/.local/share/applications`
3. Caches results locally (JSON) for fast startup
4. Shows a searchable list via [fzf](https://github.com/junegunn/fzf)
5. Launches the selected app on the remote host with `waypipe ssh -t host gtk-launch <desktop-id>`, displaying the window locally

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

## Usage

```bash
# Scan remote host and cache apps
remote-app-launcher refresh --host htpc

# Launch an app (opens fzf)
remote-app-launcher launch --host htpc

# List cached apps
remote-app-launcher list --host htpc

# Verbose output
remote-app-launcher refresh --host htpc -v
```

### Config file (optional)

```bash
mkdir -p ~/.config/remote-app-launcher
echo '{"host": "htpc"}' > ~/.config/remote-app-launcher/config.json
```

Then you can omit `--host`:

```bash
remote-app-launcher refresh
remote-app-launcher launch
```

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
pkill -f "waypipe ssh.*gtk-launch"
```

### ChromeOS Crostini – invisible fzf UI

If the fzf selection list appears blank (you can press Enter but see nothing), the
launcher cannot render its TUI because the process lacks access to the controlling
terminal (`/dev/tty`).

The launcher now opens `/dev/tty` explicitly.  Always run
`remote-app-launcher launch` **directly inside the Crostini Terminal app**, not via
a desktop shortcut, cron job, or any wrapper that detaches from the terminal.

If you see:
```
Cannot open /dev/tty for fzf TUI (…). Run 'remote-app-launcher launch' from an interactive terminal.
```
it means no TTY is available.  Switch to an interactive terminal session and try again.
