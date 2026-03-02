#!/usr/bin/env python3
"""Quick measurement of Hell Bot sprite data cost."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import extract_frames_custom, encode_animation, TRANS

HELLBOT_DIR = os.path.expanduser("~/Downloads/DARK Edition/Sprites/Hell Bot DARK")
HELLBOT_W, HELLBOT_H = 92, 36
HELLBOT_ANIMS = [
    ("hb_idle",   "idle 92x36.png",   None),
    ("hb_run",    "run 92x36.png",    None),
    ("hb_attack", "attack 92x36.png", None),
    ("hb_shoot",  "shoot 92x36.png",  None),
    ("hb_hit",    "hit 92x36.png",    None),
    ("hb_death",  "death 92x36.png",  None),
]

total = 0
overhead = 3 + len(HELLBOT_ANIMS) * 2  # chunk header: na + cw + ch + offsets
print(f"Cell size: {HELLBOT_W}x{HELLBOT_H}")
print(f"Chunk overhead: {overhead}b\n")

for name, fname, nf in HELLBOT_ANIMS:
    frames = extract_frames_custom(fname, HELLBOT_DIR, HELLBOT_W, HELLBOT_H, nf)
    block, info = encode_animation(name, frames, HELLBOT_W, HELLBOT_H)
    total += len(block)
    print(f"  {info}")

total += overhead
print(f"\n  hellbot_chunk TOTAL: {total}b")
print(f"  Current gfx used: 7217b")
print(f"  With hellbot: {7217 + total}b / 8192b ({(7217+total)*100//8192}%)")
print(f"  Remaining: {8192 - 7217 - total}b")
