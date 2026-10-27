#!/usr/bin/env python3
"""dictate-snackbar v6: butter-smooth.

- DBus via native Gio (no gdbus subprocesses), polled in a background
  thread so the GTK main loop never blocks.
- Dots drawn on a DrawingArea (paint-only, no per-frame relayout),
  advanced by the frame clock.
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
import re, time, math, threading
from gi.repository import Gtk, Gdk, GLib, Gio

POLL_MS = 0.2
DOT_PERIOD = 1.8
DOT_HOP = 4.0
DOT_STAGGER = 0.22

CSS = """
window { background: transparent; }
box.pill {
  background: #000000;
  border: 1.5px solid #ffffff;
  border-radius: 999px;
  padding: 10px 22px;
  margin: 3px;
}
label.state {
  color: #ffffff;
  font-family: "Geist";
  font-size: 13pt;
  font-weight: 600;
}
"""

_bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

def dbus_call(dest, path, iface, method, params, reply_type):
    try:
        res = _bus.call_sync(dest, path, iface, method, params, reply_type,
                             Gio.DBusCallFlags.NONE, -1, None)
        return res.unpack()
    except Exception:
        return None

def find_sni():
    res = dbus_call("org.freedesktop.DBus", "/org/freedesktop/DBus",
                    "org.freedesktop.DBus", "ListNames", None,
                    GLib.VariantType("(as)"))
    if not res:
        return None
    for name in res[0]:
        if not name.startswith("org.kde.StatusNotifierItem-"):
            continue
        v = dbus_call(name, "/StatusNotifierItem", "org.freedesktop.DBus.Properties",
                      "Get", GLib.Variant("(ss)", ("org.kde.StatusNotifierItem", "ToolTip")),
                      GLib.VariantType("(v)"))
        if v and "low_latency_dictation" in str(v[0]):
            return name
    return None

def read_state(name):
    if not name:
        return "PAUSED"
    v = dbus_call(name, "/StatusNotifierItem", "org.freedesktop.DBus.Properties",
                  "Get", GLib.Variant("(ss)", ("org.kde.StatusNotifierItem", "ToolTip")),
                  GLib.VariantType("(v)"))
    if not v:
        return "PAUSED"
    m = re.search(r"(PAUSED|LISTENING|DICTATING|FINALIZING)", str(v[0]))
    return m.group(1) if m else "PAUSED"

class Dots(Gtk.DrawingArea):
    """Three bouncing dots, painted directly - no relayout, no child widgets."""
    def __init__(self):
        super().__init__()
        self.set_size_request(40, 16)
        self.set_draw_func(self.on_draw)
        self.active = False
        self.add_tick_callback(self.on_tick)

    def on_tick(self, w, clock):
        if self.active:
            self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def on_draw(self, area, cr, width, height):
        t = time.monotonic()
        cy = height / 2 + 2
        for i in range(3):
            phase = ((t - i * DOT_STAGGER) % DOT_PERIOD) / DOT_PERIOD
            if phase < 0.35:
                hop = math.sin((phase / 0.35) * math.pi / 2)
            elif phase < 0.70:
                hop = math.cos(((phase - 0.35) / 0.35) * math.pi / 2)
            else:
                hop = 0.0
            y = cy - DOT_HOP * hop
            alpha = 0.35 + 0.65 * hop
            cr.set_source_rgba(1.0, 1.0, 1.0, alpha)
            cr.arc(7 + i * 13, y, 3.0, 0, 2 * math.pi)
            cr.fill()

class Bar:
    def __init__(self):
        self.win = Gtk.Window()
        self.win.set_title("dictate-snackbar")
        self.win.set_decorated(False)
        self.win.set_resizable(False)
        self.win.set_size_request(306, -1)

        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        pill.get_style_context().add_class("pill")
        pill.set_halign(Gtk.Align.CENTER)
        self.state_lbl = Gtk.Label()
        self.state_lbl.get_style_context().add_class("state")
        self.state_lbl.set_halign(Gtk.Align.CENTER)
        self.state_lbl.set_valign(Gtk.Align.CENTER)
        pill.append(self.state_lbl)
        self.dots = Dots()
        self.dots.set_valign(Gtk.Align.CENTER)
        pill.append(self.dots)

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.revealer.set_transition_duration(280)
        self.revealer.set_child(pill)
        self.revealer.set_reveal_child(False)
        self.win.set_child(self.revealer)

        self.win.present()
        self.win.set_visible(False)
        self.current = None

        t = threading.Thread(target=self.poll_loop, daemon=True)
        t.start()

    def poll_loop(self):
        """Background thread: native DBus polling, never blocks the UI."""
        sni = None
        while True:
            state = read_state(sni)
            if state == "PAUSED" and sni is None:
                sni = find_sni()
                state = read_state(sni)
            elif state == "PAUSED":
                # app may have restarted under a new name
                sni = find_sni()
                state = read_state(sni)
            GLib.idle_add(self.apply_state, state)
            time.sleep(POLL_MS)

    def apply_state(self, state):
        if state != self.current:
            self.current = state
            if state in ("LISTENING", "DICTATING"):
                self.state_lbl.set_text("Listening")
                self.dots.active = True
                self.win.set_visible(True)
                self.revealer.set_reveal_child(True)
            elif state == "FINALIZING":
                self.state_lbl.set_text("Transcribing")
                self.dots.active = True
                self.win.set_visible(True)
                self.revealer.set_reveal_child(True)
            else:
                self.dots.active = False
                self.revealer.set_reveal_child(False)
                GLib.timeout_add(320, self.hide_now)
        return False

    def hide_now(self):
        if self.current == "PAUSED":
            self.win.set_visible(False)
        return False

def main():
    Bar()
    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    main()
