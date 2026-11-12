"""install.sh, where the project "hyperbeam" lives (known_path), how Claude is started (permissions flags, plan mode), the Go tool build, and the `hyperbeam new` scaffold."""
import json
import os
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path

from common import HERE, hb


@unittest.skipUnless(shutil.which("uv") and shutil.which("git"), "install.sh needs uv and git")
class InstallSh(unittest.TestCase):
    """install.sh against a throwaway origin, with every destination redirected."""

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.dev = self.t / "dev"
        self.dev.mkdir()
        self.git(self.dev, "init", "-q", "-b", "main")
        self.git(self.dev, "config", "user.email", "t@t")
        self.git(self.dev, "config", "user.name", "t")
        for f in ("install.sh", "hyperbeam", "hyperbeam.conf", "guard.py", "config.default.toml"):
            shutil.copy(HERE / f, self.dev / f)
        self.git(self.dev, "add", "-A")
        self.git(self.dev, "commit", "-qm", "one")
        self.git(self.t, "clone", "-q", "--bare", str(self.dev), str(self.t / "origin.git"))
        self.git(self.dev, "remote", "add", "origin", str(self.t / "origin.git"))
        self.settings = self.t / "settings.json"
        self.settings.write_text('{"hooks": {}}')
        self.env = {**os.environ, "HB_LIB": str(self.t / "lib/hyperbeam"), "HB_BIN": str(self.t / "bin"), "HB_TMUXCONF": str(self.t / "tmux/hyperbeam.conf"),
                    "HB_SETTINGS": str(self.settings), "XDG_DATA_HOME": str(self.t / "data"), "XDG_CONFIG_HOME": str(self.t / "cfg")}

    def git(self, cwd, *a):
        subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)

    def install(self):
        return subprocess.run(["bash", str(self.dev / "install.sh")], env=self.env, capture_output=True, text=True, timeout=120)

    def test_clone_links_and_hook_path(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        lib = self.t / "lib/hyperbeam"
        self.assertEqual(os.readlink(self.t / "bin/hyperbeam"), str(lib / "hyperbeam"))
        self.assertEqual(os.readlink(self.t / "tmux/hyperbeam.conf"), str(lib / "hyperbeam.conf"))
        self.assertIn(f"exec /usr/bin/python3 {lib}/guard.py", self.settings.read_text())
        self.assertEqual(subprocess.run(["git", "-C", str(lib), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip(), "main")

    def test_running_again_fast_forwards(self):
        self.assertEqual(self.install().returncode, 0)
        (self.dev / "newfile").write_text("x")
        self.git(self.dev, "add", "-A")
        self.git(self.dev, "commit", "-qm", "two")
        self.git(self.dev, "push", "-q", "origin", "main")
        self.assertEqual(self.install().returncode, 0)
        self.assertTrue((self.t / "lib/hyperbeam/newfile").exists())
        self.assertEqual(self.install().returncode, 0)                    # nothing new: still fine


class WhereHyperbeamLives(unittest.TestCase):
    def setUp(self):
        self.saved = (hb.ROOT, dict(hb._PATHS), hb.load_manifests)
        hb._PATHS.clear()
        hb.load_manifests = lambda: {}

    def tearDown(self):
        hb.ROOT, hb.load_manifests = self.saved[0], self.saved[2]
        hb._PATHS.clear()
        hb._PATHS.update(self.saved[1])

    def test_the_project_is_the_dev_folder_when_it_exists(self):
        root = Path(tempfile.mkdtemp())
        (root / "hyperbeam").mkdir()
        hb.ROOT = root
        self.assertEqual(hb.known_path("hyperbeam"), root / "hyperbeam")

    def test_without_a_dev_folder_it_is_the_app_itself(self):
        hb.ROOT = Path(tempfile.mkdtemp())
        self.assertEqual(hb.known_path("hyperbeam"), hb.HERE)


class StartingClaude(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in ("load_cfg", "pane_command", "send_line")}
        self.cfg = {}
        hb.load_cfg = lambda: self.cfg
        self.typed = []
        hb.send_line = lambda pane, text: self.typed.append(text)
        hb.pane_command = lambda pane: "bash"

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def test_default_is_no_permission_prompts(self):
        self.assertEqual(hb.cfg_get("claude_permissions"), "skip")
        self.assertEqual(hb.claude_base(), "claude --model opusplan --effort medium --dangerously-skip-permissions")

    def test_plan_mode_allows_bypass_but_does_not_turn_it_on(self):
        self.assertEqual(hb.claude_base(plan=True), "claude --model opusplan --effort medium --permission-mode plan --allow-dangerously-skip-permissions")

    def test_ask_turns_the_flags_off(self):
        self.cfg = {"claude_permissions": "ask"}
        self.assertEqual(hb.claude_base(), "claude --model opusplan --effort medium")
        self.assertEqual(hb.claude_base(plan=True), "claude --model opusplan --effort medium --permission-mode plan")

    def test_an_invalid_value_falls_back_to_the_default(self):
        self.cfg = {"claude_permissions": "bogus"}
        self.assertEqual(hb.cfg_get("claude_permissions"), "skip")

    def test_injecting_into_a_shell_pane_starts_claude_in_plan_mode(self):
        self.assertEqual(hb.inject_prompt("%1", "/x/P.md"), "started")
        self.assertIn("--permission-mode plan --allow-dangerously-skip-permissions --continue", self.typed[0])
        self.assertIn('"$(cat /x/P.md)"', self.typed[0])

    def test_injecting_into_a_running_claude_uses_plan_command(self):
        hb.pane_command = lambda pane: "claude"
        self.assertEqual(hb.inject_prompt("%1", "/x/P.md"), "injected")
        self.assertEqual(self.typed, ["/plan Read /x/P.md and follow it."])

    def test_a_fresh_start_has_no_continue(self):
        hb.start_claude_with_prompt("%1", "/x/P.md", cont=False)
        self.assertNotIn("--continue", self.typed[0])


class GoToolBuild(unittest.TestCase):
    def test_a_missing_go_is_a_message_not_a_traceback(self):
        tools = Path(tempfile.mkdtemp())
        (tools / "t").mkdir()
        (tools / "t/go.mod").write_text("module t\n")
        (tools / "t/main.go").write_text("package main\nfunc main() {}\n")
        saved, path = hb.TOOLS_SRC, os.environ["PATH"]
        hb.TOOLS_SRC = tools
        os.environ["PATH"] = ""
        try:
            self.assertEqual(hb.build_tool("t"), "go is not installed (it builds this tool)")
        finally:
            hb.TOOLS_SRC, os.environ["PATH"] = saved, path

    def test_a_script_tool_needs_no_build(self):
        tools = Path(tempfile.mkdtemp())
        (tools / "s").mkdir()
        (tools / "s/s").write_text("#!/bin/sh\n")
        saved = hb.TOOLS_SRC
        hb.TOOLS_SRC = tools
        try:
            self.assertIsNone(hb.build_tool("s"))
        finally:
            hb.TOOLS_SRC = saved


class NewScaffold(unittest.TestCase):
    def test_new_project_gets_decision_records(self):
        home = Path(tempfile.mkdtemp())
        saved_env = {k: os.environ.get(k) for k in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "HB_CONFIG", "HB_MANIFESTS")}
        saved = (hb.ROOT, hb.MANIFESTS, hb.DATA_DIR)
        os.environ.update(XDG_DATA_HOME=str(home / "data"), XDG_CONFIG_HOME=str(home / "cfg"), HB_CONFIG=str(home / "config.toml"), HB_MANIFESTS=str(home / "man"))
        (home / "projects").mkdir()
        hb.ROOT, hb.MANIFESTS, hb.DATA_DIR = home / "projects", home / "man", home / "data"
        try:
            hb.cmd_new(types.SimpleNamespace(name="demo", cli=True, web=False, about="a demo", no_open=True))
        finally:
            hb.ROOT, hb.MANIFESTS, hb.DATA_DIR = saved
            for k, v in saved_env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        docs = home / "projects/demo/docs"
        self.assertEqual(sorted(p.name for p in docs.iterdir()), ["DECISIONS.md", "decisions"])
        rec = next((docs / "decisions").iterdir())
        self.assertTrue(rec.name.endswith("-created.md"))
        self.assertIn("status: implemented", rec.read_text())
        self.assertIn("Generated by", (docs / "DECISIONS.md").read_text())


if __name__ == "__main__":
    unittest.main()
