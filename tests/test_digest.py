"""The lab digest ranks by total time (count x duration), not by the single slowest run or by count. Runs with the rest of the suite (see CLAUDE.md, Testing)."""
import unittest

from common import hb


def run(cmd, seconds, minute, exit=0):
    return dict(time=f"2026-11-12T{10 + minute // 60:02d}:{minute % 60:02d}:00", project="p", cwd="/x", command=cmd, why="w", seconds=seconds, exit=exit, tail=[])


class Ranking(unittest.TestCase):
    def runs(self):
        out = [run("npm run big", 2700, 0)]                                        # one 45 minute run
        out += [run("npm run often", 900, 10 + i * 5) for i in range(6)]            # six 15 minute runs: 90 minutes
        out += [run("lint", 5, 50 + i) for i in range(3)]                          # cheap, repeated
        return out

    def test_six_runs_of_15_minutes_outrank_one_run_of_45(self):
        d = hb.lab_digest(self.runs())
        self.assertEqual([x["command"] for x in d["slow"]][:2], ["npm run often", "npm run big"])
        self.assertEqual(d["slow"][0]["total"], 5400)

    def test_the_single_long_run_is_not_a_candidate_but_the_repeated_one_is(self):
        d = hb.lab_digest(self.runs())
        self.assertEqual([c["what"] for c in d["candidates"]], ["npm run often"])    # needs 3+ runs and 30 s in total

    def test_candidates_mix_commands_and_sequences_by_total(self):
        runs = []
        for i in range(3):                                                          # two commands in a row, 3 times: 3 x (400 + 400)
            runs += [run("build", 400, i * 30), run("e2e", 400, i * 30 + 10)]
        runs += [run("unit", 20, 55 + i) for i in range(3)]                         # a command 3 times: 60 s
        d = hb.lab_digest(runs)
        totals = [c["total"] for c in d["candidates"]]
        self.assertEqual(totals, sorted(totals, reverse=True))
        self.assertEqual(d["candidates"][-1]["what"], "unit")
        self.assertTrue(any(c["kind"] == "sequence" for c in d["candidates"][:-1]))   # the sequences are bigger than the command and listed before it

    def test_summary_names_the_biggest_candidate(self):
        d = hb.lab_digest(self.runs())
        self.assertIn("npm run often", hb.digest_summary(d))

    def test_the_text_shows_total_average_and_longest(self):
        text = hb.format_digest(hb.lab_digest(self.runs()))
        self.assertIn("where the time went", text)
        self.assertIn("avg 15.0 min", text)
        self.assertIn("longest 45.0 min", text)


if __name__ == "__main__":
    unittest.main()
