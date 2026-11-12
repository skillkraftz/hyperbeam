"""The review pass: counting merged PRs since the last review record, the row note, the context line, the facts for the prompt, the once-a-day offer,
and the Done step. Runs in the lab: hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import importlib.machinery
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("hb", str(HERE / "hyperbeam"))
spec = importlib.util.spec_from_loader("hb", loader)
hb = importlib.util.module_from_spec(spec)
loader.exec_module(hb)


class Repo:
    """A throwaway repo with an origin: main, and PRs merged with merge commits."""

    def __init__(self):
        self.d = Path(tempfile.mkdtemp())
        self.o, self.r = self.d / "o.git", self.d / "r"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.o)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.o), str(self.r)], check=True, capture_output=True)
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        self.git("checkout", "-qb", "main")
        self.write("README.md", "base\n")
        self.commit("base")
        self.git("push", "-q", "origin", "main")

    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.r, check=True, capture_output=True, text=True).stdout.strip()

    def write(self, f, text):
        p = self.r / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-qm", msg)

    def merge_pr(self, n, files=None):
        b = f"pr{n}"
        self.git("checkout", "-qb", b, "main")
        for f in files or [f"file{n}.txt"]:
            self.write(f, f"{n}\n")
        self.commit(f"change {n}")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", f"Merge pull request #{n} from o/{b}", b)
        self.git("push", "-q", "origin", "main")
        return self.git("rev-parse", "--short", "HEAD")

    def review_record(self, date, through, prs="[1, 2]"):
        self.write(f"docs/reviews/{date}.md", f"---\nthrough: {through}\nprs: {prs}\n---\nreviewed\n")
        self.commit(f"review {date}")
        self.git("push", "-q", "origin", "main")


class ReviewCounting(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.path = self.repo.r

    def test_no_record_means_not_in_the_loop(self):
        self.repo.merge_pr(1)
        self.assertIsNone(hb.reviews_due(self.path))
        self.assertEqual(hb.review_notes("x", self.path), [])
        self.assertIsNone(hb.review_line(self.path))

    def test_counts_merges_after_the_record(self):
        through = self.repo.merge_pr(1)
        self.repo.review_record("2026-11-12", through)
        self.assertEqual(hb.reviews_due(self.path)[0], 0)
        self.assertEqual(hb.review_notes("x", self.path), [])            # nothing since: no note
        self.repo.merge_pr(2)
        self.repo.merge_pr(3)
        n, rec = hb.reviews_due(self.path)
        self.assertEqual((n, rec["date"], rec["through"]), (2, "2026-11-12", through))
        self.assertEqual(hb.review_notes("x", self.path), ["2 of 5 PRs since the last review"])

    def test_note_says_due_at_the_limit(self):
        through = self.repo.merge_pr(1)
        self.repo.review_record("2026-11-12", through)
        for n in range(2, 7):
            self.repo.merge_pr(n)
        note = hb.review_notes("x", self.path)[0]
        self.assertTrue(note.startswith("review due: 5 PRs merged since the last review (2026-11-12)"), note)

    def test_newer_record_resets_the_count(self):
        through = self.repo.merge_pr(1)
        self.repo.review_record("2026-11-10", through)
        self.repo.merge_pr(2)
        through2 = self.repo.merge_pr(3)
        self.repo.review_record("2026-11-12", through2)
        self.assertEqual(hb.reviews_due(self.path)[0], 0)
        self.repo.merge_pr(4)
        self.assertEqual(hb.reviews_due(self.path)[0], 1)

    def test_unknown_through_commit_is_ignored(self):
        self.repo.review_record("2026-11-12", "deadbee")
        self.assertIsNone(hb.reviews_due(self.path))

    def test_context_line(self):
        through = self.repo.merge_pr(1)
        self.repo.review_record("2026-11-12", through, prs="[31, 40]")
        self.repo.merge_pr(2)
        line = hb.review_line(self.path)
        self.assertIn("Last review 2026-11-12", line)
        self.assertIn(f"through {through}", line)
        self.assertIn("1 PR merged since", line)
        self.assertIn("offered at 5", line)

    def test_facts_list_prs_files_and_records(self):
        base = self.repo.git("rev-parse", "--short", "HEAD")
        self.repo.merge_pr(7, ["a.txt", "docs/decisions/2026-11-12-x.md"])
        self.repo.merge_pr(8)
        facts = hb.review_facts(self.path, base)
        self.assertIn("Merged PRs since then: 2", facts)
        self.assertIn("Merge pull request #7", facts)
        self.assertIn("a.txt, docs/decisions/2026-11-12-x.md", facts)
        self.assertIn("Decision records added: docs/decisions/2026-11-12-x.md", facts)
        self.assertLess(facts.index("#7"), facts.index("#8"))            # oldest first


class FrontMatter(unittest.TestCase):
    def test_read_front(self):
        self.assertEqual(hb.read_front("---\nid: a\nprs: [1, 2]\n---\n# T\n"), {"id": "a", "prs": "[1, 2]"})
        self.assertEqual(hb.read_front("no front matter"), {})


class OfferedOnce(unittest.TestCase):
    def test_once_per_day_per_project(self):
        old = hb.DATA_DIR
        hb.DATA_DIR = Path(tempfile.mkdtemp())
        try:
            self.assertFalse(hb.review_offered("p"))
            hb.review_mark_offered("p")
            self.assertTrue(hb.review_offered("p"))
            self.assertFalse(hb.review_offered("q"))
        finally:
            hb.DATA_DIR = old


class DoneStep(unittest.TestCase):
    """Menu.review_step on a fake menu: offers once, starts the review when asked, stops Done only when it started, and uses up the offer only then."""

    def setUp(self):
        self.repo = Repo()
        through = self.repo.merge_pr(1)
        self.repo.review_record("2026-11-12", through)
        self.saved = {k: getattr(hb, k) for k in ("load_journal", "known_path", "review_offered", "review_mark_offered", "start_review")}
        hb.load_journal = lambda: {"projects": {"proj": {}}}
        hb.known_path = lambda n: self.repo.r
        hb.review_offered = lambda n: False
        self.offers, self.started, self.marked, self.result = [], [], [], (True, "started")
        hb.review_mark_offered = lambda n: self.marked.append(n)
        hb.start_review = lambda n, p, since: (self.started.append((n, since)), self.result)[1]
        for n in range(2, 7):
            self.repo.merge_pr(n)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def menu(self, answer):
        outer = self

        class Fake:
            say = []
            choose = lambda s, text, opts: (outer.offers.append(text), answer)[1]
            say_from_thread = lambda s, m: s.say.append(m)
            review_step = hb.Menu.review_step
        return Fake()

    def test_below_the_limit_nothing_is_offered(self):
        hb.known_path = lambda n: Repo().r
        self.assertFalse(self.menu("ask").review_step())
        self.assertEqual(self.offers, [])

    def test_at_the_limit_it_offers_and_starts(self):
        self.assertTrue(self.menu("ask").review_step())
        self.assertEqual(len(self.offers), 1)
        self.assertIn("5 PRs merged since the last review", self.offers[0])
        self.assertIn("Previous Claude", self.offers[0])
        self.assertEqual(self.started, [("proj", hb.reviews_due(self.repo.r)[1]["through"])])
        self.assertEqual(self.marked, ["proj"])

    def test_later_does_not_start_does_not_stop_done_and_is_remembered(self):
        self.assertFalse(self.menu("later").review_step())
        self.assertEqual(self.started, [])
        self.assertEqual(self.marked, ["proj"])

    def test_a_review_that_could_not_start_does_not_use_up_the_offer(self):
        self.result = (False, "proj is not running: open it, then ask again")
        m = self.menu("ask")
        self.assertFalse(m.review_step())
        self.assertEqual(self.marked, [])
        self.assertTrue(any("no review started" in x for x in m.say))

    def test_already_offered_today_is_quiet(self):
        hb.review_offered = lambda n: True
        self.assertFalse(self.menu("ask").review_step())
        self.assertEqual(self.offers, [])


if __name__ == "__main__":
    unittest.main()
