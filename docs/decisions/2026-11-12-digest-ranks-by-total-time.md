---
id: 2026-11-12-digest-ranks-by-total-time
status: implemented
prs: [47]
topic: lab
---
# The lab digest ranks by total time (count x duration)

- **Decision:** "slowest" became "where the time went": the top 5 commands by total time, each with count, average and longest run. The tool candidates (repeated commands and sequences) are one list sorted by total, so the biggest cost is first and `digest_summary` names it. `hyperbeam lab log` lists repeats by total minutes, not by count. TOOLS_PROPOSE.md tells Claude to start from the top of both lists.
- **Why:** the user wants the work that costs the most to bubble up: six 15-minute runs (90 min) matter more than one 45-minute run, and what keeps climbing the list is what to speed up, parallelise or turn into a tool. The old "slowest" list was ordered by the single longest run, and the candidates listed all commands before all sequences, so a 9-minute sequence sat under a 42-second command.
- **Rejected:** weighting by count or by failures (more knobs, no clear need yet); letting one-off long runs be tool candidates (they still show in "where the time went", but a tool needs repeated work); a score combining time and frequency (total time already is that product).
