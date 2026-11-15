"""hyperbeam never starts Claude work by itself: a failed or slow service, or a project without a manifest, injects nothing into Claude.
A failed service makes the dot red (a finding) and writes a note in the project's notes folder.
Runs in the lab: hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path

from common import hb


class NoAutoPrompts(unittest.TestCase):
    NAMES = ("project_envargs", "default_layout", "tag_session", "tmux", "publish_claude_pane", "send_line", "new_pane", "wait_ready", "pane_tail",
             "write_status", "save_layout", "project_dir", "inject_prompt", "start_claude_with_prompt", "claude_cmd")

    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in self.NAMES}
        self.addCleanup(lambda: [setattr(hb, k, v) for k, v in self.saved.items()])
        self.proj = Path(tempfile.mkdtemp())
        self.data = Path(tempfile.mkdtemp())
        self.sent, self.injected, self.status = [], [], []
        hb.project_envargs = lambda *a, **k: []
        hb.default_layout = lambda sess, path, env: [("%1", "claude", str(path)), ("%2", "shell", str(path))]
        hb.tag_session = lambda s: None
        hb.tmux = lambda *a, **k: type("R", (), {"stdout": "", "stderr": "", "returncode": 0})()
        hb.publish_claude_pane = lambda *a, **k: None
        hb.send_line = lambda pane, text: self.sent.append(text)
        hb.new_pane = lambda args: "%3"
        hb.pane_tail = lambda p: "boom: it crashed"
        hb.write_status = lambda name, findings, notes: self.status.append((list(findings), list(notes)))
        hb.save_layout = lambda n: None
        hb.project_dir = lambda name, path=None: self.data
        hb.inject_prompt = lambda *a, **k: self.injected.append(a)
        hb.start_claude_with_prompt = lambda *a, **k: self.injected.append(a)
        hb.claude_cmd = lambda cont=False: "claude --continue"

    def start(self, man, ready):
        hb.wait_ready = lambda *a: ready
        hb.start_session("proj", man, lambda m: None, path=self.proj)

    def test_a_failed_service_injects_nothing_goes_red_and_writes_a_note(self):
        self.start({"path": str(self.proj), "port": 1, "service": [{"name": "web", "cmd": "false"}]}, "WARNING exited before port 1 opened")
        self.assertEqual(self.injected, [])
        self.assertIn("claude --continue", self.sent)                        # plain Claude, as always
        self.assertFalse(any("Read " in s and ".md" in s for s in self.sent))
        findings, _ = self.status[-1]
        self.assertTrue(any("web" in f and "WARNING" in f for f in findings))
        notes = list((self.data / "notes").glob("*-services.md"))
        self.assertEqual(len(notes), 1)
        self.assertIn("boom: it crashed", notes[0].read_text())

    def test_a_slow_service_is_the_same(self):
        self.start({"path": str(self.proj), "port": 1, "service": [{"name": "web", "cmd": "sleep 999"}]}, "WARNING timeout waiting for port 1")
        self.assertEqual(self.injected, [])
        self.assertTrue(self.status[-1][0])

    def test_a_project_without_a_manifest_injects_nothing(self):
        self.start(None, "started")
        self.assertEqual(self.injected, [])
        self.assertIn("claude --continue", self.sent)

    def test_healthy_services_write_no_note(self):
        self.start({"path": str(self.proj), "port": 1, "service": [{"name": "web", "cmd": "true"}]}, "port 1 open")
        self.assertEqual(self.injected, [])
        self.assertEqual(self.status[-1][0], [])
        self.assertFalse((self.data / "notes").exists())

    def test_the_removed_automatic_paths_are_gone(self):
        for name in ("investigate_prompt", "recover_prompt", "investigate_window", "fix_project", "cmd_problem", "Problem"):
            self.assertFalse(hasattr(hb, name), name)
        self.assertNotIn("on_problem", hb.DEFAULTS)
        self.assertFalse((hb.HERE / "RECOVER.md").exists())

    def test_a_failing_tool_test_is_a_note_never_red(self):
        saved = (hb.git_red_notes, hb.tool_check_findings, hb.context_note, hb.drift_notes, hb.stale_doc_notes, hb.session_exists)
        self.addCleanup(lambda: (setattr(hb, "git_red_notes", saved[0]), setattr(hb, "tool_check_findings", saved[1]), setattr(hb, "context_note", saved[2]),
                                 setattr(hb, "drift_notes", saved[3]), setattr(hb, "stale_doc_notes", saved[4]), setattr(hb, "session_exists", saved[5])))
        hb.git_red_notes = lambda *a, **k: ([], [])
        hb.tool_check_findings = lambda: ["tool x fails its test"]
        hb.context_note = lambda *a: ""
        hb.drift_notes = lambda *a: []
        hb.stale_doc_notes = lambda *a: []
        hb.session_exists = lambda s: False
        hb.recheck("hyperbeam", self.proj)
        red, notes = self.status[-1]
        self.assertEqual(red, [])
        self.assertIn("tool x fails its test", notes)


if __name__ == "__main__":
    unittest.main()
