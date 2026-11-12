# Sidebar UI: constraints and what breaks at 35 columns

Made with `hyperbeam shot` (pictures of the real menu in a pty, rendered in the lab, brought back to `~/.cache/hyperbeam-shots/<time>/`; `--cols 35`, `--phone` = 42; `--screen main|pr|project|settings|merge|done`). Regenerate after every UI change and look at the PNGs. Findings below are from 35x40 and 42x40 runs on 2026-11-11 with 8 fixture projects (long names, a PR, a working and a waiting Claude).

## Constraints (design for these)
- **Width:** the laptop sidebar is `menu_width` columns, and the user wants **35**. The phone (Termux) shows roughly **42-46 columns** and loses about 4 rows to the key rows and keyboard. Anything that works at 35 works on the phone.
- **Input:** mostly mouse/touch and voice (RSI). Everything must be a visible button; keys are shortcuts only, never the only way.
- **Height:** the laptop sidebar is tall (48 rows), the phone is about 20-25 rows with the keyboard open. The list should not need blank space, and the buttons must stay reachable without scrolling.
- **One column of meaning:** a row is dot, name, branch, port. A name is never cut before the branch is.
- **Quiet by default:** colour carries state (dot colours, magenta = PR); text never carries a state that colour already shows.

## What breaks at 35 columns (ranked)
1. **FIXED (PR #27): Modals were 64 columns wide, so they were cut off.** Now `width: 100%; max-width: 64/84`, wrapped text, buttons stacked full width (checked with `hyperbeam shot --cols 35 --screen merge|done`). Was: `Confirm` and `Choice` (Merge, Done wrap-up, Stop, Restore layout) draw a 64-wide box into a 35-wide screen: the right border is gone, lines are cut mid-word (`1 commit not on any remot`, `Add the week view and fix the sc`) and the **Close (c)** button of the Done question is not visible at all (at 42 columns it is also cut: `Close (`). This is a real bug: a button the user needs cannot be seen or clicked.
2. **FIXED (PR #27): Settings hid two values.** Labels are shorter (`model`, `effort`, `width`, `recent`), so every value shows beside the - and + buttons at 35 columns. Was: At 35 columns the `open mode` and `claude model` rows show only `- +`: the label (14 columns) plus the value (`sidebar`, `opusplan`) does not fit before the buttons. At 42 they show. The key sheet below wraps to about 25 lines and its last line is cut.
3. **Buttons are a 2-column grid of 11 labels**, 6-7 rows: `Copy context (c)` loses `(c)`, `Mark as onboarded` becomes `Mark as`, and the grid leaves a blank row and an uneven last row. The buttons use more height than the project list they act on, and a project with an open PR adds Merge as the 11th.
4. **The Project screen wraps everything**: the path and branch go on separate lines, the open-PR title wraps, notes wrap; the buttons are pushed to the bottom with a big gap. It reads like a document, not a card.
5. **The notice line (2 rows) overlaps the action result**: `dotwork: checking PR #51 against main...` sits directly on the first button row with no gap; long results are cut.
6. **A PR's magenta branch on the selected (blue) row has weak contrast**, and a long branch pushes the name: `dotwork feature/week-vie… 3103`. The branch is the least useful column on a 35-column row.
7. **The title line `hyperbeam` and the empty rows between the list and the buttons waste height** on the phone (a tall empty gap at 40 rows); on the phone, rows are the scarce thing.
8. **Port column**: `unset` (orange) and `-` take 5 and 1 columns for information that is rarely needed; it competes with the name.

## Redesign directions (for the next prompt, not decided)
- Modals: width = `min(64, screen width - 2)`, wrapped text, buttons stacked vertically when they do not fit on one row; every modal's buttons always visible.
- Settings: one row = label on the first line, value + `-`/`+` on the second, or a list the user taps to cycle; the key sheet moves to its own screen ("Keys") reached by a button.
- Buttons: a short primary row (Open, Stop, Done) and a "More" screen (or the Project screen) for the rest; labels without the key hint at 35 columns (keys are shortcuts, shown in the Keys screen).
- Project screen as a card: name, branch, PR, notes as short lines (truncate with `...`, full text on tap/Info window); actions at the bottom.
- Rows: name first; branch only when it is not `main`/`master` (and only its first characters); port only when set.
- Test every change with `hyperbeam shot --cols 35` and `--phone`, and keep the PNGs out of git (they are in `~/.cache`).
