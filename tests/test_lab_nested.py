"""Inside the lab (HB_LAB=1, set for everything a lab run starts) every command that needs the lab refuses at once with the lab's own message: it says what
happened, that nothing needs changing, and what to do. The guard no longer guesses this from the command's text (decision lab-refuses-nesting).
Runs in the lab: hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import contextlib
import io
import os
import types
import unittest

from common import hb


class LabRefusesNesting(unittest.TestCase):
    def setUp(self):
        os.environ["HB_LAB"] = "1"

    def tearDown(self):
        del os.environ["HB_LAB"]

    def refused(self, fn, *a):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = fn(*a)
        self.assertEqual(rc, 2, out.getvalue())
        self.assertEqual(out.getvalue().strip(), hb.LAB_NESTED)
        return out.getvalue()

    def test_the_message_is_complete(self):
        m = hb.LAB_NESTED
        for part in ("you are already in it", "nothing on the machine needs changing", "run the program directly"):
            self.assertIn(part, m)
        self.assertNotIn("setup.sh", m)

    def test_lab_run_status_stop_reset(self):
        for action in ("run", "status", "stop", "reset"):
            self.refused(hb.cmd_lab, types.SimpleNamespace(action=action, cmd=["--", "true"], dir=None, name=None, why="x", fresh=False, timeout=5,
                                                           collect=None, collect_to=None, quiet=False, project=None, force=False, all=False))

    def test_tool_and_tool_tests(self):
        for kw in (dict(list=False, test=False, name="x", args=[], dir=None, timeout=5), dict(list=False, test=True, name=None, args=[], dir=None, timeout=5)):
            self.refused(hb.cmd_tool, types.SimpleNamespace(**kw))

    def test_tool_list_still_works(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = hb.cmd_tool(types.SimpleNamespace(list=True, test=False, name=None, args=[], dir=None, timeout=5))
        self.assertEqual(rc, 0)

    def test_shot(self):
        self.refused(hb.cmd_shot, types.SimpleNamespace(screen=None, phone=False, cols=35, rows=40, dir=None))


class ShotDir(unittest.TestCase):
    """`hyperbeam shot --dir DIR` draws that checkout (to see a branch); without it the installed copy."""

    def run_shot(self, **kw):
        seen, old = [], hb.cmd_lab
        hb.cmd_lab = lambda ns: (seen.append(ns), 0)[1]
        try:
            hb.cmd_shot(types.SimpleNamespace(screen="project", phone=False, cols=35, rows=40, **kw))
        finally:
            hb.cmd_lab = old
        return seen[0]

    def test_default_is_the_installed_copy(self):
        self.assertEqual(self.run_shot(dir=None).dir, str(hb.HERE))

    def test_dir_is_used_and_expanded(self):
        self.assertEqual(self.run_shot(dir="~/projects/hyperbeam").dir, os.path.expanduser("~/projects/hyperbeam"))


if __name__ == "__main__":
    unittest.main()
