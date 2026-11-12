"""The sidebar's core behaviour: stopping a project moves the clients looking at it to the manager session first, and the hyperbeam row is always on top.
Runs in the lab: hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path

from common import hb


class StopMovesClients(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in ("tmux", "session_exists", "save_layout", "clear_status", "own_session", "project_ports", "sidebar_read", "manifest_path")}
        self.calls = []

        def tmux(*a, check=True, **k):
            self.calls.append(a)
            out = "/dev/pts/7 proj\n/dev/pts/8 other\n/dev/pts/9 hyperbeam\n" if a[0] == "list-clients" else ""
            return type("R", (), {"stdout": out, "returncode": 0})()
        hb.tmux = tmux
        hb.session_exists = lambda s: True
        hb.save_layout = lambda *a, **k: None
        hb.clear_status = lambda *a: None
        hb.own_session = lambda: "somewhere"
        hb.project_ports = lambda man: []
        hb.sidebar_read = lambda: {"tty": "/dev/pts/7"}

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def test_the_sidebars_client_goes_home_before_the_session_is_killed(self):
        hb.stop_project("proj", None, say=lambda *a: None)
        verbs = [c[0] for c in self.calls]
        self.assertIn(("switch-client", "-c", "/dev/pts/7", "-t", "=manager:home"), self.calls)
        self.assertEqual(sum(1 for c in self.calls if c[0] == "switch-client"), 1)     # only the client that was on proj
        self.assertLess(verbs.index("switch-client"), verbs.index("kill-session"))


class Order(unittest.TestCase):
    def test_the_manager_is_first_even_when_others_are_running_or_sort_before_it(self):
        stub = type("S", (), {"projects": [dict(name=n, running=r, opened=0) for n, r in (("alpha", True), ("manager", False), ("zeta", True), ("hyperbeam", True))]})()
        names = [p["name"] for p in hb.Menu.ordered(stub)]
        self.assertEqual(names, ["manager", "alpha", "hyperbeam", "zeta"])


if __name__ == "__main__":
    unittest.main()
