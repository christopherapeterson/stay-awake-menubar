"""Generate AppIcon.icns for the Stay Awake .app bundle.

Unlike the menu bar template icons (black + alpha), the *app* icon is the full
colored Finder/Spotlight icon: a groovy warm-orange rounded square with a cream
coffee cup and steam. Renders a 1024px master, builds the standard .iconset, and
runs iconutil to produce Resources/AppIcon.icns.

Run:  ../.venv/bin/python make_app_icon.py
"""

import math
import os
import subprocess

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "Resources")

BG_TOP = (247, 178, 88)     # warm 70s orange
BG_BOT = (236, 130, 74)     # deeper amber
CUP = (255, 244, 224)       # cream
STEAM = (255, 244, 224)


def _vertical_gradient(size, top, bot):
    base = Image.new("RGBA", (size, size))
    px = base.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b, 255)
    return base


def _rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1],
                                        radius=radius, fill=255)
    return m


def _wave(draw, x, y_top, y_bottom, amp, period, width, phase, fill):
    pts = []
    steps = 120
    for i in range(steps + 1):
        t = i / steps
        y = y_top + (y_bottom - y_top) * t
        xo = amp * math.sin(2 * math.pi * (y / period) + phase) * (0.45 + 0.55 * t)
        pts.append((x + xo, y))
    draw.line(pts, fill=fill, width=width, joint="curve")
    r = width / 2
    for (px_, py_) in (pts[0], pts[-1]):
        draw.ellipse([px_ - r, py_ - r, px_ + r, py_ + r], fill=fill)


def build_master(S=1024):
    icon = _vertical_gradient(S, BG_TOP, BG_BOT)
    icon.putalpha(_rounded_mask(S, int(S * 0.22)))  # squircle-ish corners
    d = ImageDraw.Draw(icon)

    # Cup body (centered, lower-middle), cream.
    top, bot = 0.50 * S, 0.74 * S
    lt, rt = 0.34 * S, 0.62 * S
    lb, rb = 0.38 * S, 0.58 * S
    d.polygon([(lt, top), (rt, top), (rb, bot), (lb, bot)], fill=CUP)
    d.ellipse([lt, top - 0.05 * S, rt, top + 0.05 * S], fill=CUP)
    d.ellipse([lb, bot - 0.05 * S, lb + 0.08 * S, bot + 0.02 * S], fill=CUP)
    d.ellipse([rb - 0.08 * S, bot - 0.05 * S, rb, bot + 0.02 * S], fill=CUP)
    # saucer
    d.line([(0.30 * S, 0.78 * S), (0.66 * S, 0.78 * S)], fill=CUP,
           width=int(0.045 * S), joint="curve")
    # handle
    d.arc([0.55 * S, 0.55 * S, 0.74 * S, 0.72 * S], start=-78, end=118,
          fill=CUP, width=int(0.05 * S))

    # Three groovy steam swirls.
    w = int(0.05 * S)
    _wave(d, 0.42 * S, 0.47 * S, 0.20 * S, 0.035 * S, 0.26 * S, w, 0.0, STEAM)
    _wave(d, 0.50 * S, 0.47 * S, 0.16 * S, 0.040 * S, 0.30 * S, w, math.pi, STEAM)
    _wave(d, 0.58 * S, 0.47 * S, 0.22 * S, 0.035 * S, 0.26 * S, w, math.pi / 2, STEAM)
    return icon


def main():
    master = build_master(1024)
    iconset = os.path.join(RES, "AppIcon.iconset")
    os.makedirs(iconset, exist_ok=True)
    specs = [
        (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
    ]
    for px, name in specs:
        master.resize((px, px), Image.LANCZOS).save(os.path.join(iconset, name))
    out = os.path.join(RES, "AppIcon.icns")
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
    master.resize((512, 512), Image.LANCZOS).save(os.path.join(RES, "app-icon.png"))
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
