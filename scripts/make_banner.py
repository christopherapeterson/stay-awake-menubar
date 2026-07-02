"""Render the README banner (docs/banner.png) in the brand palette.

A wide beige card with the app icon and an Avenir Next wordmark: espresso
"Stay Awake", a caramel accent rule, and a mocha tagline. Rendered offscreen
via AppKit (same trick used to verify the control panel), so the typography
matches the app exactly.

Run:  ../.venv/bin/python make_banner.py
"""

import os

from AppKit import (
    NSApplication,
    NSAttributedString,
    NSBitmapImageRep,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGradient,
    NSImage,
    NSImageScaleProportionallyUpOrDown,
    NSImageView,
    NSKernAttributeName,
    NSMakeRect,
    NSPNGFileType,
    NSTextField,
    NSView,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

W, H = 1400, 420


def _rgb(r, g, b, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r / 255, g / 255, b / 255, a)


BEIGE_TOP = _rgb(242, 234, 219)
BEIGE_BOT = _rgb(226, 213, 190)
MOCHA = _rgb(111, 78, 55)
ESPRESSO = _rgb(75, 54, 33)
CARAMEL = _rgb(164, 117, 81)


class _GradientView(NSView):
    def drawRect_(self, _rect):
        NSGradient.alloc().initWithStartingColor_endingColor_(BEIGE_BOT, BEIGE_TOP) \
            .drawInRect_angle_(self.bounds(), 90.0)


def _text(root, s, x, y, w, h, font, color, kern=0.0):
    attrs = {NSFontAttributeName: font, NSForegroundColorAttributeName: color}
    if kern:
        attrs[NSKernAttributeName] = kern
    lbl = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    lbl.setBezeled_(False)
    lbl.setDrawsBackground_(False)
    lbl.setEditable_(False)
    lbl.setSelectable_(False)
    lbl.setAttributedStringValue_(
        NSAttributedString.alloc().initWithString_attributes_(s, attrs))
    root.addSubview_(lbl)


def main():
    NSApplication.sharedApplication()
    root = _GradientView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))

    # Icon, left side of the lockup.
    icon = NSImageView.alloc().initWithFrame_(NSMakeRect(330, (H - 200) / 2, 200, 200))
    img = NSImage.alloc().initWithContentsOfFile_(os.path.join(ROOT, "Resources", "app-icon.png"))
    if img is not None:
        icon.setImage_(img)
    icon.setImageScaling_(NSImageScaleProportionallyUpOrDown)
    root.addSubview_(icon)

    # Wordmark block.
    tx = 580
    title_font = (NSFont.fontWithName_size_("AvenirNext-Bold", 82)
                  or NSFont.boldSystemFontOfSize_(82))
    _text(root, "Stay Awake", tx, 208, 700, 108, title_font, ESPRESSO)

    # Caramel accent rule between wordmark and tagline.
    rule = NSView.alloc().initWithFrame_(NSMakeRect(tx + 6, 192, 130, 6))
    rule.setWantsLayer_(True)
    rule.layer().setCornerRadius_(3)
    rule.layer().setBackgroundColor_(CARAMEL.CGColor())
    root.addSubview_(rule)

    tag_font = (NSFont.fontWithName_size_("AvenirNext-Medium", 25)
                or NSFont.systemFontOfSize_(25))
    _text(root, "A groovy caffeinate companion for your menu bar",
          tx + 4, 140, 720, 36, tag_font, MOCHA)

    small_font = (NSFont.fontWithName_size_("AvenirNext-DemiBold", 14)
                  or NSFont.boldSystemFontOfSize_(14))
    _text(root, "B E I G E  ·  M O C H A  ·  C A F F E I N E",
          tx + 6, 104, 720, 22, small_font, CARAMEL, kern=1.5)

    rect = root.bounds()
    rep = root.bitmapImageRepForCachingDisplayInRect_(rect)
    root.cacheDisplayInRect_toBitmapImageRep_(rect, rep)
    out = os.path.join(ROOT, "docs", "banner.png")
    rep.representationUsingType_properties_(NSPNGFileType, None) \
        .writeToFile_atomically_(out, True)
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
