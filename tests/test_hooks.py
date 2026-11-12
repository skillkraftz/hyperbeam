"""The Claude hooks hyperbeam installs (idempotent, no duplicates), the PR refresh hook script, and the signal that tells running menus to re-read the PR cache."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from common import HERE, hb


class InstallHooks(unittest.TestCase):
    def setUp(self):
        self.f = Path(tempfile.mkdtemp()) / "settings.json"
        self.saved = hb.DATA_DIR
        hb.DATA_DIR = self.f.parent / "data"

    def tearDown(self):
        hb.DATA_DIR = self.saved

    def old_style_settings(self, copies=26):
        st = {"hooks": {}, "theme": "dark"}
        for ev, m, state in hb.HOOK_CMDS:
            st["hooks"][ev] = [{"hooks": [{"type": "command", "command": hb.hook_command(state), "timeout": 5}]} for _ in range(copies)]
        st["hooks"]["PreToolUse"] += [{"matcher": "Bash", "hooks": [{"type": "command", "command": hb.guard_command(), "timeout": 5}]} for _ in range(3)]
        st["hooks"]["PostToolUse"].append({"hooks": [{"type": "command", "command": "echo someone-elses-hook"}]})
        self.f.write_text(json.dumps(st))

    def commands(self, event):
        return [h["command"] for g in json.loads(self.f.read_text())["hooks"][event] for h in g["hooks"]]

    def test_duplicates_collapse_and_other_hooks_survive(self):
        self.old_style_settings()
        self.assertTrue(hb.install_hooks(str(self.f)))
        hooks = json.loads(self.f.read_text())["hooks"]
        self.assertEqual({e: len(g) for e, g in hooks.items()}, {"Stop": 1, "Notification": 1, "UserPromptSubmit": 1, "PreToolUse": 2, "PostToolUse": 3})
        self.assertIn("echo someone-elses-hook", self.commands("PostToolUse"))
        self.assertEqual(json.loads(self.f.read_text())["theme"], "dark")             # nothing else is touched

    def test_a_second_run_changes_nothing(self):
        self.old_style_settings(1)
        hb.install_hooks(str(self.f))
        before = self.f.read_text()
        self.assertEqual(hb.install_hooks(str(self.f)), [])
        self.assertEqual(self.f.read_text(), before)

    def test_from_nothing_it_installs_one_of_each(self):
        hb.install_hooks(str(self.f))
        hooks = json.loads(self.f.read_text())["hooks"]
        self.assertEqual({e: len(g) for e, g in hooks.items()}, {"Stop": 1, "Notification": 1, "UserPromptSubmit": 1, "PreToolUse": 2, "PostToolUse": 2})

    def test_the_pr_hook_points_at_the_script_next_to_the_app(self):
        hb.install_hooks(str(self.f))
        cmd = next(c for c in self.commands("PostToolUse") if "hyperbeam-prs" in c)
        self.assertIn(str(HERE / "hooks" / "pr-refresh.sh"), cmd)
        self.assertTrue((HERE / "hooks" / "pr-refresh.sh").is_file())
        guard = next(c for c in self.commands("PreToolUse") if "hyperbeam-guard" in c)
        self.assertIn(str(HERE / "guard.py"), guard)


class PRHookScript(unittest.TestCase):
    """hooks/pr-refresh.sh with a fake `hyperbeam` on PATH that logs its arguments."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.log = self.d / "log"
        (self.d / "bin").mkdir()
        fake = self.d / "bin" / "hyperbeam"
        fake.write_text(f'#!/bin/sh\necho "$@" >> {self.log}\n')
        fake.chmod(0o755)

    def fire(self, command, output, project="proj"):
        env = {**os.environ, "PATH": f"{self.d / 'bin'}:{os.environ['PATH']}"}
        env.pop("HB_PROJECT", None)
        if project:
            env["HB_PROJECT"] = project
        self.log.write_text("")
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "tool_response": {"stdout": output}})
        r = subprocess.run(["sh", str(HERE / "hooks" / "pr-refresh.sh")], input=payload, text=True, env=env, timeout=10)
        self.assertEqual(r.returncode, 0)
        for _ in range(20):                                           # the refresh runs in the background
            if self.log.read_text():
                break
            time.sleep(0.05)
        return self.log.read_text().strip() or "(nothing run)"

    def test_create_passes_the_new_number(self):
        self.assertEqual(self.fire("gh pr create --title x --body-file b.md", "https://github.com/o/r/pull/41\n"), "refresh-prs proj 41")

    def test_merge_and_close_pass_the_numbers_as_gone(self):
        self.assertEqual(self.fire("gh pr merge 36 --merge --delete-branch", "ok"), "refresh-prs proj --gone 36")
        self.assertEqual(self.fire("gh pr close 7; gh pr close 8", "ok"), "refresh-prs proj --gone 7 8")

    def test_other_commands_do_nothing(self):
        self.assertEqual(self.fire("git status", "On branch main"), "(nothing run)")
        self.assertEqual(self.fire("gh pr view 12", "https://github.com/o/r/pull/12"), "(nothing run)")
        self.assertEqual(self.fire("gh pr list", "https://github.com/o/r/pull/12"), "(nothing run)")

    def test_outside_a_hyperbeam_session_nothing_runs(self):
        self.assertEqual(self.fire("gh pr create", "https://github.com/o/r/pull/5", project=None), "(nothing run)")


class NudgeMenus(unittest.TestCase):
    def test_only_menus_that_registered_usr2_get_the_signal(self):
        d = Path(tempfile.mkdtemp())
        saved = hb.MENU_PIDS
        hb.MENU_PIDS = d
        new = subprocess.Popen([sys.executable, "-c", "import signal,time\nsignal.signal(signal.SIGUSR2, lambda *a: print('GOT', flush=True))\ntime.sleep(5)", "_menu"],
                               stdout=subprocess.PIPE, text=True)
        old = subprocess.Popen([sys.executable, "-c", "import time\ntime.sleep(5)", "_menu"])
        try:
            (d / str(new.pid)).write_text(json.dumps({"home": "x", "usr2": True}))
            (d / str(old.pid)).write_text(json.dumps({"home": "x"}))
            time.sleep(0.5)
            hb.nudge_menus()
            time.sleep(0.5)
            self.assertIsNone(old.poll())                              # an older menu would be killed by SIGUSR2: it is not signalled
            new.terminate()
            self.assertIn("GOT", new.stdout.read())
        finally:
            hb.MENU_PIDS = saved
            new.kill()
            old.kill()
            new.wait()
            old.wait()
            new.stdout.close()


if __name__ == "__main__":
    unittest.main()
