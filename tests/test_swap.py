"""Swapping a fresh plan-mode Claude into a pane for the review (swap_claude), going back (back_claude), the review snapshot, the plan-first line in every
prompt, and the guard rule that keeps `hyperbeam review --print` out of non-plan sessions. Runs in the lab:
hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load(name, file):
    loader = importlib.machinery.SourceFileLoader(name, str(HERE / file))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


hb = load("hb", "hyperbeam")
guard = load("guard", "guard.py")

SID = "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"


class Fakes(unittest.TestCase):
    """A project with a running Claude pane, tmux replaced by a recorder."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = {k: getattr(hb, k) for k in ("DATA_DIR", "known_path", "find_claude_pane", "session_exists", "claude_state", "claude_session_file", "tmux", "send_line",
                                                  "report_text", "context_bundle", "session_project", "review_facts")}
        hb.DATA_DIR = self.tmp / "data"
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        hb.known_path = lambda n: self.proj
        hb.find_claude_pane = lambda s: "%7"
        hb.session_exists = lambda s: True
        self.state = ("waiting", "")
        hb.claude_state = lambda n: self.state
        self.sf = self.tmp / f"{SID}.jsonl"
        hb.claude_session_file = lambda pane: self.sf
        self.tmux_calls, self.typed = [], []
        hb.tmux = lambda *a, check=True, **k: (self.tmux_calls.append(a), type("R", (), {"stdout": "", "returncode": 0})())[1]
        hb.send_line = lambda pane, text: self.typed.append(text)
        hb.report_text = lambda name: "last words of the previous session"
        self.prompt = self.tmp / "prompt.md"
        self.prompt.write_text("the prompt")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)


class Swap(Fakes):
    def test_swap_starts_a_fresh_plan_mode_claude_and_remembers_the_old_one(self):
        ok, msg = hb.swap_claude("proj", self.proj, self.prompt, "review")
        self.assertTrue(ok, msg)
        self.assertIn(("respawn-pane", "-k", "-t", "%7", "-c", str(self.proj)), self.tmux_calls)
        self.assertEqual(len(self.typed), 1)
        cmd = self.typed[0]
        self.assertIn("--permission-mode plan", cmd)
        self.assertIn("$(cat ", cmd)
        self.assertNotIn("--continue", cmd)                      # a fresh conversation
        rec = hb.previous_claude("proj")
        self.assertEqual(rec["session_id"], SID)
        self.assertEqual(rec["why"], "review")

    def test_swap_refuses_while_claude_is_working(self):
        self.state = ("working", "")
        ok, msg = hb.swap_claude("proj", self.proj, self.prompt, "review")
        self.assertFalse(ok)
        self.assertIn("working", msg)
        self.assertEqual((self.tmux_calls, self.typed), ([], []))
        self.assertIsNone(hb.previous_claude("proj"))

    def test_swap_needs_a_running_session(self):
        hb.session_exists = lambda s: False
        ok, msg = hb.swap_claude("proj", self.proj, self.prompt, "review")
        self.assertFalse(ok)
        self.assertIn("not running", msg)

    def test_start_review_swaps_in_the_review_prompt(self):
        hb.session_project = lambda sess: "proj"
        hb.review_facts = lambda path, since: "FACTS since " + since
        hb.context_bundle = lambda *a, **k: [("CLAUDE.md", "claude md")]
        ok, msg = hb.start_review("proj", self.proj, "abc123")
        self.assertTrue(ok, msg)
        self.assertIn("--permission-mode plan", self.typed[0])
        self.assertIn("tokens of context", msg)
        f = next((hb.project_dir("proj") / "prompts").glob("*.md"))
        text = f.read_text()
        for part in ("Plan mode first", "Review the work since the last review", "FACTS since abc123", "### CLAUDE.md", "last words of the previous session"):
            self.assertIn(part, text)
        self.assertEqual(hb.previous_claude("proj")["session_id"], SID)

    def test_extra_dirs_are_passed(self):
        hb.swap_claude("proj", self.proj, self.prompt, "review", ["/some/dir"])
        self.assertIn("--add-dir /some/dir", self.typed[0])


