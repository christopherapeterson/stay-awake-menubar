"""Stay Awake: a self-contained rumps menu component that keeps the Mac awake.

This module is a drop-in component for an existing ``rumps`` menu bar app. It owns
a single ``caffeinate`` subprocess and exposes a "Stay Awake" toggle plus a
"Stay awake for..." submenu of preset durations (15 minutes, 1 hour, 4 hours, and
"Until turned off").

Design notes
------------
* Exactly one ``caffeinate`` process is ever running. Toggling or picking a new
  duration tears down the previous one first, so assertions never stack up.
* Every ``caffeinate`` is launched with ``-w <our pid>``. macOS releases the
  assertion the instant our process exits, so caffeinate can never be left
  orphaned, even if we are SIGKILL'd. ``-t`` is added on top for timed sessions;
  caffeinate exits at whichever comes first (timeout, our kill, or our death).
* Process state is polled on the main thread via ``rumps.Timer`` (1s). When a
  timed session's ``-t`` expires, caffeinate exits on its own and the poll
  notices, auto-reverting the icon. No background threads touch the UI.

Usage
-----
    import rumps
    from stay_awake import StayAwake

    class App(rumps.App):
        def __init__(self):
            super().__init__("Dictation", title="\U0001F3A4")
            self.stay_awake = StayAwake(self)
            self.menu = [
                "Start Dictation",
                None,
                self.stay_awake.menu,   # installs the toggle + duration submenu
                None,
            ]

    if __name__ == "__main__":
        App().run()

Remember to also call ``stay_awake.shutdown()`` from your app's quit handler for
a tidy teardown. The ``-w`` guard makes this belt-and-suspenders rather than
strictly required, but it is good hygiene.
"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import weakref

import rumps

__all__ = ["StayAwake"]

# Title shown in the menu bar while a session is active. Override via the
# ``active_title`` constructor argument if your app prefers a different glyph.
ACTIVE_TITLE = "☕"  # ☕ coffee cup

# Preset durations offered in the submenu, in order. ``None`` means indefinite
# ("Until turned off"), i.e. no ``-t`` flag.
PRESETS = [
    ("15 minutes", 15 * 60),
    ("1 hour", 60 * 60),
    ("4 hours", 4 * 60 * 60),
    ("Until turned off", None),
]

# Every live StayAwake instance, so the module-level atexit/signal hooks can kill
# any caffeinate child even if the host app forgets to call shutdown().
_INSTANCES: "weakref.WeakSet[StayAwake]" = weakref.WeakSet()


class StayAwake:
    """Owns the Stay Awake menu items and the backing ``caffeinate`` process.

    Parameters
    ----------
    app:
        The ``rumps.App`` instance. Used to read/restore its menu bar title.
    active_title:
        Title to display in the menu bar while keeping the Mac awake. Defaults
        to a coffee-cup glyph. When the session ends the app's previous title is
        restored.
    """

    def __init__(self, app: rumps.App, active_title: str = ACTIVE_TITLE):
        self._app = app
        self._active_title = active_title
        self._idle_title = app.title  # remembered so we can revert on stop
        self._proc: subprocess.Popen | None = None
        self._active_seconds: int | None = None  # None => indefinite

        # Top-level toggle: click to keep awake indefinitely / turn off.
        self._toggle = rumps.MenuItem("Stay Awake", callback=self._on_toggle)

        # Submenu of preset durations. Each item is a radio-style choice.
        self._duration_menu = rumps.MenuItem("Stay awake for...")
        self._duration_items: dict[str, rumps.MenuItem] = {}
        for label, seconds in PRESETS:
            item = rumps.MenuItem(
                label,
                callback=lambda sender, s=seconds: self._start(s),
            )
            self._duration_items[label] = item
            self._duration_menu.add(item)

        # Polls caffeinate's liveness on the main thread; only runs while active.
        self._timer = rumps.Timer(self._poll, 1)

        _INSTANCES.add(self)

    # -- Public API ---------------------------------------------------------

    @property
    def menu(self):
        """A list suitable for splicing into the host app's ``self.menu``.

        Splice with ``*stay_awake.menu`` or just reference ``stay_awake.menu``
        as a nested iterable; rumps accepts either.
        """
        return [self._toggle, self._duration_menu]

    @property
    def active(self) -> bool:
        """True while a caffeinate session is running."""
        return self._proc is not None and self._proc.poll() is None

    def shutdown(self):
        """Stop any session and stop polling. Safe to call from a quit handler."""
        self._stop()

    # -- Menu callbacks -----------------------------------------------------

    def _on_toggle(self, _sender):
        if self.active:
            self._stop()
        else:
            self._start(None)  # plain toggle => indefinite

    def _start(self, seconds: int | None):
        """(Re)start caffeinate for ``seconds`` (None => indefinite)."""
        # Always tear down any existing session first so assertions never stack.
        self._kill_proc()

        cmd = ["/usr/bin/caffeinate", "-d", "-i"]
        if seconds is not None:
            cmd += ["-t", str(seconds)]
        # OS-level orphan guard: caffeinate dies the moment we do.
        cmd += ["-w", str(os.getpid())]

        self._proc = subprocess.Popen(cmd)
        self._active_seconds = seconds
        self._apply_active_ui()
        self._timer.start()

    def _stop(self):
        """End the current session and revert to the idle state."""
        self._kill_proc()
        self._active_seconds = None
        if self._timer.is_alive():
            self._timer.stop()
        self._apply_idle_ui()

    # -- Process management -------------------------------------------------

    def _kill_proc(self):
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        except Exception:
            # Best effort: the -w guard guarantees the OS reaps it on our exit.
            pass

    def _poll(self, _timer):
        """Main-thread tick: detect a timed session that expired on its own."""
        if self._proc is not None and self._proc.poll() is not None:
            # caffeinate exited (its -t timeout elapsed) -> auto-revert.
            self._stop()

    # -- UI -----------------------------------------------------------------

    def _apply_active_ui(self):
        self._app.title = self._active_title
        self._toggle.state = 1  # checkmark on the toggle
        self._toggle.title = "Stay Awake (on)"
        for label, item in self._duration_items.items():
            # Tick the preset that matches the running session.
            seconds = dict(PRESETS)[label]
            item.state = 1 if seconds == self._active_seconds else 0

    def _apply_idle_ui(self):
        self._app.title = self._idle_title
        self._toggle.state = 0
        self._toggle.title = "Stay Awake"
        for item in self._duration_items.values():
            item.state = 0


# -- Module-level safety net: never leave caffeinate orphaned ---------------

def _kill_all_instances(*_args):
    for inst in list(_INSTANCES):
        inst._kill_proc()


atexit.register(_kill_all_instances)

# Chain SIGTERM/SIGINT so a `kill` or Ctrl-C also tears caffeinate down. SIGKILL
# can't be caught, but the per-process `-w <pid>` guard covers that case too.
for _sig in (signal.SIGTERM, signal.SIGINT):
    try:
        _prev = signal.getsignal(_sig)

        def _handler(signum, frame, _prev=_prev):
            _kill_all_instances()
            if callable(_prev) and _prev not in (signal.SIG_DFL, signal.SIG_IGN):
                _prev(signum, frame)
            else:
                # Restore default and re-raise so normal termination proceeds.
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)

        signal.signal(_sig, _handler)
    except (ValueError, OSError):
        # Not on the main thread / unsupported: atexit + -w still protect us.
        pass
