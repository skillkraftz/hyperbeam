"""The work loop's start and end: how Claude starts when a project is opened (fresh plan session / review / continue), what the fresh session is told, the
previous conversation kept aside, and the same choice after a Merge. Runs in the lab:
hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import json
import tempfile
import unittest
from pathlib import Path

from common import hb

DUE = (5, {"date": "2026-11-12", "through": "abc1234"})
NOT_DUE = (2, {"date": "2026-11-12", "through": "abc1234"})


class Base(unittest.TestCase):
    NAMES = ("DATA_DIR", "CLAUDE_DIR", "known_path", "ensure_link", "load_layout", "start_check", "start_session", "session_exists", "reviews_due", "open_prs",
             "review_snapshot", "review_prompt", "send_line", "swap_claude", "start_review", "start_fresh")

    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in self.NAMES}
        self.tmp = Path(tempfile.mkdtemp())
        hb.DATA_DIR = self.tmp / "data"
        hb.CLAUDE_DIR = self.tmp / "claude"
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        hb.known_path = lambda n: self.proj
        hb.reviews_due = lambda path, name=None: None
        hb.open_prs = lambda *a, **k: []
        hb.review_snapshot = lambda n, p: "SNAPSHOT"
        self.typed = []
        hb.send_line = lambda pane, text: self.typed.append(text)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def conversation(self, sid="0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"):
        d = hb.CLAUDE_DIR / "projects" / hb.re.sub(r"[^A-Za-z0-9]", "-", str(self.proj))
        d.mkdir(parents=True)
        f = d / f"{sid}.jsonl"
        f.write_text("{}\n")
        return f


class OpenChoice(Base):
    def setUp(self):
        super().setUp()
        hb.ensure_link = lambda *a: None
        hb.load_layout = lambda n: None
        hb.session_exists = lambda s: False
        hb.start_check = lambda n, p: ([], [])
        self.begins = []
        hb.start_session = lambda *a, **k: self.begins.append(k.get("begin", "unset"))
        self.asked = []
        self.answer = "fresh"

    def choose(self, text, options, enter=None):
        self.asked.append(([o[0] for o in options], enter, text))
        return self.answer

    def open(self, man=True, onboard=False, ask=lambda t: False):
        hb.open_project("proj", self.proj, {"port": 1} if man else None, ask, lambda m: None, onboard, choose=self.choose)

    def test_no_earlier_conversation_asks_nothing(self):
        self.open()
        self.assertEqual((self.asked, self.begins), ([], [None]))

    def test_earlier_conversation_asks_and_passes_the_answer(self):
        self.conversation()
        self.open()
        self.assertEqual(self.asked[0][:2], (["fresh", "continue"], "fresh"))
        self.assertIn("Previous Claude", self.asked[0][2])
        self.assertEqual(self.begins, ["fresh"])

    def test_review_is_offered_only_when_due_and_escape_still_continues(self):
        self.conversation()
        hb.reviews_due = lambda path, name=None: DUE
        self.open()
        self.assertEqual(self.asked[0][0], ["fresh", "review", "continue"])          # the last option is Escape: never a review
        self.assertIn("A review is due: 5 PRs merged since the last review (2026-11-12)", self.asked[0][2])
        self.asked.clear()
        hb.reviews_due = lambda path, name=None: NOT_DUE
        self.open()
        self.assertEqual(self.asked[0][0], ["fresh", "continue"])

    def test_no_question_for_onboard_no_manifest_or_recover(self):
        self.conversation()
        self.open(onboard=True)
        self.open(man=False)
        hb.start_check = lambda n, p: (["merge stuck with conflicts"], [])
        self.open(ask=lambda t: True)                                               # the user said yes to "Start Claude to sort it out?"
        self.assertEqual(self.asked, [])
        self.assertEqual(self.begins, [None, None, None])

    def test_cli_without_a_terminal_continues(self):
        self.assertEqual(hb.choose_tty("x", [("fresh", "F", "f"), ("continue", "C", "c")], "fresh"), "continue")


class BeginClaude(Base):
    def test_fresh_is_a_plan_session_from_start_md_and_keeps_the_old_conversation(self):
        f = self.conversation()
        hb.begin_claude("proj", self.proj, "%1", "fresh")
        cmd = self.typed[0]
        self.assertIn("--permission-mode plan", cmd)
        self.assertNotIn("--continue", cmd)
        prompt = Path(cmd.split("$(cat ")[1].split(")")[0].strip("'"))
        text = prompt.read_text()
        self.assertTrue(text.startswith(hb.PLAN_FIRST))
        for want in ("# Start a piece of work", "Open PRs (yours): none", "SNAPSHOT"):
            self.assertIn(want, text)
        self.assertEqual(json.loads(hb.pfile("proj", "previous-claude").read_text())["session_id"], f.stem)

    def test_continue_and_plain(self):
        hb.begin_claude("proj", self.proj, "%1", "continue")
        hb.begin_claude("proj", self.proj, "%1", None)
        hb.begin_claude("proj", self.proj, "%1", None, cont=True)
        self.assertIn("--continue", self.typed[0])
        self.assertNotIn("--continue", self.typed[1])
        self.assertIn("--continue", self.typed[2])

    def test_review_starts_from_the_review_prompt_and_falls_back_to_fresh(self):
        self.conversation()
        rp = self.tmp / "review.md"
        rp.write_text("REVIEW PROMPT")
        seen = []
        hb.review_prompt = lambda n, p, since: (seen.append(since), rp)[1]
        hb.reviews_due = lambda path, name=None: DUE
        hb.begin_claude("proj", self.proj, "%1", "review")
        self.assertEqual(seen, ["abc1234"])
        self.assertIn(str(rp), self.typed[0])
        self.assertIn("--permission-mode plan", self.typed[0])
        hb.reviews_due = lambda path, name=None: None                                  # nothing due after all: a fresh session, not an error
        hb.begin_claude("proj", self.proj, "%1", "review")
        self.assertNotIn(str(rp), self.typed[1])


class NextStep(Base):
    """Menu.next_step: after a Merge run the same choice, so a conversation has an end."""

    def setUp(self):
        super().setUp()
        hb.session_exists = lambda s: True
        self.calls = []
        hb.start_fresh = lambda n, p: (self.calls.append(("fresh", n)), (True, "a fresh Claude in plan mode"))[1]
        hb.start_review = lambda n, p, since: (self.calls.append(("review", since)), (True, "review started"))[1]

    def menu(self, answer):
        outer = self

        class Fake:
            say = []
            choose = lambda s, text, opts, enter=None: (outer.offers.append(([o[0] for o in opts], enter, text)), answer)[1]
            say_from_thread = lambda s, m: s.say.append(m)
            next_step = hb.Menu.next_step
        return Fake()

    def run_step(self, answer):
        self.offers = []
        m = self.menu(answer)
        m.next_step({"name": "proj", "path": str(self.proj)}, [{"number": 7}, {"number": 8}])
        return m

    def test_fresh(self):
        m = self.run_step("fresh")
        self.assertEqual(self.offers[0][:2], (["fresh", "keep"], "fresh"))
        self.assertIn("merged #7, #8", self.offers[0][2])
        self.assertEqual(self.calls, [("fresh", "proj")])
        self.assertIn("a fresh Claude in plan mode", m.say[0])

    def test_keep_does_nothing(self):
        m = self.run_step("keep")
        self.assertEqual((self.calls, m.say), ([], []))

    def test_review_when_due(self):
        hb.reviews_due = lambda path, name=None: DUE
        self.run_step("review")
        self.assertEqual(self.offers[0][0], ["fresh", "review", "keep"])
        self.assertEqual(self.calls, [("review", "abc1234")])

    def test_not_running_asks_nothing(self):
        hb.session_exists = lambda s: False
        self.run_step("fresh")
        self.assertEqual((self.offers, self.calls), ([], []))


if __name__ == "__main__":
    unittest.main()
