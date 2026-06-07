# Clipboard Bridge

*Send text and auto-typed input from your phone to your computer over your local Wi-Fi. macOS / Windows / Linux. No cloud.*

Send text from your **phone** to your **computer's clipboard**, plus an
**autotyper** that types queued text into the focused window on a hotkey.
Runs entirely on your local Wi-Fi (no cloud) and works on macOS, Windows,
and Linux.

```
   ┌──────────────┐                       ┌────────────────┐
   │  Phone       │   ─── HTTP / LAN ───> │  cb-bridge     │
   │  (browser)   │                       │  on your       │
   │   • Send     │                       │  computer      │
   │   • Autotype │                       │   • Clipboard  │
   └──────────────┘                       │   • Autotyper  │
                                          └────────────────┘
```

- One-way: phone → computer
- Plain text only (no images / files / formatting)
- Protected by a 4-digit PIN (persistent; rotate with `cb-bridge regen-pin`)

---

## Install

The recommended installer is [`pipx`](https://pipx.pypa.io/), which
isolates the tool in its own virtual environment automatically.

### Option 1 — `pipx` from the GitHub Release (current recommended path)

The package isn't on PyPI yet. Until then, install directly from the GitHub
Release wheel:

```bash
pipx install https://github.com/phani69015/clipboard-bridge/releases/download/v0.1.0/clipboard_bridge-0.1.0-py3-none-any.whl
```

If you don't have `pipx`:

```bash
# macOS:    brew install pipx
# Linux:    sudo apt install pipx        (Debian/Ubuntu)
# Windows:  python -m pip install --user pipx

pipx ensurepath           # one-time, then open a new terminal
```

### Option 2 — `pipx` from PyPI (once published)

```bash
pipx install clipboard-bridge
```

Not yet available; this is what the install command will look like
once `clipboard-bridge` is published to PyPI.

### Option 3 — plain `pip` from the GitHub Release

```bash
pip install --user https://github.com/phani69015/clipboard-bridge/releases/download/v0.1.0/clipboard_bridge-0.1.0-py3-none-any.whl
```

### Option 4 — from a local checkout

```bash
git clone https://github.com/phani69015/clipboard-bridge
cd clipboard-bridge
pip install .
# or for development:
pip install -e .
```

After install, the `cb-bridge` command is on your PATH.

---

## Run

```bash
cb-bridge
```

You'll see a banner with the URL, PIN, and a QR code:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Clipboard Bridge v0.1.0

   URL  : http://192.168.1.6:8765
   Alt  : http://yourpc.local:8765   (only if your network supports mDNS)
   PIN  : 4729

 (PIN persists across restarts. Run "cb-bridge regen-pin" to rotate.)

 Scan this QR code with your phone camera:

   [ASCII QR code here]

 Press Ctrl+C to stop.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Autotyper hotkey: Ctrl+a   Abort: Esc
 Stop with Ctrl+C, or from any other terminal: cb-bridge stop
```

Scan the QR code with your phone camera, enter the PIN once, and you're in.

### Stopping the server

Two ways:
- Press **`Ctrl+C`** in the terminal where it's running.
- From any terminal: `cb-bridge stop`.

---

## CLI reference

| Command | Description |
|---|---|
| `cb-bridge` / `cb-bridge run` | Start the server |
| `cb-bridge stop` | Stop a running server (works from any terminal) |
| `cb-bridge status` | Show whether a server is running |
| `cb-bridge pin` | Print the persisted PIN |
| `cb-bridge regen-pin` | Generate and persist a new PIN |
| `cb-bridge --version` | Print version |
| `cb-bridge --help` | Show help |

The server writes a PID file at `<config_dir>/server.pid` while running,
so `cb-bridge stop` and `cb-bridge status` work from any terminal — even
after the original terminal is closed. Pressing `Ctrl+C` in the running
terminal also stops the server cleanly and removes the PID file.

`run` flags:

| Flag | Default | Description |
|---|---|---|
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `8765` | Listen port |
| `--no-hotkey` | off | Disable the autotyper hotkey listener |
| `--hotkey` | `<ctrl>+a` | Type-trigger hotkey (pynput syntax) |
| `--abort-key` | `<esc>` | Abort-typing hotkey |

Hotkey strings use [pynput modifier syntax](https://pynput.readthedocs.io/en/latest/keyboard.html#monitoring-the-keyboard):
`<cmd>`, `<shift>`, `<ctrl>`, `<alt>`, `<esc>`, `<f1>`–`<f20>`.

---

## First-run prompts (per OS)

### macOS

1. **Firewall:** "Do you want python3 to accept incoming network connections?" → click **Allow**.
2. **Accessibility (autotyper only):** Open **System Settings → Privacy & Security → Accessibility** and enable your terminal app. **Quit and relaunch the terminal**, then re-run `cb-bridge`. The clipboard feature works without this; only the autotyper hotkey needs it.

### Windows

1. **Windows Defender Firewall:** "Windows Defender Firewall has blocked some features..." → check both boxes → **Allow access**.
2. No extra permissions for the autotyper.

### Linux

1. **Clipboard backend** must be installed for the clipboard tab:
   - X11: `sudo apt install xclip` (or `xsel`)
   - Wayland: `sudo apt install wl-clipboard`
2. **Firewall** (only if enabled): `sudo ufw allow 8765/tcp`.
3. **Wayland autotyper:** Wayland blocks synthetic key injection. The autotyper may not work; clipboard mode does. Workaround: use an X11 session, or install `ydotool` separately.

---

## Connect from your phone

1. **Scan the QR code** in the terminal with your phone's camera, or
2. **Type the URL** manually (e.g. `http://192.168.1.6:8765`).
3. Enter the **4-digit PIN** once. Your phone remembers it.
4. Use the **Clipboard** or **Autotype** tab.

If the phone times out, it's almost always the host firewall. See troubleshooting below.

---

## Using it

### Clipboard tab
1. Type or paste into the textarea.
2. Tap **Send to Computer**.
3. Paste with `Cmd+V` (mac) / `Ctrl+V` (Win/Linux) anywhere on the host.

### Autotype tab
1. Paste the text you want auto-typed.
2. Pick **speed** (Slow / Normal / Fast); optional **human jitter**.
3. Tap **Queue for typing**.
4. On the host: focus the target field/window.
5. Press **`Ctrl+A`** (default).
6. After a 2-second pause, characters are typed.
7. Press **`Esc`** to abort.

The queued text **stays buffered after typing finishes** — press the hotkey again to retype the same content. A second hotkey press while typing is in progress is ignored. To replace the buffer, queue new text from the phone or tap **Clear queue**.

Maximum length per queue: **10,000 characters**.

---

## Where things are stored

| OS | Config (with PIN) | PID file (while running) |
|---|---|---|
| macOS | `~/Library/Application Support/clipboard-bridge/config.json` | `~/Library/Application Support/clipboard-bridge/server.pid` |
| Linux | `~/.config/clipboard-bridge/config.json` | `~/.config/clipboard-bridge/server.pid` |
| Windows | `%APPDATA%\clipboard-bridge\config.json` | `%APPDATA%\clipboard-bridge\server.pid` |

The PIN is stored as plain JSON, with file mode `0600` on Unix.
Delete the config file (or run `cb-bridge regen-pin`) to rotate the PIN.
The PID file is written on `cb-bridge run` startup and removed on clean
shutdown; stale PID files left by crashes are detected and cleaned up
automatically on the next `cb-bridge status` or `cb-bridge run`.

---

## Manual autostart (optional)

There's no built-in autostart command. If you want `cb-bridge` to run on every login:

### macOS — `launchd`

Create `~/Library/LaunchAgents/com.clipboardbridge.server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.clipboardbridge.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/cb-bridge</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/tmp/clipboard-bridge.log</string>
    <key>StandardErrorPath</key><string>/tmp/clipboard-bridge.log</string>
</dict>
</plist>
```

Find the path to `cb-bridge` with `which cb-bridge`. Then:

```bash
launchctl load ~/Library/LaunchAgents/com.clipboardbridge.server.plist
```

### Linux — XDG autostart

Create `~/.config/autostart/clipboard-bridge.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Clipboard Bridge
Exec=/path/to/cb-bridge
X-GNOME-Autostart-enabled=true
NoDisplay=true
```

### Windows — Startup folder

Press `Win+R`, type `shell:startup`, hit Enter. Create a shortcut to
`cb-bridge.exe` (find its path with `where cb-bridge`) in that folder.

---

## Troubleshooting

**Phone connection times out**
- Host firewall is blocking the port. Allow it (see "First-run prompts").
- Confirm phone and host are on the same Wi-Fi.
- Some Wi-Fi networks isolate clients. Try a personal hotspot.

**`yourpc.local` doesn't resolve from phone**
- Use the IP URL printed in the terminal (`http://192.168.x.x:8765`).

**"Incorrect PIN"**
- Run `cb-bridge pin` to see the current PIN.
- Or run `cb-bridge regen-pin` to set a new one (phone will prompt to re-enter).

**"Too many failed attempts"**
- 5 failed PIN attempts within 60s lock the IP for the rest of the window.
  Wait a minute.

**Autotyper hotkey does nothing**
- macOS: Accessibility permission missing. See "First-run prompts".
- Linux on Wayland: synthetic key injection is blocked; switch to X11 or install `ydotool`.
- Try a different hotkey: `cb-bridge --hotkey "<ctrl>+<shift>+a"`.

**Autotyper types into the wrong window**
- Whatever app is focused at the moment of typing receives the keystrokes.
  Click into the target field *before* pressing the hotkey. The 2-second
  pre-delay gives you a final moment to switch focus.

**Special / non-Latin characters type as `?`**
- Known limitation of `pynput` for some characters. Use Clipboard mode
  + manual paste for those.

**Server says "already running" but I can't find it**
- `cb-bridge status` will show the PID. `cb-bridge stop` ends it cleanly.
- If a stale PID file is left after a crash, it's auto-cleaned on the next
  `cb-bridge status` or `cb-bridge run`.

**Port 8765 already in use**
- `cb-bridge --port 9000`

---

## Building and testing locally

```bash
# Editable install for development
pip install -e .

# Run in place
cb-bridge

# Build distributable wheel + sdist
python -m pip install build
python -m build
# Outputs: dist/clipboard_bridge-0.1.0-py3-none-any.whl
#          dist/clipboard_bridge-0.1.0.tar.gz

# Install the built wheel into a fresh isolated environment
pipx install ./dist/clipboard_bridge-0.1.0-py3-none-any.whl
```

Pre-built artifacts for the latest release are also attached to the
[GitHub Releases](https://github.com/phani69015/clipboard-bridge/releases)
page — no local build required.

---

## Security notes

- Designed for **trusted local networks** (home Wi-Fi, personal hotspot).
- Traffic is **plain HTTP**, not encrypted. The PIN is the only access control.
- The autotyper synthesizes arbitrary keystrokes into the focused app. Treat
  the PIN like a password to your machine.
- **Do not** run on public/coffee-shop Wi-Fi.

---

## Limitations

- Phone → computer only (one-way)
- Plain text only
- No history of past clips
- No built-in autostart command (manual instructions above)
- Autotyper: 10,000 char cap per queue
- Linux Wayland: autotyper limited (clipboard works)
- Some non-Latin characters may type imperfectly through `pynput`

---

## Releases

Latest: **v0.1.0** — see the [GitHub Releases](https://github.com/phani69015/clipboard-bridge/releases)
page for downloadable wheels and sdists.

---

## License

MIT — see [LICENSE](LICENSE).
