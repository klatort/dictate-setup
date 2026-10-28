#!/bin/bash
# Runs Dictate on a hidden pty - no terminal window.
# PATH is restricted so notify-send is NOT found: the app's toast
# notifications are disabled by design (the snackbar is the feedback).
export TERM=xterm
export PATH="$HOME/dictate-trial/pathless"

# Wait for the audio stack to expose a capture device (boot race guard,
# up to 60s). pactl lives in /usr/bin, outside the restricted PATH.
for i in $(seq 1 60); do
    if /usr/bin/pactl list sources 2>/dev/null | grep -q "alsa_input\|source"; then
        break
    fi
    sleep 1
done

exec /usr/bin/python3 -c "
import pty
pty.spawn(['$HOME/dictate-trial/patched/dictate'])
"
