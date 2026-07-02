"""A pretty floating control panel for Stay Awake.

rumps' built-in dialogs are bare NSAlerts, so this module builds a real AppKit
window instead: a warm orange gradient card (matching the app icon), the groovy
cup up top, a live status line, one big Turn On / Turn Off button, and a row of
preset-duration pills. It pops up when the app is opened (or re-opened), when
the menu status line is clicked, or via ``stayawake show``.

Everything here runs on the main thread: button actions and the 1s refresh
NSTimer are all main-run-loop callbacks, same as the rumps timers.
"""

from __future__ import annotations

import time

import objc
from AppKit import (
    NSApp,
    NSAttributedString,
    NSBackingStoreBuffered,
    NSButton,
    NSButtonTypeMomentaryChange,
    NSColor,
    NSFloatingWindowLevel,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGradient,
    NSImage,
    NSImageScaleProportionallyUpOrDown,
    NSImageView,
    NSKernAttributeName,
    NSMakeRect,
    NSMutableParagraphStyle,
    NSParagraphStyleAttributeName,
    NSTextAlignmentCenter,
    NSTextField,
    NSView,
    NSWindow,
    NSWindowCollectionBehaviorMoveToActiveSpace,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskFullSizeContentView,
    NSWindowStyleMaskTitled,
    NSWindowTitleHidden,
)
from Foundation import NSObject, NSTimer

__all__ = ["ControlPanel", "install_reopen_handler"]

# Brand palette — matches scripts/make_app_icon.py: beige card, mocha primary,
# espresso type, caramel highlights.
def _rgb(r, g, b, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r / 255, g / 255, b / 255, a)


_TOP = _rgb(242, 234, 219)          # beige, light
_BOT = _rgb(226, 213, 190)          # beige, deep
_MOCHA = _rgb(111, 78, 55)          # primary fills & body text
_MOCHA_DIM = _rgb(111, 78, 55, 0.78)
_MOCHA_FAINT = _rgb(111, 78, 55, 0.55)
_ESPRESSO = _rgb(75, 54, 33)        # title type
_CARAMEL = _rgb(164, 117, 81)       # highlights / active state
_BEIGE_TEXT = _rgb(247, 240, 228)   # text on mocha/caramel fills
_PILL_BG = _rgb(111, 78, 55, 0.12)  # resting pill fill on beige

_W, _H = 340, 442  # window size


class _GradientView(NSView):
    """Content view: the warm vertical gradient behind everything."""

    def drawRect_(self, _rect):
        NSGradient.alloc().initWithStartingColor_endingColor_(_BOT, _TOP) \
            .drawInRect_angle_(self.bounds(), 90.0)


def _attr_title(text, font, color, kern=0.0):
    style = NSMutableParagraphStyle.alloc().init()
    style.setAlignment_(NSTextAlignmentCenter)
    attrs = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: color,
        NSParagraphStyleAttributeName: style,
    }
    if kern:
        attrs[NSKernAttributeName] = kern
    return NSAttributedString.alloc().initWithString_attributes_(text, attrs)


def _label(text, frame, font, color, kern=0.0):
    lbl = NSTextField.alloc().initWithFrame_(frame)
    lbl.setBezeled_(False)
    lbl.setDrawsBackground_(False)
    lbl.setEditable_(False)
    lbl.setSelectable_(False)
    lbl.setAttributedStringValue_(_attr_title(text, font, color, kern))
    return lbl


def _pill(title, frame, target, action, radius, font, fg, bg):
    btn = NSButton.alloc().initWithFrame_(frame)
    btn.setButtonType_(NSButtonTypeMomentaryChange)  # dims while pressed
    btn.setBordered_(False)
    btn.setWantsLayer_(True)
    btn.layer().setCornerRadius_(radius)
    btn.layer().setBackgroundColor_(bg.CGColor())
    btn.setAttributedTitle_(_attr_title(title, font, fg))
    btn.setTarget_(target)
    btn.setAction_(action)
    return btn


