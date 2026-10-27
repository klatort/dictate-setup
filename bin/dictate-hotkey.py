#!/usr/bin/env python3
"""dictate-hotkey: toggle Dictate with a bare Right-Ctrl tap.

Right-Ctrl press+release with no other key in between toggles dictation
via the app's tray DBus Activate. Right-Ctrl used in combos is ignored.
"""
import glob, os, select, struct, subprocess, re, time

EV_KEY = 0x01
KEY_RIGHTCTRL = 97
EV_FMT = "@llHHi"
EV_SIZE = struct.calcsize(EV_FMT)
LOG = "/tmp/dictate-hotkey-keys.log"

def log(msg):
    with open(LOG, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")

def gdbus(*a):
    try:
        return subprocess.check_output(
            ["gdbus", "call", "--session"] + list(a),
            stderr=subprocess.DEVNULL, timeout=5).decode()
    except Exception:
        return ""

def toggle_dictation():
    log("TOGGLE fired")
    out = gdbus("--dest", "org.freedesktop.DBus",
                "--object-path", "/org/freedesktop/DBus",
                "--method", "org.freedesktop.DBus.ListNames")
    for name in re.findall(r"'(org\.kde\.StatusNotifierItem-[\d-]+)'", out):
        tip = gdbus("--dest", name, "--object-path", "/StatusNotifierItem",
                    "--method", "org.freedesktop.DBus.Properties.Get",
                    "org.kde.StatusNotifierItem", "ToolTip")
        if "low_latency_dictation" in tip:
            subprocess.call(
                ["gdbus", "call", "--session", "--dest", name,
                 "--object-path", "/StatusNotifierItem",
                 "--method", "org.kde.StatusNotifierItem.Activate", "0", "0"],
                stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=5)
            log("activated via %s" % name)
            return
    log("no dictate SNI found")

def open_keyboards():
    fds = {}
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            continue
        fds[fd] = path
    return fds

def main():
    log("daemon started (hotkey only)")
    rc_down = False
    combo = False
    last_release = 0.0
    while True:
        fds = open_keyboards()
        if not fds:
            time.sleep(1)
            continue
        while fds:
            r, _, _ = select.select(list(fds), [], [], 5)
            if not r:
                for fd in fds:
                    os.close(fd)
                break
            for fd in r:
                try:
                    data = os.read(fd, EV_SIZE * 8)
                except OSError:
                    os.close(fd)
                    del fds[fd]
                    continue
                for i in range(0, len(data) - EV_SIZE + 1, EV_SIZE):
                    _, _, typ, code, val = struct.unpack_from(EV_FMT, data, i)
                    if typ != EV_KEY or val == 2:
                        continue
                    if code == KEY_RIGHTCTRL:
                        if val == 1:
                            rc_down, combo = True, False
                        else:
                            now = time.time()
                            # dedup: one physical key reports on several
                            # event nodes; ignore echoes within 120ms
                            if rc_down and not combo and now - last_release > 0.12:
                                last_release = now
                                toggle_dictation()
                            rc_down = False
                    elif rc_down and val == 1:
                        combo = True

if __name__ == "__main__":
    main()