class Back(Fakes):
    def test_back_resumes_the_saved_conversation_and_clears_the_record(self):
        hb.swap_claude("proj", self.proj, self.prompt, "review")
        self.typed.clear()
        ok, msg = hb.back_claude("proj")
        self.assertTrue(ok, msg)
        self.assertEqual(len(self.typed), 1)
        self.assertTrue(self.typed[0].endswith(f"--resume {SID}"), self.typed[0])
        self.assertNotIn("--permission-mode plan", self.typed[0])
        self.assertIsNone(hb.previous_claude("proj"))

    def test_back_without_a_record(self):
        ok, msg = hb.back_claude("proj")
        self.assertFalse(ok)
        self.assertIn("no previous", msg)

    def test_back_refuses_while_the_review_claude_is_working(self):
        hb.swap_claude("proj", self.proj, self.prompt, "review")
        self.state = ("working", "")
        ok, msg = hb.back_claude("proj")
        self.assertFalse(ok)
        self.assertIsNotNone(hb.previous_claude("proj"))

    def test_a_bad_id_in_the_record_is_ignored(self):
        hb.pfile("proj", "previous-claude").write_text(json.dumps({"session_id": "x; rm -rf ~"}))
        self.assertIsNone(hb.previous_claude("proj"))


class Snapshot(Fakes):
    def test_snapshot_has_its_parts_and_the_last_words_and_is_capped(self):
        hb.context_bundle = lambda name, path, parts_only=False: [("RULES.md", "rules"), ("CLAUDE.md", "claude md"), ("docs/DECISIONS.md", "index"),
                                                                  ("IDEAS.md", "x" * 30000), ("Last review", "Last review 2026-11-12"), ("README.md", "readme"),
                                                                  ("Recent history", "history")]
        s = hb.review_snapshot("proj", self.proj)
        for part in ("### CLAUDE.md", "### docs/DECISIONS.md", "### IDEAS.md", "### Last review", "### Recent history", "last words of the previous session"):
            self.assertIn(part, s)
        self.assertNotIn("rules", s.replace("Snapshot", ""))      # RULES.md and README.md are not part of it
        self.assertNotIn("### README.md", s)
        self.assertIn("(cut; read the file)", s)
        self.assertLess(len(s), 12000 + 2000 + 1500)

    def test_no_previous_message_is_fine(self):
        hb.report_text = lambda name: (_ for _ in ()).throw(RuntimeError("no Claude"))
        hb.context_bundle = lambda name, path, parts_only=False: [("CLAUDE.md", "claude md")]
        self.assertNotIn("previous session last said", hb.review_snapshot("proj", self.proj))


class PlanFirst(Fakes):
    def test_every_prompt_starts_with_the_plan_first_line(self):
        hb.session_project = lambda sess: "proj"
        f = hb.write_prompt("proj", "body of the prompt")
        text = f.read_text()
        self.assertTrue(text.startswith(hb.PLAN_FIRST))
        self.assertIn("EnterPlanMode", hb.PLAN_FIRST)
        self.assertTrue(text.endswith("body of the prompt"))


class GuardRule(unittest.TestCase):
    def blocked(self, mode, cmd):
        guard.PERMISSION_MODE = mode
        return guard.reviews_outside_plan(cmd)

    def test_print_is_blocked_outside_plan_mode(self):
        self.assertTrue(self.blocked("default", "hyperbeam review hyperbeam --since 9360c15 --print"))
        self.assertTrue(self.blocked("acceptEdits", "hyperbeam review --print"))
        self.assertTrue(self.blocked("bypassPermissions", "~/.local/bin/hyperbeam review x --print | head"))

    def test_allowed_in_plan_mode_or_when_the_mode_is_unknown(self):
        self.assertFalse(self.blocked("plan", "hyperbeam review --print"))
        self.assertFalse(self.blocked("", "hyperbeam review --print"))

    def test_review_without_print_is_always_allowed(self):
        self.assertFalse(self.blocked("default", "hyperbeam review hyperbeam --since 9360c15"))
        self.assertFalse(self.blocked("default", "hyperbeam review --help"))

    def test_other_commands_are_untouched(self):
        self.assertFalse(self.blocked("default", "hyperbeam list --print"))
        self.assertFalse(self.blocked("default", "git log --oneline"))

    def test_the_rule_is_part_of_check_and_says_what_to_do(self):
        guard.PERMISSION_MODE = "default"
        msg = guard.check("hyperbeam review --print")
        self.assertIn("EnterPlanMode", msg)
        guard.PERMISSION_MODE = "plan"
        self.assertFalse(guard.check("hyperbeam review --print"))


if __name__ == "__main__":
    unittest.main()
