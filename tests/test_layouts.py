"""Layouts come back whole: the hyperbeam session is saved too, and the program running in a pane is started again. Real tmux (the lab gives each run its
own server). Runs in the lab:
hyperbeam lab run --why "tests" -- uv run --quiet --with textual python3 -m unittest discover -s tests -v"""
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from common import hb


def wait(cond, secs=8):
    end = time.time() + secs
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.1)
    return False


def program_of(pane):
    return hb.pane_program(hb.tmux("display-message", "-p", "-t", pane, "#{pane_pid}").stdout.strip())


class Layouts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = {k: getattr(hb, k) for k in ("DATA_DIR", "known_path", "load_manifests", "menu_cmd", "claude_cmd", "session_path")}
        hb.DATA_DIR = self.tmp / "data"
        self.dev = self.tmp / "dev"
        self.dev.mkdir()
        hb.known_path = lambda n: self.dev
        hb.load_manifests = lambda: {}
        hb.menu_cmd = lambda: "sleep 300"
        hb.claude_cmd = lambda *a, **k: "echo claude-started"       # no real Claude here
        hb.session_path = lambda: "/usr/bin:/bin"
        hb.tmux("kill-server", check=False)

    def tearDown(self):
        hb.tmux("kill-server", check=False)
        for k, v in self.saved.items():
            setattr(hb, k, v)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def panes(self):
        return hb.tmux("list-panes", "-t", f"={hb.MENU}:home", "-F", "#{pane_id}", check=False).stdout.split()

    def test_hyperbeam_session_comes_back_with_its_panes_and_programs(self):
        hb.ensure_menu()
        first = self.panes()[0]
        hb.new_pane(["split-window", "-v", "-t", first, "-c", str(self.dev)])
        third = hb.new_pane(["split-window", "-h", "-t", first, "-c", str(self.dev)])
        hb.send_line(third, "sleep 777")
        self.assertTrue(wait(lambda: program_of(third) == "sleep 777"))
        self.assertTrue(hb.save_layout("hyperbeam"))
        lay = hb.load_layout("hyperbeam")
        self.assertEqual([w["name"] for w in lay["windows"]], ["home"])                   # the menu window is not saved
        self.assertEqual(sum(len(w["panes"]) for w in lay["windows"]), 4)
        self.assertEqual([p["prog"] for w in lay["windows"] for p in w["panes"] if p.get("prog")], ["sleep 777"])

        hb.tmux("kill-session", "-t", f"={hb.MENU}")                                       # the reboot
        hb.ensure_menu()
        names = hb.tmux("list-windows", "-t", f"={hb.MENU}", "-F", "#{window_name}").stdout.split()
        self.assertEqual(sorted(names), ["home", "menu"])
        panes = self.panes()
        self.assertEqual(len(panes), 4)
        self.assertTrue(wait(lambda: any(program_of(p) == "sleep 777" for p in panes)), "the program in the pane is started again")

    def test_no_saved_layout_gives_the_default(self):
        hb.ensure_menu()
        self.assertEqual(len(self.panes()), 2)

    def test_pane_program_skips_shells_and_sudo(self):
        for cmd, want in (("sleep 55", "sleep 55"), ("sudo -n -l", ""), ("bash -c 'sleep 56; true'", "")):
            hb.tmux("kill-server", check=False)
            pane = hb.new_pane(["new-session", "-d", "-s", "t", "-x", "80", "-y", "20"])
            hb.send_line(pane, cmd)
            time.sleep(0.6)
            self.assertEqual(program_of(pane), want, cmd)


if __name__ == "__main__":
    unittest.main()
