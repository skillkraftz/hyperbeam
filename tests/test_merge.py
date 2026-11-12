"""Merge: pr_state (behind / overlap / conflicts), merge_pr and what it does to the local checkout, the merge-all loop, open_prs (add / gone), the PR poller."""
import json
import tempfile
import unittest
from pathlib import Path

from common import Repo, hb


class PRState(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.repo.write("D.md", "top\nrest\n")
        self.repo.commit("D")
        self.repo.git("push", "-q", "origin", "main")
        self.repo.git("checkout", "-qb", "pr", "main")
        self.repo.write("D.md", "pr entry\ntop\nrest\n")
        self.repo.commit("pr")
        self.repo.git("push", "-q", "origin", "pr")
        self.repo.git("checkout", "-q", "main")
        self.pr = {"branch": "pr", "base": "main"}

    def main_commit(self, f, text):
        self.repo.write(f, text)
        self.repo.commit(f"main {f}")
        self.repo.git("push", "-q", "origin", "main")

    def test_not_behind(self):
        self.assertEqual(hb.pr_state(self.repo.r, self.pr), {"behind": 0, "overlap": [], "conflicts": []})

    def test_behind_in_other_files_is_not_a_problem(self):
        self.main_commit("projects/x.toml", "manifest\n")
        self.main_commit("README.md", "other pr\n")
        self.assertEqual(hb.pr_state(self.repo.r, self.pr), {"behind": 2, "overlap": [], "conflicts": []})

    def test_same_file_different_lines_overlaps_but_does_not_conflict(self):
        self.main_commit("D.md", "top\nrest\nmain at the end\n")
        st = hb.pr_state(self.repo.r, self.pr)
        self.assertEqual((st["behind"], st["overlap"], st["conflicts"]), (1, ["D.md"], []))

    def test_same_lines_conflict(self):
        self.main_commit("D.md", "main entry\ntop\nrest\n")
        st = hb.pr_state(self.repo.r, self.pr)
        self.assertEqual((st["behind"], st["overlap"], st["conflicts"]), (1, ["D.md"], ["D.md"]))

    def test_cannot_be_told(self):
        self.assertIsNone(hb.pr_state(self.repo.r, {"branch": "", "base": "main"}))
        self.assertIsNone(hb.pr_state(self.repo.r, {"branch": "no-such-branch", "base": "main"}))


class MergePR(unittest.TestCase):
    """merge_pr with a fake gh: what happens to the local checkout."""

    def setUp(self):
        self.repo = Repo()
        self.saved = {k: getattr(hb, k) for k in ("gh_run", "github_slug", "time")}
        self.gh_calls = []
        hb.github_slug = lambda p: "o/r"
        hb.gh_run = lambda slug, *a: (self.gh_calls.append(a), (0, "", ""))[1]
        self.pr = {"number": 7, "branch": "pr7", "base": "main"}
        self.repo.git("branch", "pr7")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def branch(self):
        return self.repo.git("rev-parse", "--abbrev-ref", "HEAD")

    def test_on_main_it_pulls(self):
        ok, local_ok, msgs = hb.merge_pr("x", self.repo.r, self.pr)
        self.assertEqual((ok, local_ok), (True, True))
        self.assertIn("local: on main", msgs)
        self.assertEqual(self.gh_calls[0][:3], ("pr", "merge", "7"))

    def test_on_the_merged_branch_it_goes_to_main(self):
        self.repo.git("checkout", "-q", "pr7")
        ok, local_ok, msgs = hb.merge_pr("x", self.repo.r, self.pr)
        self.assertEqual((ok, local_ok, self.branch()), (True, True, "main"))

    def test_a_feature_branch_you_are_working_on_is_left_alone(self):
        self.repo.git("checkout", "-qb", "my-feature")
        ok, local_ok, msgs = hb.merge_pr("x", self.repo.r, self.pr)
        self.assertEqual((ok, local_ok, self.branch()), (True, False, "my-feature"))
        self.assertTrue(any("left as it is" in m and "my-feature" in m for m in msgs), msgs)

    def test_uncommitted_changes_are_left_alone(self):
        self.repo.write("README.md", "changed\n")
        ok, local_ok, msgs = hb.merge_pr("x", self.repo.r, self.pr)
        self.assertEqual((ok, local_ok, self.branch()), (True, False, "main"))
        self.assertTrue(any("uncommitted" in m for m in msgs), msgs)
        self.assertEqual((self.repo.r / "README.md").read_text(), "changed\n")

    def test_a_failed_merge_changes_nothing(self):
        hb.gh_run = lambda slug, *a: (1, "", "GraphQL: not mergeable")
        ok, local_ok, msgs = hb.merge_pr("x", self.repo.r, self.pr)
        self.assertEqual((ok, local_ok), (False, False))
        self.assertTrue(msgs[0].startswith("merge failed:"), msgs)

    def test_base_branch_modified_is_retried_once(self):
        answers = [(1, "", "Base branch was modified. Review and try the merge again."), (0, "", "")]
        hb.gh_run = lambda slug, *a: answers.pop(0)
        hb.time = type("T", (), {"sleep": staticmethod(lambda s: None), "time": staticmethod(lambda: 0), "strftime": staticmethod(lambda f: "x")})
        ok, local_ok, msgs = hb.merge_pr("x", self.repo.r, self.pr)
        self.assertEqual((ok, answers), (True, []))

    def test_no_github_remote(self):
        hb.github_slug = lambda p: None
        self.assertEqual(hb.merge_pr("x", self.repo.r, self.pr), (False, False, ["no GitHub remote"]))


class Fake:
    """A menu with the pieces _merge_all and _merge_one use."""

    def __init__(self, answers=()):
        self.busy, self.say, self.asked, self.chose, self.answers, self.updated, self.asked_update = {"x"}, [], [], [], list(answers), 0, []

    ask = lambda self, t: (self.asked.append(t), True)[1]
    choose = lambda self, t, opts, enter=None: (self.chose.append(t), self.answers.pop(0))[1]
    say_from_thread = lambda self, m: self.say.append(m)
    call_from_thread = lambda self, f, *a: f(*a)
    refresh_list = lambda self: None
    _merge_one = hb.Menu._merge_one
    next_steps = None

    def next_step(self, p, merged):                       # the fresh-start choice after a finished run (tests/test_start.py)
        self.next_steps = (self.next_steps or []) + [[x["number"] for x in merged]]

    def _ask_update(self, p, pr, behind, base, conflicts=()):
        self.asked_update.append((pr["number"], list(conflicts)))
        return "asked Claude to rebase"

    def update_hyperbeam(self):
        self.updated += 1


class MergeAll(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in ("pr_state", "merge_pr", "open_prs", "run_verb", "DATA_DIR", "pr_stale")}
        self.log, self.updates = [], []
        hb.DATA_DIR = Path(tempfile.mkdtemp())
        hb.pr_stale = lambda pr: False
        hb.run_verb = lambda name, verb, path, say: (self.updates.append(name), 0)[1]
        self.prs = [{"number": n, "title": f"t{n}", "base": "main", "branch": f"b{n}"} for n in (35, 33, 34)]
        hb.open_prs = lambda *a, **k: [q for q in self.prs if q["number"] not in k.get("gone", ())]
        self.state = lambda n: {"behind": 0, "overlap": [], "conflicts": []}
        hb.pr_state = lambda path, pr: self.state(pr["number"])
        self.local_ok = True
        self.fail_at = None

        def merge_pr(name, path, pr, say):
            self.log.append(pr["number"])
            if pr["number"] == self.fail_at:
                return False, False, ["merge failed: GraphQL: Pull Request is not mergeable"]
            return True, self.local_ok, [f"merged PR #{pr['number']} on GitHub", "local: on main"]
        hb.merge_pr = merge_pr

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def run_all(self, name="hyperbeam", answers=()):
        f = Fake(answers)
        p = {"name": name, "path": "/x", "prs": list(self.prs)}
        hb.Menu._merge_all(f, p, sorted(self.prs, key=lambda x: x["number"]))
        return f, p

    def left(self, p):
        return [q["number"] for q in (p["prs"] or [])]

    def test_all_clear_merges_oldest_first_with_one_question_and_one_update(self):
        f, p = self.run_all()
        self.assertEqual(self.log, [33, 34, 35])
        self.assertEqual((len(f.asked), f.updated, self.left(p)), (1, 1, []))
        self.assertEqual(f.say[-1], "hyperbeam: merged #33, #34, #35")
        self.assertEqual(f.next_steps, [[33, 34, 35]])                 # the work is done: the fresh-start choice comes once, before hyperbeam's update restarts the menu

    def test_a_conflict_stops_the_run_and_asks_claude_to_rebase(self):
        self.state = lambda n: {"behind": 1, "overlap": ["D.md"], "conflicts": ["D.md"]} if n == 34 else {"behind": 0, "overlap": [], "conflicts": []}
        f, p = self.run_all()
        self.assertEqual(self.log, [33])
        self.assertEqual(f.asked_update, [(34, ["D.md"])])
        self.assertEqual(self.left(p), [35, 34])
        self.assertIn("stopped at #34: asked Claude to rebase", f.say[-1])
        self.assertIsNone(f.next_steps)                                # a stopped run is not a finished piece of work

    def test_overlap_asks_and_cancel_stops(self):
        self.state = lambda n: {"behind": 1, "overlap": ["hyperbeam"], "conflicts": []} if n == 34 else {"behind": 0, "overlap": [], "conflicts": []}
        f, p = self.run_all(answers=["cancel"])
        self.assertEqual((self.log, self.left(p)), ([33], [35, 34]))
        self.assertIn("also changed hyperbeam", f.chose[0])
        self.assertIn("stopped at #34: cancelled", f.say[-1])

    def test_overlap_merge_anyway_goes_on(self):
        self.state = lambda n: {"behind": 1, "overlap": ["hyperbeam"], "conflicts": []} if n == 34 else {"behind": 0, "overlap": [], "conflicts": []}
        f, p = self.run_all(answers=["merge"])
        self.assertEqual((self.log, self.left(p)), ([33, 34, 35], []))

    def test_overlap_ask_claude_stops(self):
        self.state = lambda n: {"behind": 2, "overlap": ["hyperbeam"], "conflicts": []} if n == 35 else {"behind": 0, "overlap": [], "conflicts": []}
        f, p = self.run_all(answers=["ask"])
        self.assertEqual((self.log, f.asked_update), ([33, 34], [(35, [])]))

    def test_behind_in_other_files_merges_without_a_question(self):
        self.state = lambda n: {"behind": 3, "overlap": [], "conflicts": []}
        f, p = self.run_all()
        self.assertEqual((self.log, f.chose), ([33, 34, 35], []))

    def test_github_refusing_with_a_conflict_hands_it_to_claude(self):
        self.fail_at = 34
        f, p = self.run_all()
        self.assertEqual(self.log, [33, 34])
        self.assertEqual(f.asked_update, [(34, ["(see the PR on GitHub)"])])

    def test_another_failure_just_stops_with_its_message(self):
        hb.merge_pr = lambda name, path, pr, say: (False, False, ["merge failed: network"]) if pr["number"] == 34 else (True, True, ["merged", "local: on main"])
        f, p = self.run_all()
        self.assertIn("stopped at #34: merge failed: network", f.say[-1])

    def test_hyperbeam_updates_even_when_the_dev_folder_was_left_alone(self):          # the installed copy updates from GitHub
        self.local_ok = False
        f, p = self.run_all()
        self.assertEqual(f.updated, 1)

    def test_other_projects_update_only_when_the_checkout_was_pulled(self):
        f, p = self.run_all(name="dotwork")
        self.assertEqual((self.updates, f.updated), (["dotwork"], 0))
        self.updates.clear()
        self.local_ok = False
        self.run_all(name="dotwork")
        self.assertEqual(self.updates, [])

    def test_nothing_merged_means_no_update(self):
        self.state = lambda n: {"behind": 1, "overlap": ["x"], "conflicts": ["x"]}
        f, p = self.run_all()
        self.assertEqual((self.log, f.updated, self.updates), ([], 0, []))
        self.assertIn("nothing merged", f.say[-1])

    def test_a_check_that_cannot_be_made_says_so_and_merges(self):
        hb.pr_state = lambda path, pr: None
        f, p = self.run_all()
        self.assertEqual(self.log, [33, 34, 35])
        self.assertTrue(any("could not check PR #33" in m for m in f.say))


class OpenPRs(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in ("gh_run", "github_slug", "pr_cache_file")}
        self.d = Path(tempfile.mkdtemp())
        self.row = lambda n, st="OPEN": {"number": n, "title": f"t{n}", "url": "u", "headRefName": f"b{n}", "baseRefName": "main", "createdAt": "2026-11-12T10:00:00Z", "state": st}

        def gh(slug, *a):
            if a[:2] == ("pr", "list"):
                return 0, json.dumps([self.row(38)]), ""                    # GitHub's search index lags: 39 is not listed yet
            return 0, json.dumps(self.row(int(a[2]), "OPEN" if a[2] == "39" else "MERGED")), ""
        hb.gh_run, hb.github_slug, hb.pr_cache_file = gh, lambda p: "o/r", lambda n, p: self.d / "prs.json"

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def numbers(self, **kw):
        return [x["number"] for x in hb.open_prs("x", "/x", force=True, **kw)]

    def test_plain_list_misses_a_new_pr_add_finds_it(self):
        self.assertEqual(self.numbers(), [38])
        self.assertEqual(self.numbers(add=[39]), [39, 38])
        self.assertEqual([x["number"] for x in hb.cached_prs("x", "/x")[0]], [39, 38])

    def test_a_merged_or_closed_number_is_not_added(self):
        self.assertEqual(self.numbers(add=[40]), [38])

    def test_gone_drops_a_pr_the_list_still_shows(self):
        self.assertEqual(self.numbers(gone={38}), [])

    def test_row_shape(self):
        self.assertEqual(hb.pr_row(self.row(5)), {"number": 5, "title": "t5", "url": "u", "branch": "b5", "base": "main", "created": "2026-11-12T10:00:00Z"})


class Poller(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(hb, k) for k in ("cached_prs", "open_prs", "github_slug")}
        self.cache = {"a": ([{"number": 1}], 10, ""), "b": (None, 1e9, ""), "c": ([{"number": 3}], 1000, "")}
        hb.cached_prs = lambda name, path: self.cache[name]
        self.fetched = []
        hb.open_prs = lambda name, path, force=False: (self.fetched.append(name), [{"number": 9}])[1]
        hb.github_slug = lambda p: "o/r"
        self.refreshed = 0

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(hb, k, v)

    def menu(self):
        outer = self

        class M:
            projects = [{"name": "a", "path": "/a", "prs": None}, {"name": "b", "path": "/b", "prs": None}, {"name": "c", "path": "/c", "prs": None},
                        {"name": "nogit", "path": "/n", "prs": None, "slug": None}]
            run_worker = lambda s, fn, **k: (setattr(s, "group", k.get("group")), fn())
            call_from_thread = lambda s, f, *a: setattr(outer, "refreshed", outer.refreshed + 1)
            refresh_list = lambda s: None
            poll_prs = hb.Menu.poll_prs
        return M()

    def test_disk_only_reads_the_cache_and_never_calls_gh(self):
        m = self.menu()
        m.poll_prs(False)
        self.assertEqual(self.fetched, [])
        self.assertEqual([p["prs"] for p in m.projects], [[{"number": 1}], None, [{"number": 3}], None])      # b has never been fetched: left alone
        self.assertEqual((m.group, self.refreshed), ("prcache", 1))

    def test_fetch_refreshes_what_is_older_than_the_ttl(self):
        m = self.menu()
        m.poll_prs(True)
        self.assertEqual(self.fetched, ["b", "c"])                                   # a is fresh (10 s); b never fetched; c is 1000 s old
        self.assertEqual(m.projects[1]["prs"], [{"number": 9}])
        self.assertEqual(m.group, "prs")

    def test_no_change_no_refresh(self):
        m = self.menu()
        m.poll_prs(False)
        n = self.refreshed
        m.poll_prs(False)
        self.assertEqual(self.refreshed, n)


if __name__ == "__main__":
    unittest.main()
