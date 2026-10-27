#!/bin/bash
# Full removal - complete footprint.
systemctl --user disable --now dictate dictate-hotkey dictate-snackbar 2>/dev/null
rm -f "$HOME/.config/systemd/user/dictate.service" \
      "$HOME/.config/systemd/user/dictate-hotkey.service" \
      "$HOME/.config/systemd/user/dictate-snackbar.service"
systemctl --user daemon-reload
# remove only our rule if kwinrulesrc contains nothing else
if grep -q "dictate-snackbar" "$HOME/.config/kwinrulesrc" 2>/dev/null; then
    rm -f "$HOME/.config/kwinrulesrc"
fi
rm -f "$HOME/bin/dictate-hidden.sh" "$HOME/bin/dictate-hotkey.py" \
      "$HOME/bin/dictate-snackbar-gtk.py"
rm -rf "$HOME/.config/low_latency_dictation" "$HOME/.cache/low_latency_dictation"
rm -rf "$HOME/dictate-trial" "$HOME/low_latency_dictation"
rm -f /tmp/dictate-*.log
sudo sed -i "/^input:.*\b$USER\b\$/d" /etc/group
echo "Dictate setup removed. Log out/in to refresh group membership."
