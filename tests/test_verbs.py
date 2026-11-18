"""The Test button (output through `say`, ok / FAILED), Merge's update (compares against the commit before the merge), the kk link."""
import os
import tempfile
import types
import unittest
from pathlib import Path

from common import Repo, hb


class TestVerb(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in ("lab_ready", "cmd_lab", "verb_command", "DATA_DIR")}
        self.addCleanup(lambda: [setattr(hb, k, v) for k, v in self.saved.items()])
        hb.DATA_DIR = Path(tempfile.mkdtemp())
        hb.verb_command = lambda n, p, v: ("make check", "Makefile")
        hb.lab_ready = lambda: ""
        self.proj = Path(tempfile.mkdtemp())

    def run_test(self, rc):
        def fake_lab(ns):
            self.ns = ns
            ns.say("line one")                      # the lab's output goes through the callback, never to stdout
            return rc
        hb.cmd_lab = fake_lab
        lines = []
        return hb.run_verb("proj", "test", self.proj, lines.append), lines

    def test_ok(self):
        rc, lines = self.run_test(0)
        self.assertEqual(rc, 0)
        self.assertIn("line one", lines)
        self.assertTrue(lines[-1].startswith("test ok") and "verb-test.txt" in lines[-1], lines)
        self.assertEqual(self.ns.cmd, ["--", "make check"])

    def test_failed_says_where_the_output_is(self):
        rc, lines = self.run_test(1)
        self.assertEqual(rc, 1)
        self.assertTrue(lines[-1].startswith("test FAILED (exit 1)") and "verb-test.txt" in lines[-1], lines)

    def test_lab_not_ready_is_said_not_printed(self):
        hb.lab_ready = lambda: "lab is not set up"
        hb.cmd_lab = lambda ns: self.fail("ran")
        lines = []
        self.assertEqual(hb.run_verb("proj", "test", self.proj, lines.append), 2)
        self.assertEqual(lines, ["lab is not set up"])


class UpdateBase(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in ("restart_services", "verb_command", "run_cmd_stream", "load_manifests", "DATA_DIR")}
        self.addCleanup(lambda: [setattr(hb, k, v) for k, v in self.saved.items()])
        hb.DATA_DIR = Path(tempfile.mkdtemp())
        self.repo = Repo()
        self.repo.write("uv.lock", "1\n")
        self.repo.commit("lock")
        self.repo.git("push", "-q", "origin", "main")
        self.restarts, self.installs = [], []
        hb.restart_services = lambda n, say: (self.restarts.append(n), 1)[1]
        hb.verb_command = lambda n, p, v: ("uv sync", "default")
        hb.run_cmd_stream = lambda cmd, cwd, say: (self.installs.append(cmd), 0)[1]

    def merge_then_update(self, files):
        before = self.repo.git("rev-parse", "main")
        self.repo.merge_pr(5, files)
        self.repo.git("reset", "-q", "--hard", before)          # the checkout has not pulled yet
        self.repo.git("pull", "-q", "--ff-only")               # what merge_pr (Merge) does
        lines = []
        rc = hb.verb_update("proj", self.repo.r, lines.append, since=before)
        return rc, lines


class UpdateSince(UpdateBase):
    """verb_update after something else (Merge) already pulled."""

    def test_lockfile_changed_installs_and_restarts(self):
        rc, lines = self.merge_then_update(["uv.lock"])
        self.assertEqual((rc, self.installs, self.restarts), (0, ["uv sync"], ["proj"]))
        self.assertTrue(any("->" in l for l in lines), lines)

    def test_other_files_restart_without_install(self):
        rc, lines = self.merge_then_update(["app.py"])
        self.assertEqual((rc, self.installs, self.restarts), (0, [], ["proj"]))
        self.assertIn("no lockfile changed: nothing to install", lines)

    def test_nothing_changed_restarts_nothing(self):
        lines = []
        head = self.repo.git("rev-parse", "main")
        self.assertEqual(hb.verb_update("proj", self.repo.r, lines.append, since=head), 0)
        self.assertEqual((self.installs, self.restarts), ([], []))
        self.assertTrue(any("nothing changed" in l for l in lines), lines)


class UpdateOwn(UpdateBase):
    """The project's own update verb."""

    def setUp(self):
        super().setUp()
        self.own = "make update"
        hb.verb_command = lambda n, p, v: ((self.own, "Makefile target update") if v == "update" and self.own else ("uv sync", "default"))

    def update(self, since=None):
        lines = []
        return hb.verb_update("proj", self.repo.r, lines.append, since=since), lines

    def test_code_only_change_runs_own_update(self):
        rc, lines = self.merge_then_update(["app.py"])
        self.assertEqual((rc, self.installs, self.restarts), (0, ["make update"], ["proj"]))

    def test_manual_pull_still_runs_it_once(self):
        self.update()                                          # records the commit
        self.installs.clear()
        self.repo.merge_pr(6, ["app.py"])
        self.repo.git("pull", "-q", "--ff-only")               # someone pulled first
        rc, lines = self.update()
        self.assertEqual((rc, self.installs), (0, ["make update"]))
        self.installs.clear()
        self.assertEqual(self.update()[0], 0)
        self.assertEqual(self.installs, [])                    # nothing changed since the record

    def test_no_own_update_keeps_old_behaviour(self):
        self.own = None
        rc, lines = self.merge_then_update(["app.py"])
        self.assertEqual(self.installs, [])
        self.assertIn("no lockfile changed: nothing to install", lines)

    def test_failing_own_update(self):
        hb.run_cmd_stream = lambda cmd, cwd, say: 3
        rc, lines = self.merge_then_update(["app.py"])
        self.assertEqual(rc, 1)
        self.assertTrue(any("own update failed" in l for l in lines), lines)
        self.assertEqual(self.restarts, [])


class KkLink(unittest.TestCase):
    def setUp(self):
        self.bin = Path(tempfile.mkdtemp())
        self.old_env = os.environ.get("HB_BIN")
        os.environ["HB_BIN"] = str(self.bin)
        self.addCleanup(lambda: os.environ.__setitem__("HB_BIN", self.old_env) if self.old_env else os.environ.pop("HB_BIN", None))
        self.target = str(hb.HERE / "hyperbeam")

    def test_old_link_to_the_dev_folder_is_fixed(self):
        (self.bin / "kk").symlink_to("/home/x/projects/hyperbeam/hyperbeam")
        self.assertIn("linked", hb.link_kk())
        self.assertEqual(os.readlink(self.bin / "kk"), self.target)

    def test_missing_is_made_and_current_is_left(self):
        self.assertIn("linked", hb.link_kk())
        self.assertEqual(hb.link_kk(), "")

    def test_a_real_file_is_left_alone(self):
        (self.bin / "kk").write_text("mine")
        self.assertIn("left alone", hb.link_kk())
        self.assertEqual((self.bin / "kk").read_text(), "mine")


if __name__ == "__main__":
    unittest.main()
