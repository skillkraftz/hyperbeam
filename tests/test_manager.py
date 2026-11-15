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
        for f in ("now.md", "hyperbeam.md", ".claude/settings.json", "projects", "outbox", "inbox"):
            self.assertTrue((d / f).exists(), f)
        self.assertEqual(subprocess.run(["git", "-C", str(d), "log", "--oneline"], capture_output=True, text=True).stdout.count("\n"), 1)
        (d / "now.md").write_text("my notes\n")
        hb.ensure_manager_dir()
        self.assertEqual((d / "now.md").read_text(), "my notes\n")

    def test_the_role_is_not_copied_and_an_old_full_copy_is_removed_notes_untouched(self):
        d = hb.MANAGER_DIR
        d.mkdir(parents=True)
        (d / "CLAUDE.md").write_bytes((HERE / "manager" / "CLAUDE.md").read_bytes())
        (d / "now.md").write_text("my notes\n")
        (d / "projects").mkdir()
        (d / "projects" / "x.md").write_text("x notes\n")
        hb.ensure_manager_dir()
        self.assertFalse((d / "CLAUDE.md").exists())
        self.assertEqual((d / "now.md").read_text(), "my notes\n")
        self.assertEqual((d / "projects" / "x.md").read_text(), "x notes\n")
        (d / "CLAUDE.md").write_text("# my own rules\n")
        hb.ensure_manager_dir()
        self.assertEqual((d / "CLAUDE.md").read_text(), "# my own rules\n")

    def test_a_changed_role_reaches_a_manager_started_afterwards(self):
        """The manager's command points at the running hyperbeam's manager/CLAUDE.md; claude reads it at each start, so editing it is enough."""
        saved, saved_cfg = hb.HERE, hb.cfg_get
        try:
            hb.HERE = self.tmp / "installed"
            (hb.HERE / "manager").mkdir(parents=True)
            (hb.HERE / "manager" / "CLAUDE.md").write_text("role v1\n")
            hb.cfg_get = lambda k: {"manager_model": "opus", "claude_effort": "medium"}[k]
            before = hb.manager_cmd()
            self.assertIn(f"--append-system-prompt-file {hb.HERE}/manager/CLAUDE.md", before)
            (hb.HERE / "manager" / "CLAUDE.md").write_text("role v2\n")
            self.assertEqual(hb.manager_cmd(), before)  # same command, new text read at start
            hb.ensure_manager_dir()
            self.assertFalse((hb.MANAGER_DIR / "CLAUDE.md").exists())
        finally:
            hb.HERE, hb.cfg_get = saved, saved_cfg

    def test_the_template_denies_edits_under_the_projects(self):
        deny = json.loads((HERE / "manager" / ".claude" / "settings.json").read_text())["permissions"]["deny"]
        for tool in ("Edit", "Write"):
            self.assertIn(f"{tool}(~/projects/**)", deny)


if __name__ == "__main__":
    unittest.main()
