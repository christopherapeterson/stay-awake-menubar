"""Menu bar app: Dictation tool + Stay Awake.

This is the host ``rumps`` app. The dictation item here is a minimal stand-in for
your real dictation tool; the point of this file is to show how ``stay_awake``
plugs in alongside it without touching the dictation code.
"""

import os

import rumps

from stay_awake import StayAwake

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
    MenuBarApp().run()


if __name__ == "__main__":
    main_entry()
