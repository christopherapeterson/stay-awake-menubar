"""Headless lifecycle test for StayAwake (no GUI run loop needed).

Uses a tiny stub in place of rumps.App (StayAwake only needs ``.title``), then
drives the controller directly and inspects the real caffeinate subprocess.
"""

import os
import subprocess
import time

from stay_awake import StayAwake


class StubApp:
    def __init__(self):
        self.title = "🎤"


def running_caffeinate_pids():
    out = subprocess.run(["pgrep", "-x", "caffeinate"], capture_output=True, text=True)
    return set(out.stdout.split())


def assert_(cond, msg):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("ok -", msg)


def caffeinate_cmd(pid):
    return subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                          capture_output=True, text=True).stdout.strip()


def main():
    app = StubApp()
    sa = StayAwake(app)

    # --- indefinite toggle on ---
    before = running_caffeinate_pids()
    sa._on_toggle(None)
    time.sleep(0.5)
    assert_(sa.active, "indefinite toggle reports active")
    assert_(app.title == "☕", "menu bar title switched to active glyph")
    assert_(sa._toggle.state == 1, "toggle shows checkmark")
    new = running_caffeinate_pids() - before
    assert_(len(new) >= 1, "a caffeinate process is running")
    cmd = caffeinate_cmd(sa._proc.pid)
    assert_("-w" in cmd and str(os.getpid()) in cmd, "caffeinate has -w <our pid> orphan guard")
    assert_("-t" not in cmd, "indefinite session has no -t flag")

    # --- toggle off ---
    sa._on_toggle(None)
    time.sleep(0.5)
    assert_(not sa.active, "toggle off reports inactive")
    assert_(app.title == "🎤", "menu bar title reverted")
    assert_(sa._toggle.state == 0, "toggle checkmark cleared")

    # --- timed session via preset, -t present, auto-revert on expiry ---
    sa._start(2)  # 2 second timed session
    time.sleep(0.5)
    assert_(sa.active, "timed session active")
    cmd = caffeinate_cmd(sa._proc.pid)
    assert_("-t" in cmd and " 2" in (" " + cmd), "timed session passes -t 2")
    assert_("-w" in cmd, "timed session also has -w orphan guard")
    proc = sa._proc
    # Wait past the -t timeout; caffeinate should exit on its own.
    time.sleep(2.5)
    assert_(proc.poll() is not None, "caffeinate exited on its own at -t timeout")
    sa._poll(None)  # simulate the main-thread timer tick
    assert_(not sa.active, "session auto-reverted after expiry")
    assert_(app.title == "🎤", "title reverted after timed expiry")

    # --- switching duration replaces (never stacks) the process ---
    sa._start(None)
    p1 = sa._proc.pid
    sa._start(900)
    time.sleep(0.3)
    p2 = sa._proc.pid
    assert_(p1 != p2, "selecting a new duration replaced the process")
    assert_(not _pid_alive(p1), "previous caffeinate was killed (no stacking)")

    # --- shutdown cleans up ---
    sa.shutdown()
    time.sleep(0.3)
    assert_(not sa.active, "shutdown stopped the session")
    assert_(not _pid_alive(p2), "shutdown killed caffeinate")

    print("\nALL CHECKS PASSED")


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


if __name__ == "__main__":
    main()
