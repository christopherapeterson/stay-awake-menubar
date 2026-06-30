"""Generate the groovy menu bar icons (template images) for Stay Awake.

Draws a chunky 70s-style coffee cup with wavy "groovy" steam, rendered at high
resolution and downscaled for crisp antialiasing. Outputs macOS *template*
images: solid black + alpha on a transparent canvas, so the menu bar recolors
them automatically for light/dark mode.

Two variants:
  * stay-awake-idle   - empty cup, no steam (Mac can sleep)
  * stay-awake-active - cup with three groovy steam swirls (staying awake)

Each is written at 1x (22pt) and 2x (44pt) into ../Resources, following Apple's
``name.png`` / ``name@2x.png`` retina naming so rumps/AppKit pick the right one.

Run:  ../.venv/bin/python make_icons.py
"""

import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "Resources")

SS = 16            # supersampling factor for smooth edges
BASE = 22         # logical points (menu bar icons are ~18-22pt)


def _new(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _wave(draw, x, y_top, y_bottom, amp, period, width, phase=0.0):
    """Draw one groovy (sine) steam swirl as a thick stroke."""
    pts = []
    steps = 80
    for i in range(steps + 1):
        t = i / steps
        y = y_top + (y_bottom - y_top) * t
        x_off = amp * math.sin(2 * math.pi * (y / period) + phase)
        # taper the amplitude toward the top so it curls outward like rising steam
        x_off *= 0.45 + 0.55 * t
        pts.append((x + x_off, y))
    draw.line(pts, fill=(0, 0, 0, 255), width=width, joint="curve")
    # round the ends
    r = width / 2
    for (px, py) in (pts[0], pts[-1]):
        draw.ellipse([px - r, py - r, px + r, py + r], fill=(0, 0, 0, 255))


def _cup(draw, S):
    """Draw a chunky retro coffee cup filling the lower portion of the canvas."""
    # Cup body: a rounded trapezoid (wider at top, gently tapered).
    top = 0.50 * S
    bot = 0.86 * S
    left_top, right_top = 0.20 * S, 0.66 * S
    left_bot, right_bot = 0.26 * S, 0.60 * S
    body = [
        (left_top, top), (right_top, top),
        (right_bot, bot), (left_bot, bot),
    ]
    draw.polygon(body, fill=(0, 0, 0, 255))
    # round the top rim with a fat ellipse (the "lip" of the cup)
    rim_h = 0.10 * S
    draw.ellipse([left_top, top - rim_h / 2, right_top, top + rim_h / 2],
                 fill=(0, 0, 0, 255))
    # round the bottom corners
    draw.ellipse([left_bot, bot - 0.06 * S, left_bot + 0.10 * S, bot + 0.02 * S],
                 fill=(0, 0, 0, 255))
    draw.ellipse([right_bot - 0.10 * S, bot - 0.06 * S, right_bot, bot + 0.02 * S],
                 fill=(0, 0, 0, 255))

    # Handle: a thick ring on the right, drawn as an arc stroke (open center).
    # Pulled left so its ends tuck into the cup body (no floating gap).
    hx0, hy0 = 0.55 * S, 0.55 * S
    hx1, hy1 = 0.82 * S, 0.80 * S
    draw.arc([hx0, hy0, hx1, hy1], start=-78, end=118,
             fill=(0, 0, 0, 255), width=int(0.08 * S))


def _saucer(draw, S):
    """A groovy little saucer line under the cup."""
    y = 0.90 * S
    draw.line([(0.16 * S, y), (0.70 * S, y)], fill=(0, 0, 0, 255),
              width=int(0.06 * S), joint="curve")


def build(active: bool, size: int) -> Image.Image:
    S = size * SS
    img, draw = _new(S)

    _cup(draw, S)
    _saucer(draw, S)

    if active:
        # Three groovy steam swirls rising from the cup, offset in phase so they
        # weave like a 70s pattern.
        w = int(0.075 * S)
        _wave(draw, 0.31 * S, 0.46 * S, 0.10 * S, amp=0.045 * S, period=0.30 * S,
              width=w, phase=0.0)
        _wave(draw, 0.43 * S, 0.46 * S, 0.06 * S, amp=0.055 * S, period=0.34 * S,
              width=w, phase=math.pi)
        _wave(draw, 0.55 * S, 0.46 * S, 0.12 * S, amp=0.045 * S, period=0.30 * S,
              width=w, phase=math.pi / 2)

    return img.resize((size, size), Image.LANCZOS)


def save(img: Image.Image, name: str):
    os.makedirs(RES, exist_ok=True)
    path = os.path.join(RES, name)
    img.save(path)
    return path


def main():
    for active, stem in ((False, "stay-awake-idle"), (True, "stay-awake-active")):
        one = build(active, BASE)
        two = build(active, BASE * 2)
        save(one, f"{stem}.png")
        save(two, f"{stem}@2x.png")
        print("wrote", stem, "(1x + @2x)")
    print("done ->", os.path.normpath(RES))


if __name__ == "__main__":
    main()
