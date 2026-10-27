# dictate-setup — privacy-first, low-latency voice dictation for KDE Plasma (Wayland)

A complete, batteries-included dictation setup built on
[`electronstudio/low_latency_dictation`](https://github.com/electronstudio/low_latency_dictation):
local Whisper inference on your GPU, a right-Ctrl hotkey, and a minimal
bottom-center snackbar. No cloud, nothing leaves the machine.

Built and battle-tested on **Bazzite** (Fedora Atomic, KDE Plasma 6.7 Wayland,
NVIDIA RTX 3070), but it should work on any KDE Plasma Wayland system with a
GPU supported by whisper.cpp's Vulkan backend.

## What you get

- **Tap Right Ctrl** → a black pill appears bottom-center with bouncy dots:
  `Listening` → speak → tap again → `Transcribing` → text is pasted into
  whatever text box has focus (~0.7s).
- **English + Spanish auto-detection** per utterance.
- **No terminal window**, no app notifications — just the pill.
- **No "Thank you." hallucinations**: includes a patch to the upstream VAD
  (absolute-silence gate) plus a rebuild script.
- **Proper services**: three systemd user units, auto-restart, start at login.
- **One-command removal** (`REMOVE.sh`) — nothing lingers.

## Architecture

| Piece | What it is |
|---|---|
| `bin/dictate-hotkey.py` | Watches `/dev/input` for a bare Right-Ctrl tap (with cross-device echo dedup) and toggles dictation via the app's tray DBus interface. |
| `bin/dictate-snackbar-gtk.py` | GTK4 pill: black background, 1.5px white border, Geist typeface, dots painted on a canvas and driven by the frame clock. Polls app state via native Gio DBus in a background thread. |
| `bin/dictate-hidden.sh` | Runs the app on a hidden pseudo-terminal with a PATH that excludes `notify-send` (disables the app's toast popups by design). |
| `systemd/*.service` | Persistent user units for the three components. |
| `kwin/kwinrulesrc` | KWin rule: pill stays above, unfocused (so pastes land in *your* window), no border, skip taskbar, fixed bottom-center position. |
| `config/config.yaml` | App config: large-v3-turbo, `final-model: none` (instant paste), language auto-detect, strict VAD. |
| `patch/apply_gate.py` | Adds an absolute-silence gate to the upstream VAD — the fix for Whisper inventing "Thank you." on near-silence. |
| `build-patched-binary.sh` | Clones upstream, applies the patch, builds the patched binary (Vulkan) inside a distrobox container. |

## Install

```bash
git clone <this repo> ~/dictate-setup && cd ~/dictate-setup
./build-patched-binary.sh     # builds the patched app (~20-40 min first run)
./install.sh
# log out and back in once (input-group membership for /dev/uinput)
```

Requirements: KDE Plasma on Wayland, `distrobox` (for the build), Python 3 with
PyGObject/GTK4 (default on Fedora KDE), `git`, and an internet connection for
the model download (~550 MB, fetched automatically on first launch).

## Usage

- **Tap Right Ctrl**: start listening. The pill appears.
- **Speak**, then **tap Right Ctrl** again: text is transcribed and pasted.
- Language is auto-detected per utterance (English, Spanish, 99 more).
- **Discard a session** without pasting: right-click the tray icon → "Delete session".

## Customisation

- **Hotkey**: right Ctrl is chosen because it is rarely used on its own.
  To change the key, edit `KEY_RIGHTCTRL = 97` in `bin/dictate-hotkey.py`
  (see `linux/input-event-codes.h`; mind that left/right variants differ).
- **Snackbar position**: the KWin rule's `position=807,950` assumes a 1920x1080
  primary monitor. For other resolutions set
  `x = (screenWidth − barWidth)/2`, `y = screenHeight − ~130`, then
  `qdbus org.kde.KWin /KWin reconfigure`.
- **Font**: the pill ships with [Geist](https://vercel.com/font). Any installed
  font works — change `font-family` in `bin/dictate-snackbar-gtk.py`.
- **Model / quality**: edit `config/config.yaml`. `final-model: none` uses the
  live model's output directly (fastest); set a final model for a slower,
  higher-quality second pass.
- **Hallucination gate**: `patch/apply_gate.py` uses `0.004` as the absolute
  silence floor. Raise it if stray text still appears on silence; lower it if
  the first word of quiet speech is clipped. Rebuild after changing.

## Removal

```bash
./REMOVE.sh
```

## Notes & pitfalls (learned the hard way)

- **Fedora Atomic / Bazzite**: system groups live in `/usr/lib/group`, so
  `usermod -aG input` may silently fail. `install.sh` appends the override line
  to `/etc/group` instead. Log out/in to apply.
- **Flatpak is not recommended** for the app: its DBus sandbox blocks the
  system-tray interface the hotkey daemon uses. Use the standalone binary.
- **`freq-thold`** above 100 mangles the audio fed to Whisper (the filter runs
  in place on the buffer) — keep it at 100.
- Whisper's "Thank you." hallucination is *structural* with the app's original
  ratio-based VAD; only an absolute silence floor (this patch) fixes it.
- The app only pastes on finalize; streaming text into the box was tried and
  removed — it fights the model's self-revisions.

## License

Scripts in this repo: MIT. The underlying app is GPL-3.0; the patched binary is
a build of it and inherits that license.
