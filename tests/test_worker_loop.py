"""The worker loop on a real tmux server (an isolated one: HB_TMUX_SOCKET, no display) with a fake `claude`: work -> wait -> send -> wait -> close, a session that
ends while `wait` waits, and the hooks of a worker's nested `claude -p`. The fake runs the real hook commands the way Claude Code does (UserPromptSubmit,
Stop with a JSON on stdin) and takes `send`'s bracketed paste in raw mode. Runs in the lab: `hyperbeam hyperbeam test`."""
import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import tempfile
import threading
import types
import unittest
from pathlib import Path

from common import hb

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, subprocess, sys, termios, tty
prompt = sys.argv[-1]
out, sid = Path = os.environ["FAKE_OUT"], os.environ.get("FAKE_SID", "session-A")
open(out + "/prompt.txt", "w").write(prompt)
tp = out + "/transcript.jsonl"
n = 0

def hook(cmd, payload):
    subprocess.run(["sh", "-c", cmd], input=json.dumps(payload), text=True)

def add(rec):
    open(tp, "a").write(json.dumps(rec) + "\n")

def turn(text):
    global n
    n += 1
    add({"type": "user", "message": {"role": "user", "content": text}})
    hook(os.environ["FAKE_UPS"], {"session_id": sid, "prompt": text})
    if "FAKE-HANG" in text:
        while True:
            os.read(0, 1)
    add({"type": "assistant", "message": {"id": f"m{n}", "role": "assistant", "content": [{"type": "text", "text": f"answer {n}: " + text.strip().splitlines()[-1]}]}})
    hook(os.environ["FAKE_STOP"], {"session_id": sid, "transcript_path": tp, "cwd": os.getcwd()})

turn(prompt)
sys.stdout.write("\x1b[?2004h")
sys.stdout.flush()
tty.setraw(0)
buf = b""
while True:
    buf += os.read(0, 65536)
    if b"\x1b[200~" in buf and b"\x1b[201~" in buf and buf.endswith(b"\r"):         # a bracketed paste, then Enter
        pre, rest = buf.split(b"\x1b[200~", 1)
        pasted, post = rest.split(b"\x1b[201~", 1)
        text = pasted.decode().replace("\r", "\n")
        open(out + f"/received-{n + 1}.json", "w").write(json.dumps({"text": text, "before": pre.decode(), "after": post.decode()}))
        buf = b""
        turn(text)
