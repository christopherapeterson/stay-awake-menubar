"""Menu bar app: Dictation tool + Stay Awake.

This is the host ``rumps`` app. The dictation item here is a minimal stand-in for
your real dictation tool; the point of this file is to show how ``stay_awake``
plugs in alongside it without touching the dictation code.
"""

import fcntl
import os
import tempfile

import rumps

from stay_awake import StayAwake

# Single-instance lock: a second launch (e.g. double-clicking the app again)
# should not add a duplicate menu bar cup. We hold an exclusive flock for the
# life of the process; if it's already held, another copy is running.
_LOCK_PATH = os.path.join(tempfile.gettempdir(), "stay-awake-menubar.lock")
_lock_fd = None  # kept open for the process lifetime to retain the lock


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
            self, idle_icon=IDLE_ICON, active_icon=ACTIVE_ICON
        )

        self.menu = [
            rumps.MenuItem("Start Dictation", callback=self.start_dictation),
            None,                       # separator
            *self.stay_awake.menu,      # "Stay Awake" toggle + duration submenu
            None,                       # separator
            rumps.MenuItem("Quit", callback=self.quit),
        ]

    # -- Dictation (stand-in for the existing tool) -------------------------

    def start_dictation(self, _sender):
        rumps.notification("Dictation", "", "Listening...")

    # -- Quit ---------------------------------------------------------------

    def quit(self, _sender):
        # Tear down caffeinate cleanly before exiting.
        self.stay_awake.shutdown()
        rumps.quit_application()


def main_entry():
    """Console-script entry point (see ``[project.scripts]`` in pyproject.toml)."""
    if not _acquire_single_instance():
        # Already running; quietly bow out so we don't stack menu bar icons.
        print("Stay Awake is already running.")
        return
    MenuBarApp().run()


if __name__ == "__main__":
    main_entry()
