"""Menu bar app: Dictation tool + Stay Awake.

This is the host ``rumps`` app. The dictation item here is a minimal stand-in for
your real dictation tool; the point of this file is to show how ``stay_awake``
plugs in alongside it without touching the dictation code.
"""

import fcntl
import os
import sys
import tempfile

import rumps

from control_panel import ControlPanel, install_reopen_handler
from stay_awake import StayAwake

# Single-instance lock: a second launch (e.g. double-clicking the app again)
# should not add a duplicate menu bar cup. We hold an exclusive flock for the
# life of the process; if it's already held, another copy is running.
_LOCK_PATH = os.path.join(tempfile.gettempdir(), "stay-awake-menubar.lock")
_lock_fd = None  # kept open for the process lifetime to retain the lock

# Control channel so a hotkey/CLI can toggle the running app without the menu
# bar (see `stayawake` in bin/). Lives in Application Support so it survives.
_SUPPORT_DIR = os.path.expanduser("~/Library/Application Support/StayAwake")
CONTROL_FILE = os.path.join(_SUPPORT_DIR, "command")
STATUS_FILE = os.path.join(_SUPPORT_DIR, "status")

_COMMANDS = ("toggle", "on", "off", "15m", "1h", "4h", "status", "show")


def _acquire_single_instance() -> bool:
    global _lock_fd
    _lock_fd = open(_LOCK_PATH, "w")
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False

# Groovy menu bar icons (template images). Regenerate with scripts/make_icons.py.
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources")
IDLE_ICON = os.path.join(RES, "stay-awake-idle.png")     # resting cup
ACTIVE_ICON = os.path.join(RES, "stay-awake-active.png")  # steaming cup


class MenuBarApp(rumps.App):
    def __init__(self):
        super().__init__("Dictation", icon=IDLE_ICON, template=True,
                         quit_button=None)

        # Stay Awake is fully self-contained: it builds its own menu items and
        # manages its own caffeinate subprocess. We hand it the app plus the two
        # groovy icons to swap between resting and awake states.
        self.stay_awake = StayAwake(
            self, idle_icon=IDLE_ICON, active_icon=ACTIVE_ICON,
            control_file=CONTROL_FILE, status_file=STATUS_FILE,
        )

        # The pretty control panel. Opens on launch, on re-opening the app, on
        # clicking the menu's status line, and via `stayawake show`.
        self.panel = ControlPanel.alloc().initWithStayAwake_iconPath_(
            self.stay_awake, os.path.join(RES, "app-icon.png")
        )
        self.stay_awake.on_show = self.panel.show
        install_reopen_handler(self.panel.show)

        # Pop the panel once the run loop is going (can't order windows before).
        self._welcome = rumps.Timer(self._show_panel_on_launch, 0.4)
        self._welcome.start()

        self.menu = [
            rumps.MenuItem("Start Dictation", callback=self.start_dictation),
            None,                       # separator
            *self.stay_awake.menu,      # "Stay Awake" toggle + duration submenu
            None,                       # separator
            rumps.MenuItem("Quit", callback=self.quit),
        ]

    def _show_panel_on_launch(self, _timer):
        self._welcome.stop()
        self.panel.show()

    # -- Dictation (stand-in for the existing tool) -------------------------

    def start_dictation(self, _sender):
        rumps.notification("Dictation", "", "Listening...")

    # -- Quit ---------------------------------------------------------------

    def quit(self, _sender):
        # Tear down caffeinate cleanly before exiting.
        self.stay_awake.shutdown()
        rumps.quit_application()


def _send_command(cmd: str) -> int:
    """CLI path: hand a command to the running app (or report status) and exit.

    Used by bin/stayawake so a hotkey can toggle without touching the menu bar.
    """
    os.makedirs(_SUPPORT_DIR, exist_ok=True)
    if cmd == "status":
        try:
            with open(STATUS_FILE) as fh:
                print(fh.read().strip() or "unknown")
        except FileNotFoundError:
            print("Stay Awake is not running.")
        return 0
    with open(CONTROL_FILE, "w") as fh:
        fh.write(cmd)
    print(f"sent: {cmd}")
    return 0


def main_entry():
    """Entry point. With no args, runs the app; with a command, drives it.

    Commands: toggle | on | off | 15m | 1h | 4h | status
    """
    args = sys.argv[1:]
    if args:
        cmd = args[0].lower()
        if cmd in _COMMANDS:
            sys.exit(_send_command(cmd))
        print(f"unknown command: {cmd}\nusage: stayawake [{' | '.join(_COMMANDS)}]")
        sys.exit(2)

    if not _acquire_single_instance():
        # Already running: don't stack a second cup — pop the existing
        # instance's control panel instead, so "opening the app" always
        # gives the user something visible.
        _send_command("show")
        print("Stay Awake is already running — opened its panel.")
        return
    os.makedirs(_SUPPORT_DIR, exist_ok=True)  # so status is readable immediately
    MenuBarApp().run()


if __name__ == "__main__":
    main_entry()
