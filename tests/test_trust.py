"""Pre-trusting a project's folder in Claude's config (trust_folder), so a first session or worker does not stop at the trust dialog. Runs in the lab."""
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from common import hb


class Trust(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.f = self.d / ".claude.json"
        self.proj = self.d / "proj"
        self.proj.mkdir()
        p = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.d)})
        p.start()
        self.addCleanup(p.stop)

    def read(self):
        return json.loads(self.f.read_text())

    def test_a_missing_entry_is_added_and_other_keys_and_the_mode_are_kept(self):
        self.f.write_text(json.dumps({"numStartups": 7, "projects": {"/x": {"hasTrustDialogAccepted": False, "allowedTools": ["a"]}}}))
        os.chmod(self.f, 0o600)
        self.assertTrue(hb.trust_folder(self.proj))
        d = self.read()
        self.assertIs(d["projects"][str(self.proj.resolve())]["hasTrustDialogAccepted"], True)
        self.assertEqual(d["numStartups"], 7)
        self.assertEqual(d["projects"]["/x"], {"hasTrustDialogAccepted": False, "allowedTools": ["a"]})
        self.assertEqual(self.f.stat().st_mode & 0o777, 0o600)
        self.assertEqual([p.name for p in self.d.iterdir() if p.name.startswith(".claude.json.")], [])

    def test_an_existing_entry_keeps_its_other_fields(self):
        key = str(self.proj.resolve())
        self.f.write_text(json.dumps({"projects": {key: {"hasTrustDialogAccepted": False, "lastCost": 1}}}))
        hb.trust_folder(self.proj)
        self.assertEqual(self.read()["projects"][key], {"hasTrustDialogAccepted": True, "lastCost": 1})

    def test_already_true_is_not_rewritten(self):
        self.f.write_text(json.dumps({"projects": {str(self.proj.resolve()): {"hasTrustDialogAccepted": True}}}))
        os.utime(self.f, (1, 1))
        before = self.f.stat()
        self.assertFalse(hb.trust_folder(self.proj))
        after = self.f.stat()
        self.assertEqual((before.st_mtime_ns, before.st_ino), (after.st_mtime_ns, after.st_ino))

    def test_a_missing_or_unreadable_file_is_skipped_quietly(self):
        self.assertFalse(hb.trust_folder(self.proj))
        self.assertFalse(self.f.exists())
        self.f.write_text("{not json")
        self.assertFalse(hb.trust_folder(self.proj))
        self.assertEqual(self.f.read_text(), "{not json")

    def test_a_symlinked_config_stays_a_symlink(self):
        real = self.d / "dotfiles" / "claude.json"
        real.parent.mkdir()
        real.write_text(json.dumps({"projects": {}}))
        self.f.symlink_to(real)
        self.assertTrue(hb.trust_folder(self.proj))
        self.assertTrue(self.f.is_symlink())
        self.assertIs(json.loads(real.read_text())["projects"][str(self.proj.resolve())]["hasTrustDialogAccepted"], True)

    def test_a_failed_write_leaves_no_temp_file_and_the_original(self):
        self.f.write_text(json.dumps({"projects": {}}))
        with mock.patch.object(hb.os, "replace", side_effect=OSError("no")):
            self.assertFalse(hb.trust_folder(self.proj))
        self.assertEqual(self.read(), {"projects": {}})
        self.assertEqual([p.name for p in self.d.iterdir() if p.name.startswith(".claude.json.")], [])

    def test_home_file_is_used_without_a_config_dir(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CLAUDE_CONFIG_DIR")
            with mock.patch.object(hb.Path, "home", return_value=self.d):
                self.assertEqual(hb.claude_json_path(), self.d / ".claude.json")

    def test_work_trusts_the_folder_before_the_worker_starts(self):
        order = []
        saved = {k: getattr(hb, k) for k in ("project_exists", "known_path", "session_exists", "start_check", "trust_folder", "new_pane", "load_manifests", "DATA_DIR")}
        self.addCleanup(lambda: [setattr(hb, k, v) for k, v in saved.items()])
        hb.project_exists = lambda n: True
        hb.known_path = lambda n: self.proj
        hb.session_exists = lambda s: True              # the user's session runs; only the worker is new
        hb.session_exists = lambda s: not s.startswith("claude-")
        hb.start_check = lambda n, p: ([], [])
        hb.load_manifests = lambda: {}
        hb.DATA_DIR = self.d / "data"
        hb.trust_folder = lambda p: order.append(("trust", p))

        def pane(args):
            order.append(("pane", args[0]))
            raise RuntimeError("stop here")
        hb.new_pane = pane
        prompt = self.d / "p.md"
        prompt.write_text("# task\n")
        with self.assertRaises(RuntimeError):
            hb.cmd_work(types.SimpleNamespace(name="proj", prompt_file=str(prompt)))
        self.assertEqual([o[0] for o in order], ["trust", "pane"])


if __name__ == "__main__":
    unittest.main()
