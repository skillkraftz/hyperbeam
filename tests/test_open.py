"""Open: attaches to a running session; otherwise starts it and Claude continues its last conversation. No question about how Claude starts.
Runs in the lab: hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path

from common import hb


class Open(unittest.TestCase):
    NAMES = ("ensure_link", "load_layout", "start_check", "start_session", "session_exists")

    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in self.NAMES}
        self.addCleanup(lambda: [setattr(hb, k, v) for k, v in self.saved.items()])
        self.proj = Path(tempfile.mkdtemp())
        hb.ensure_link = lambda *a: None
        hb.load_layout = lambda n: None
        hb.start_check = lambda n, p: ([], [])
        self.started = []
        hb.start_session = lambda *a, **k: self.started.append(k)
        self.running = False
        hb.session_exists = lambda s: self.running

    def test_stopped_project_starts_without_asking(self):
        hb.open_project("proj", self.proj, {"port": 1}, lambda t: self.fail("asked"), lambda m: None)
        self.assertEqual(len(self.started), 1)
        self.assertNotIn("begin", self.started[0])

    def test_running_project_is_only_attached(self):
        self.running = True
        hb.open_project("proj", self.proj, {"port": 1}, lambda t: self.fail("asked"), lambda m: None)
        self.assertEqual(self.started, [])


if __name__ == "__main__":
    unittest.main()
