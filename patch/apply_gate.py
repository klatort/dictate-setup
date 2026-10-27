#!/usr/bin/env python3
"""Add an absolute-silence gate to low_latency_dictation's VAD.

Whisper hallucinates "Thank you." when fed near-silence. The app's VAD only
compares recent energy to the buffer average (a ratio), so tiny digital blips
in a silent room still register as speech. This gate makes near-silence
(strictly below a small absolute level) count as quiet, regardless of ratio.

Usage: apply_gate.py [path-to-cloned-repo]   (default: ~/low_latency_dictation)
"""
import os, sys

repo = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/low_latency_dictation")
path = os.path.join(repo, "vad", "vad.go")
src = open(path).read()

anchor = "\t// If recent energy is higher than the threshold relative to the average,"
gate = """\t// Absolute floor: near-digital-silence never counts as speech,
\t// regardless of the ratio to the buffer average. Prevents Whisper
\t// hallucinating ("Thank you.") on tiny blips in a silent room.
\tif energyLast < 0.004 {
\t\treturn true
\t}

"""

if "Absolute floor" in src:
    print("already patched")
    sys.exit(0)
assert anchor in src, "anchor not found in %s" % path
open(path, "w").write(src.replace(anchor, gate + anchor, 1))
print("patched %s" % path)
