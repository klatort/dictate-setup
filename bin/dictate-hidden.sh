#!/bin/bash
# Runs Dictate on a hidden pty - no terminal window.
# PATH is restricted so notify-send is NOT found: the app's toast
# notifications are disabled by design (the snackbar is the feedback).
export TERM=xterm
export PATH="$HOME/dictate-trial/pathless"
exec /usr/bin/python3 -c "
import pty
pty.spawn(['$HOME/dictate-trial/patched/dictate'])
"