class ControlPanel(NSObject):
    """The floating Stay Awake window. Create once, ``show()`` any time."""

    def initWithStayAwake_iconPath_(self, stay_awake, icon_path):
        self = objc.super(ControlPanel, self).init()
        if self is None:
            return None
        self._sa = stay_awake
        self._icon_path = icon_path
        self._window = None
        self._timer = None
        return self

    # -- Public ---------------------------------------------------------------

    def show(self):
        if self._window is None:
            self._build()
        self._refresh()
        self._window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        if self._timer is None:
            self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0, self, "tick:", None, True
            )

    # -- Window construction ----------------------------------------------------

    def _build(self):
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
                | NSWindowStyleMaskFullSizeContentView)
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, _W, _H), mask, NSBackingStoreBuffered, False
        )
        win.setTitle_("Stay Awake")
        win.setTitlebarAppearsTransparent_(True)
        win.setTitleVisibility_(NSWindowTitleHidden)
        win.setMovableByWindowBackground_(True)
        win.setReleasedWhenClosed_(False)
        win.setLevel_(NSFloatingWindowLevel)
        win.setCollectionBehavior_(NSWindowCollectionBehaviorMoveToActiveSpace)
        win.setDelegate_(self)

        root = _GradientView.alloc().initWithFrame_(NSMakeRect(0, 0, _W, _H))
        win.setContentView_(root)

        # Groovy cup, floating at the top.
        icon = NSImageView.alloc().initWithFrame_(NSMakeRect((_W - 108) / 2, _H - 148, 108, 108))
        img = NSImage.alloc().initWithContentsOfFile_(self._icon_path)
        if img is not None:
            icon.setImage_(img)
        icon.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        root.addSubview_(icon)

        # Title.
        title_font = (NSFont.fontWithName_size_("AvenirNext-Bold", 27)
                      or NSFont.boldSystemFontOfSize_(27))
        root.addSubview_(_label("Stay Awake", NSMakeRect(0, _H - 196, _W, 42),
                                title_font, _ESPRESSO))

        # Live status line.
        self._status_label = _label("", NSMakeRect(10, _H - 222, _W - 20, 22),
                                    NSFont.systemFontOfSize_(13.5), _MOCHA_DIM)
        root.addSubview_(self._status_label)

        # Big toggle (mocha when off inviting Turn On; caramel while running).
        toggle_font = (NSFont.fontWithName_size_("AvenirNext-DemiBold", 18)
                       or NSFont.boldSystemFontOfSize_(18))
        self._toggle_btn = _pill("Turn On", NSMakeRect(20, _H - 296, _W - 40, 54),
                                 self, "toggleClicked:", 27, toggle_font,
                                 _BEIGE_TEXT, _MOCHA)
        root.addSubview_(self._toggle_btn)

        # "OR STAY AWAKE FOR" caption — caramel accent.
        cap_font = (NSFont.fontWithName_size_("AvenirNext-DemiBold", 11)
                    or NSFont.boldSystemFontOfSize_(11))
        root.addSubview_(_label("O R   S T A Y   A W A K E   F O R",
                                NSMakeRect(0, _H - 330, _W, 16),
                                cap_font, _CARAMEL, kern=1.0))

        # Preset pills.
        pill_font = (NSFont.fontWithName_size_("AvenirNext-DemiBold", 14)
                     or NSFont.boldSystemFontOfSize_(14))
        presets = [("15 min", 15 * 60), ("1 hour", 60 * 60), ("4 hours", 4 * 60 * 60)]
        x, w, gap = 20, (_W - 40 - 24) / 3, 12
        self._preset_btns = []
        for label, secs in presets:
            b = _pill(label, NSMakeRect(x, _H - 388, w, 42), self,
                      "presetClicked:", 21, pill_font, _MOCHA, _PILL_BG)
            b.setTag_(secs)
            root.addSubview_(b)
            self._preset_btns.append(b)
            x += w + gap

        # Footer hint.
        root.addSubview_(_label("Also lives in your menu bar — look for the cup",
                                NSMakeRect(0, 14, _W, 15),
                                NSFont.systemFontOfSize_(11), _MOCHA_FAINT))

        win.center()
        self._window = win

    # -- Actions ------------------------------------------------------------------

    def toggleClicked_(self, _sender):
        if self._sa.active:
            self._sa._stop()
        else:
            self._sa._start(None)
        self._refresh()

    def presetClicked_(self, sender):
        self._sa._start(int(sender.tag()))
        self._refresh()

    def tick_(self, _timer):
        if self._window is not None and self._window.isVisible():
            self._refresh()

    def windowWillClose_(self, _note):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None

    # -- State -> UI ---------------------------------------------------------------

    _PRESET_LABELS = {15 * 60: "15 min", 60 * 60: "1 hour", 4 * 60 * 60: "4 hours"}

    def _refresh(self):
        sa = self._sa
        toggle_font = (NSFont.fontWithName_size_("AvenirNext-DemiBold", 18)
                       or NSFont.boldSystemFontOfSize_(18))
        if sa.active:
            if sa._deadline is None:
                status = "●  On — staying awake until you turn it off"
            else:
                left = sa._fmt_remaining(sa._deadline - time.monotonic())
                status = f"●  On — sleeping again in {left}"
            self._toggle_btn.setAttributedTitle_(
                _attr_title("Turn Off", toggle_font, _BEIGE_TEXT))
            self._toggle_btn.layer().setBackgroundColor_(_CARAMEL.CGColor())
        else:
            status = "○  Off — your Mac can sleep normally"
            self._toggle_btn.setAttributedTitle_(
                _attr_title("Turn On", toggle_font, _BEIGE_TEXT))
            self._toggle_btn.layer().setBackgroundColor_(_MOCHA.CGColor())
        self._status_label.setAttributedStringValue_(
            _attr_title(status, NSFont.systemFontOfSize_(13.5), _MOCHA_DIM))
        # The running preset pill fills caramel; the rest rest quietly on beige.
        pill_font = (NSFont.fontWithName_size_("AvenirNext-DemiBold", 14)
                     or NSFont.boldSystemFontOfSize_(14))
        for b in self._preset_btns:
            on = sa.active and sa._active_seconds == b.tag()
            label = self._PRESET_LABELS.get(b.tag(), "")
            b.setAttributedTitle_(
                _attr_title(label, pill_font, _BEIGE_TEXT if on else _MOCHA))
            b.layer().setBackgroundColor_(
                (_CARAMEL if on else _PILL_BG).CGColor())


def install_reopen_handler(callback):
    """Show the panel when the already-running app is opened again.

    LaunchServices delivers a "reopen" event to the live process instead of
    starting a new one; rumps' internal NSApplicationDelegate doesn't handle it,
    so graft the handler onto that class. Best-effort: failure just means
    re-opening falls back to the control-file path.
    """
    try:
        from rumps.rumps import NSApp as _RumpsDelegate

        def applicationShouldHandleReopen_hasVisibleWindows_(self, _sender, _flag):
            callback()
            return True

        objc.classAddMethods(_RumpsDelegate,
                             [applicationShouldHandleReopen_hasVisibleWindows_])
        return True
    except Exception:
        return False
