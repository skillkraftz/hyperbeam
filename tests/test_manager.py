"""The manager: the first row, a Claude for talking about every project. It starts in ~/manager with the manager model, never in plan mode, never without
permission prompts; its notes folder is made from the template in manager/ and never overwritten; the template denies edits under ~/projects.
Runs in the lab: hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from common import HERE, hb


class ManagerCommand(unittest.TestCase):
    def setUp(self):
        self.saved = hb.cfg_get
        hb.cfg_get = lambda k: {"manager_model": "opus", "claude_effort": "medium", "claude_model": "opusplan", "claude_permissions": "skip"}[k]

    def tearDown(self):
        hb.cfg_get = self.saved

    def test_not_plan_mode_not_skipping_permissions_sees_the_projects(self):
        for cont in (False, True):
            cmd = hb.manager_cmd(cont=cont)
            self.assertIn("--model opus ", cmd)
            self.assertNotIn("plan", cmd)
            self.assertNotIn("skip", cmd)
            self.assertIn(f"--add-dir {hb.ROOT}", cmd)
        self.assertIn("--continue", hb.manager_cmd(cont=True))
        self.assertNotIn("--continue", hb.manager_cmd())

    def test_the_menu_session_is_the_manager_and_hyperbeam_is_a_project(self):
        self.assertEqual(hb.MENU, "manager")
        self.assertEqual(hb.DEV, "hyperbeam")
        self.assertNotEqual(hb.sanitize(hb.DEV), hb.MENU)


class ManagerNotes(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = hb.MANAGER_DIR
        hb.MANAGER_DIR = self.tmp / "manager"

    def tearDown(self):
        hb.MANAGER_DIR = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_made_from_the_template_as_a_git_repo_and_never_overwritten(self):
        d = hb.ensure_manager_dir()
        for f in ("CLAUDE.md", "now.md", "hyperbeam.md", ".claude/settings.json", "projects", "outbox", "inbox"):
            self.assertTrue((d / f).exists(), f)
        self.assertEqual(subprocess.run(["git", "-C", str(d), "log", "--oneline"], capture_output=True, text=True).stdout.count("\n"), 1)
        (d / "now.md").write_text("my notes\n")
        hb.ensure_manager_dir()
        self.assertEqual((d / "now.md").read_text(), "my notes\n")

    def test_the_template_denies_edits_under_the_projects(self):
        deny = json.loads((HERE / "manager" / ".claude" / "settings.json").read_text())["permissions"]["deny"]
        for tool in ("Edit", "Write"):
            self.assertIn(f"{tool}(~/projects/**)", deny)


if __name__ == "__main__":
    unittest.main()
