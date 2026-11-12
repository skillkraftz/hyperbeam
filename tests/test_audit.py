"""`hyperbeam audit`: the whole-project audit starts a fresh plan-mode Claude from AUDIT.md, a few facts about the project's size and the snapshot.
Runs in the lab: hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import contextlib
import io
import subprocess
import types
from pathlib import Path

from common import hb
from test_start import Base


class Audit(Base):
    def setUp(self):
        super().setUp()
        self.saved_audit = {k: getattr(hb, k) for k in ("known_path",)}
        subprocess.run(["git", "init", "-q", str(self.proj)], check=True)
        (self.proj / "big.py").write_text("x = 1\n" * 50)
        (self.proj / "small.md").write_text("hi\n")
        subprocess.run(["git", "-C", str(self.proj), "add", "."], check=True)

    def test_text_has_the_prompt_the_facts_and_the_snapshot(self):
        t = hb.audit_text("proj", self.proj)
        self.assertTrue(t.startswith("# Audit the whole project"))
        for want in ("Project: proj", "Tracked files: 2", "big.py (50)", "SNAPSHOT"):
            self.assertIn(want, t)
        self.assertLess(t.index("big.py (50)"), t.index("small.md (1)"))                       # largest first

    def test_the_prompt_has_the_five_steps_and_the_stop_rule(self):
        t = (hb.HERE / "AUDIT.md").read_text()
        for want in ("## Step 1: Read and list", "## Step 2: Triage", "## Step 3: Write the findings down", "## Step 4: Fix, in small PRs", "## Step 5: Close",
                     "Looked at and fine", "Audit done."):
            self.assertIn(want, t)

    def test_start_swaps_in_a_fresh_plan_claude_with_the_audit_prompt(self):
        seen = []
        hb.swap_claude = lambda name, path, f, why, dirs=(): (seen.append((name, why, Path(f).read_text(), list(dirs))), (True, "a fresh Claude in plan mode"))[1]
        ok, msg = hb.start_audit("proj", self.proj)
        self.assertTrue(ok)
        name, why, text, dirs = seen[0]
        self.assertEqual((name, why, dirs), ("proj", "audit", []))
        self.assertTrue(text.startswith(hb.PLAN_FIRST))
        self.assertIn("# Audit the whole project", text)

    def test_the_command_prints_or_starts(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(hb.cmd_audit(types.SimpleNamespace(project="proj", print=True)), 0)
        self.assertIn("# Audit the whole project", out.getvalue())
        hb.swap_claude = lambda *a, **k: (False, "proj is not running: open it, then ask again")
        with contextlib.redirect_stdout(out):
            self.assertEqual(hb.cmd_audit(types.SimpleNamespace(project="proj", print=False)), 1)
