"""Manager workers (`hyperbeam work|wait|close`, the report written at Stop with HB_WORKER=1) and the one-time move of Claude's global model from opusplan to sonnet.
Runs in the lab: `hyperbeam hyperbeam test`. tmux is replaced by recorders; nothing real is started."""
import io
import json
import os
import subprocess
import tempfile
import threading
import time
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from common import Repo, hb


class SonnetMigration(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.f = self.d / "settings.json"
        self.saved = hb.DATA_DIR
        hb.DATA_DIR = self.d / "data"
        self.addCleanup(setattr, hb, "DATA_DIR", self.saved)

    def model(self):
        return json.loads(self.f.read_text()).get("model")

    def test_opusplan_becomes_sonnet_once_and_a_manual_choice_is_left_alone(self):
        self.f.write_text('{"model": "opusplan"}')
        hb.install_hooks(str(self.f))
        self.assertEqual(self.model(), "sonnet")
        self.f.write_text(json.dumps({**json.loads(self.f.read_text()), "model": "opusplan"}))      # the user switches back by hand
        hb.install_hooks(str(self.f))
        self.assertEqual(self.model(), "opusplan")

    def test_another_model_is_not_touched_and_an_unset_one_stays_unset(self):
        self.f.write_text('{"model": "opus"}')
        hb.install_hooks(str(self.f))
        self.assertEqual(self.model(), "opus")
        g = self.d / "other.json"
        hb.DATA_DIR = self.d / "data2"
        hb.install_hooks(str(g))
        self.assertIsNone(json.loads(g.read_text()).get("model"))


class Workers(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        names = ("DATA_DIR", "tmux", "session_exists", "project_exists", "known_path", "running_sessions", "load_cfg")
        self.saved = {k: getattr(hb, k) for k in names}
        self.addCleanup(lambda: [setattr(hb, k, v) for k, v in self.saved.items()])
        hb.DATA_DIR = self.tmp / "data"
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        hb.known_path = lambda name: self.proj
        hb.project_exists = lambda name: True
        self.sessions = {"proj"}
        self.calls = []
        hb.session_exists = lambda s: s in self.sessions
        hb.running_sessions = lambda: set(self.sessions)

        def tmux(*a, check=True):
            self.calls.append(a)
            if a[0] == "show-environment":
                return types.SimpleNamespace(stdout="HB_WORKER=1\n" if self.is_worker else "", returncode=0)
            return types.SimpleNamespace(stdout="", returncode=0)
        self.is_worker = True
        hb.tmux = tmux
        self.prompt = self.tmp / "p.md"
        self.prompt.write_text("# Fix the thing\nmore\n")

    def test_work_refuses_a_second_worker(self):
        self.sessions.add("claude-proj")
        with self.assertRaises(SystemExit) as e:
            hb.cmd_work(types.SimpleNamespace(name="proj", prompt_file=str(self.prompt)))
        self.assertIn("already has a worker", str(e.exception))
        self.assertEqual(self.calls, [])                    # nothing was started

    def test_close_ends_only_the_worker_session(self):
        self.sessions.add("claude-proj")
        hb.cmd_close(types.SimpleNamespace(name="proj"))
        kills = [a for a in self.calls if a[0] == "kill-session"]
        self.assertEqual(kills, [("kill-session", "-t", "=claude-proj")])

    def test_close_leaves_a_session_that_is_not_a_worker(self):
        self.sessions.add("claude-proj")
        self.is_worker = False
        with self.assertRaises(SystemExit):
            hb.cmd_close(types.SimpleNamespace(name="proj"))
        self.assertFalse([a for a in self.calls if a[0] == "kill-session"])

    def test_close_without_a_worker_touches_nothing(self):
        with self.assertRaises(SystemExit):
            hb.cmd_close(types.SimpleNamespace(name="proj"))
        self.assertFalse([a for a in self.calls if a[0] == "kill-session"])

    def test_the_worker_prompt_is_worker_md_the_problems_then_the_task_and_never_plan_mode(self):
        text = hb.worker_prompt_text(self.prompt, ["merge in progress"])
        self.assertTrue(text.startswith("The start check found problems"))
        self.assertIn("- merge in progress", text)
        self.assertIn("You are a worker", text)
        self.assertTrue(text.rstrip().endswith("more"))
        hb.load_cfg = lambda: {"claude_model": "opusplan"}
        hb.session_project = lambda s: "proj"
        self.assertNotIn("Plan mode first", hb.write_prompt("proj", text, plan=False).read_text())

    def test_wait_prints_the_report_of_a_finished_worker_and_times_out_on_a_busy_one(self):
        self.sessions.add("claude-proj")
        wd = hb.worker_dir("proj")
        (wd / "started.json").write_text(json.dumps({"time": 0}))
        (wd / "claude").write_text("working\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(hb.cmd_wait(types.SimpleNamespace(names=["proj"], timeout=1)), 1)
        (wd / "claude").write_text("waiting finished responding\n")
        rd = hb.reports_dir("proj")
        rd.mkdir(parents=True)
        (rd / "2026-11-15-1200-x.md").write_text("# x\n")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(hb.cmd_wait(types.SimpleNamespace(names=["proj"], timeout=5)), 0)
        self.assertIn("2026-11-15-1200-x.md", out.getvalue())

    def wait(self, timeout=5):
        out = io.StringIO()
        with redirect_stdout(out):
            code = hb.cmd_wait(types.SimpleNamespace(names=["proj"], timeout=timeout))
        return code, out.getvalue()

    def worker(self, state):
        self.sessions.add("claude-proj")
        wd = hb.worker_dir("proj")
        (wd / "started.json").write_text(json.dumps({"time": 0}))
        (wd / "claude").write_text(state)
        for k, v in (("WAIT_POLL", 0.05), ("BLOCKED_GRACE", 0.3)):
            self.addCleanup(setattr, hb, k, getattr(hb, k))
            setattr(hb, k, v)
        return wd

    def test_a_worker_with_a_question_ends_the_wait_at_once_with_status_2(self):
        self.worker("waiting asks you a question\n")
        code, out = self.wait()
        self.assertEqual(code, 2)
        self.assertIn("blocked", out)

    def test_a_needs_input_state_is_waited_through_and_a_stuck_one_is_blocked_after_the_limit(self):
        wd = self.worker("waiting needs your input or permission\n")
        t = time.time()
        code, out = self.wait()
        self.assertEqual(code, 2)
        self.assertGreaterEqual(time.time() - t, 0.3)
        self.assertIn("blocked", out)
        wd = self.worker("waiting needs your input or permission\n")        # Claude Code blocks the prompt itself and carries on, then finishes
        rd = hb.reports_dir("proj")
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "r.md").write_text("# r\n")
        threading.Timer(0.1, lambda: (wd / "claude").write_text("waiting finished responding\n")).start()
        code, out = self.wait()
        self.assertEqual(code, 0)
        self.assertIn("r.md", out)

    def test_the_hooks_put_the_state_back_to_working_and_an_idle_notice_keeps_finished(self):
        events = {e for e, _, st in hb.HOOK_CMDS if st == "working"}
        self.assertTrue({"PostToolUse", "PostToolUseFailure", "PermissionDenied", "UserPromptSubmit"} <= events)
        state = Path(tempfile.mkdtemp())
        env = dict(os.environ, HB_PROJECT="proj", HB_STATE=str(state))
        env.pop("HB_WORKER", None)
        (state / "claude").write_text("waiting finished responding\n")
        run = lambda cmd, inp: subprocess.run(["sh", "-c", cmd], env=env, input=inp, text=True, check=True)
        note = hb.hook_command("waiting needs your input or permission", notification=True)
        run(note, '{"notification_type": "idle_prompt"}')
        self.assertEqual((state / "claude").read_text().strip(), "waiting finished responding")
        run(note, '{"notification_type": "permission_prompt"}')
        self.assertEqual((state / "claude").read_text().strip(), "waiting needs your input or permission")
        run(hb.hook_command("working"), "{}")
        self.assertEqual((state / "claude").read_text().strip(), "working")

    def test_send_refuses_while_the_worker_works_or_sits_at_a_prompt_and_pastes_when_it_waits(self):
        f = self.tmp / "fb.md"
        f.write_text("change X, same PR\n")
        a = types.SimpleNamespace(name="proj", file=str(f))
        wd = self.worker("working\n")
        for st in ("working\n", "waiting needs your input or permission\n"):
            (wd / "claude").write_text(st)
            with self.assertRaises(SystemExit):
                hb.cmd_send(a)
        self.assertEqual([c for c in self.calls if c[0] in ("paste-buffer", "send-keys")], [])
        (wd / "claude").write_text("waiting finished responding\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(hb.cmd_send(a), 0)
        kinds = [c[0] for c in self.calls]
        self.assertEqual(kinds[kinds.index("set-buffer"):][:3], ["set-buffer", "paste-buffer", "send-keys"])
        self.assertIn("change X, same PR", [c for c in self.calls if c[0] == "set-buffer"][0])
        self.assertIn("-p", [c for c in self.calls if c[0] == "paste-buffer"][0])
        self.assertEqual(hb.worker_state("proj")[0], "working")
        self.assertIn("sent", json.loads((wd / "started.json").read_text()))

    def test_send_reads_stdin_for_a_dash_and_refuses_without_a_worker(self):
        with self.assertRaises(SystemExit):
            hb.cmd_send(types.SimpleNamespace(name="proj", file="-"))

    def test_the_sidebar_row_marks_a_running_worker(self):
        row = dict(name="proj", recent=True, branch="main", worker=True)
        self.assertIn("»", hb.row_text(row, ("green", ""), 35).plain)
        row["worker"] = False
        self.assertNotIn("»", hb.row_text(row, ("green", ""), 35).plain)


class Report(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.state = Path(tempfile.mkdtemp())
        self.reports = Path(tempfile.mkdtemp()) / "reports"
        head = self.repo.git("rev-parse", "HEAD")
        (self.state / "started.json").write_text(json.dumps({"time": 0, "head": head, "task": "Fix the Thing!", "path": str(self.repo.r)}))
        self.repo.git("checkout", "-qb", "fix-thing")
        self.repo.write("a.txt", "a\n")
        self.repo.commit("Fix the thing")
        self.transcript = self.state / "t.jsonl"
        recs = [{"type": "user", "message": {"role": "user", "content": "go"}},
                {"type": "assistant", "message": {"id": "m1", "role": "assistant", "content": [{"type": "text", "text": "Done. Branch fix-thing, PR https://github.com/me/proj/pull/7"}]}}]
        self.transcript.write_text("\n".join(json.dumps(r) for r in recs))

    def env(self, worker):
        e = {k: v for k, v in os.environ.items() if k not in ("HB_WORKER", "HB_REPORTS")}
        e.update(HB_PROJECT="proj", HB_STATE=str(self.state))
        if worker:
            e.update(HB_WORKER="1", HB_REPORTS=str(self.reports))
        return e

    def test_the_report_has_the_task_the_message_the_commits_the_pr_and_the_transcript(self):
        saved = dict(os.environ)
        os.environ.update(self.env(True))
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO(json.dumps({"transcript_path": str(self.transcript)}))
        self.addCleanup(setattr, sys, "stdin", old)
        hb.cmd_worker_report(None)
        (f,) = list(self.reports.glob("*.md"))
        self.assertRegex(f.name, r"^\d{4}-\d\d-\d\d-\d{4}-fix-the-thing\.md$")
        text = f.read_text()
        for want in ("# Fix the Thing!", "Done. Branch fix-thing", "branch: fix-thing", "PR: https://github.com/me/proj/pull/7", "Fix the thing", str(self.transcript)):
            self.assertIn(want, text)

    def test_commits_made_in_a_worktree_branch_are_listed(self):
        (self.state / "started.json").write_text(json.dumps({"time": time.time() - 60, "head": self.repo.git("rev-parse", "HEAD"), "task": "T", "path": str(self.repo.r)}))
        self.repo.git("checkout", "-q", "main")                     # the project folder stays on main; the worker commits elsewhere
        wt = self.repo.d / "wt"
        self.repo.git("worktree", "add", "-q", "-b", "wt-branch", str(wt), "main")
        (wt / "w.txt").write_text("w\n")
        for c in (["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "From the worktree"]):
            subprocess.run(["git", *c], cwd=wt, check=True, capture_output=True)
        saved = dict(os.environ)
        os.environ.update(self.env(True))
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO("{}")
        self.addCleanup(setattr, sys, "stdin", old)
        hb.cmd_worker_report(None)
        text = next(self.reports.glob("*.md")).read_text()
        self.assertIn("From the worktree [wt-branch]", text)
        self.assertNotIn("none\n", text.split("## Commits since the worker started")[1][:10])

    def test_the_stop_hook_writes_state_for_everyone_and_calls_the_report_only_for_workers(self):
        cmd = hb.hook_command("waiting finished responding", stop=True)
        self.assertIn("_worker-report", cmd)
        self.assertIn('[ -z "$HB_WORKER" ] ||', cmd)
        subprocess.run(["sh", "-c", cmd], env=self.env(False), check=True)          # no HB_WORKER: no report (and no uv start)
        self.assertEqual((self.state / "claude").read_text().strip(), "waiting finished responding")
        self.assertFalse(self.reports.exists())
        self.assertNotIn("_worker-report", hb.hook_command("working"))


if __name__ == "__main__":
    unittest.main()
