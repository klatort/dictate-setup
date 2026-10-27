#!/bin/bash
# Installer for the low_latency_dictation setup (KDE Plasma / Wayland).
# Target: Fedora Atomic / Bazzite. Adapt paths/package names for other distros.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/dictate-trial"
BIN_DIR="$HOME/bin"

echo "== 1/7: user bin + app dirs =="
mkdir -p "$BIN_DIR" "$APP_DIR/patched" "$APP_DIR/pathless"

echo "== 2/7: input group for uinput (hotkey + paste) =="
if ! id -nG "$USER" | grep -qw input; then
    if getent group input >/dev/null; then
        # Fedora Atomic keeps system groups in /usr/lib/group; usermod may
        # silently fail, so append the override line directly.
        grep -q "^input:.*\b$USER\b" /etc/group || \
            echo "input:x:$(getent group input | cut -d: -f3):$USER" | sudo tee -a /etc/group >/dev/null
        echo "   added $USER to 'input' - LOG OUT/IN for it to take effect"
    fi
fi

echo "== 3/7: install scripts =="
install -m755 "$REPO_DIR/bin/dictate-hotkey.py"       "$BIN_DIR/dictate-hotkey.py"
install -m755 "$REPO_DIR/bin/dictate-snackbar-gtk.py" "$BIN_DIR/dictate-snackbar-gtk.py"
install -m755 "$REPO_DIR/bin/dictate-hidden.sh"       "$BIN_DIR/dictate-hidden.sh"

echo "== 4/7: config =="
mkdir -p "$HOME/.config/low_latency_dictation"
[ -f "$HOME/.config/low_latency_dictation/config.yaml" ] || \
    cp "$REPO_DIR/config/config.yaml" "$HOME/.config/low_latency_dictation/config.yaml"

echo "== 5/7: Geist font (user-level) =="
if ! fc-list | grep -qi "Geist"; then
    mkdir -p "$HOME/.local/share/fonts"
    tmp=$(mktemp -d)
    url=$(curl -s https://api.github.com/repos/vercel/geist-font/releases/latest \
          | python3 -c "import json,sys;print([a['browser_download_url'] for a in json.load(sys.stdin)['assets'] if a['name'].endswith('.zip')][0])")
    curl -sL -o "$tmp/geist.zip" "$url"
    python3 - "$tmp/geist.zip" "$HOME/.local/share/fonts" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
for n in z.namelist():
    if n.endswith(("Geist-Regular.ttf", "Geist-Medium.ttf", "Geist-SemiBold.ttf")):
        open(sys.argv[2] + "/" + n.split("/")[-1], "wb").write(z.read(n))
PY
    fc-cache -f "$HOME/.local/share/fonts" >/dev/null
    rm -rf "$tmp"
fi

echo "== 6/7: prompt to install the patched binary =="
if [ ! -x "$APP_DIR/patched/dictate" ]; then
    cat <<'MSG'
   The patched binary (absolute-silence VAD gate, kills Whisper's
   "Thank you." hallucination on silence) is NOT included in this repo
   because it is a 75 MB build artifact. Build it with:

       ./build-patched-binary.sh

   That script clones the upstream repo, applies patch/apply_gate.py,
   and builds inside a distrobox container. Run this installer again
   afterwards to finish.
MSG
fi

echo "== 7/7: services + KWin rule =="
mkdir -p "$HOME/.config/systemd/user"
cp "$REPO_DIR"/systemd/*.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now dictate dictate-hotkey dictate-snackbar

# KWin rule: keep the pill above, unfocused, bottom-center. Adjust
# position= if your resolution/primary monitor differ (see README).
if [ ! -f "$HOME/.config/kwinrulesrc" ]; then
    cp "$REPO_DIR/kwin/kwinrulesrc" "$HOME/.config/kwinrulesrc"
else
    echo "   ~/.config/kwinrulesrc exists - merge kwin/kwinrulesrc manually"
fi
qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || true

echo
echo "Done. Tap RIGHT CTRL to dictate. See README.md for customisation + removal."