'''


class WorkerLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        (bin_ / "claude").write_text(FAKE_CLAUDE)
        (bin_ / "claude").chmod(0o755)
        self.out = self.tmp / "out"
        self.out.mkdir()
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        env = {"HB_TMUX_SOCKET": f"hbtest-{os.getpid()}-{self.id().split('.')[-1][:20]}", "FAKE_OUT": str(self.out), "PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}",
               }
        saved = dict(os.environ)
        os.environ.update(env)
        for k in ("WAYLAND_DISPLAY", "DISPLAY", "TMUX", "HB_WORKER", "HB_STATE", "HB_REPORTS"):
            os.environ.pop(k, None)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        names = ("SELF", "DATA_DIR", "project_exists", "known_path", "start_check", "install_shims", "WAIT_POLL")
        old = {k: getattr(hb, k) for k in names}
        self.addCleanup(lambda: [setattr(hb, k, v) for k, v in old.items()])
        hb.SELF = f"uv run --quiet --script {hb.HERE / 'hyperbeam'}"                    # the script's own shebang names the user's uv, which the lab user may not run
        hb.DATA_DIR = self.tmp / "data"
        hb.known_path = lambda name: self.proj
        hb.project_exists = lambda name: True
        hb.start_check = lambda name, path: ([], [])
        hb.install_shims = lambda: None
        os.environ["FAKE_UPS"] = hb.hook_command("working", prompt=True)
        os.environ["FAKE_STOP"] = hb.hook_command("waiting finished responding", stop=True)
        hb.WAIT_POLL = 0.2
        self.addCleanup(lambda: hb.tmux("kill-server", check=False))
        hb.tmux("new-session", "-d", "-s", "proj", "-c", str(self.proj))                 # the user's session
        hb.tmux("new-session", "-d", "-s", "other")
        self.prompt = self.tmp / "task.md"

    def task(self, text):
        self.prompt.write_text(text)

    def say(self, fn, *a, **kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            return fn(*a, **kw), buf.getvalue()

    def wait(self, timeout=30):
        return self.say(hb.cmd_wait, types.SimpleNamespace(names=["proj"], timeout=timeout))

    def sessions(self):
        return set(hb.tmux("list-sessions", "-F", "#{session_name}").stdout.split())

    def reports(self):
        return sorted(hb.reports_dir("proj").glob("*.md"))

    def test_work_wait_send_wait_close(self):
        self.task("# Fix the thing\nsecond line\n")
        self.say(hb.cmd_work, types.SimpleNamespace(name="proj", prompt_file=str(self.prompt)))
        self.assertEqual(self.sessions(), {"proj", "other", "claude-proj"})
        code, printed = self.wait()
        self.assertEqual(code, 0, printed)
        prompt = (self.out / "prompt.txt").read_text()
        self.assertIn("Fix the thing", prompt)                                           # the real command line reached the fake, with WORKER.md in front
        self.assertTrue(prompt.startswith(hb.worker_prompt_text(self.prompt, [])[:40]))
        reps = self.reports()
        self.assertEqual(len(reps), 1, printed)
        self.assertIn("answer 1: second line", reps[0].read_text())
        self.assertEqual((hb.worker_dir("proj") / "claude").read_text().strip(), "waiting finished responding")

        fb = self.tmp / "fb.md"
        fb.write_text("change X\n\n  indented line\nlast line, \"quoted\" and $HOME\n")
        self.say(hb.cmd_send, types.SimpleNamespace(name="proj", file=str(fb)))
        code, printed = self.wait()
        self.assertEqual(code, 0, printed)
        got = json.loads((self.out / "received-2.json").read_text())                    # the paste arrived whole, between the paste markers, Enter once after
        self.assertEqual(got["text"], fb.read_text().strip())
        self.assertEqual((got["before"], got["after"]), ("", "\r"))
        reps = self.reports()
        self.assertEqual(len(reps), 1)
        text = reps[0].read_text()
        self.assertIn("answer 2: last line", text)
        self.assertIn("answer 1: second line", text.split("## Earlier rounds")[1])

        self.say(hb.cmd_close, types.SimpleNamespace(name="proj"))
        self.assertEqual(self.sessions(), {"proj", "other"})                            # only claude-proj is gone
        self.assertEqual(len(self.reports()), 1)

    def test_the_session_ending_while_waiting_is_exit_2(self):
        self.task("# Hang\nFAKE-HANG\n")
        self.say(hb.cmd_work, types.SimpleNamespace(name="proj", prompt_file=str(self.prompt)))
        t = threading.Timer(2.0, lambda: hb.tmux("kill-session", "-t", "=claude-proj", check=False))
        t.start()
        self.addCleanup(t.cancel)
        code, printed = self.wait()
        self.assertEqual(code, 2)
        self.assertIn("worker ended", printed)

    def test_a_nested_claudes_hooks_do_not_finish_the_worker(self):
        state, reports = self.tmp / "state", self.tmp / "reports"
        state.mkdir()
        env = dict(os.environ, HB_PROJECT="proj", HB_STATE=str(state), HB_WORKER="1", HB_REPORTS=str(reports))
        run = lambda cmd, sid: subprocess.run(["sh", "-c", cmd], env=env, input=json.dumps({"session_id": sid}), text=True, check=True)
        ups, stop = os.environ["FAKE_UPS"], os.environ["FAKE_STOP"]
        run(ups, "worker")                                                               # the worker's own first prompt records its session
        run(ups, "nested")                                                               # a nested `claude -p` does not replace it
        self.assertEqual((state / "session_id").read_text(), "worker")
        run(stop, "nested")                                                              # ... and its Stop is not the worker finishing
        self.assertEqual((state / "claude").read_text().strip(), "working")
        self.assertFalse(reports.exists())
        run(stop, "worker")
        self.assertEqual((state / "claude").read_text().strip(), "waiting finished responding")
        self.assertEqual(len(list(reports.glob("*.md"))), 1)


if __name__ == "__main__":
    unittest.main()
