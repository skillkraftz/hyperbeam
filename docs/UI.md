# Sidebar UI: constraints and what breaks at 35 columns

Made with `hyperbeam shot` (pictures of the real menu in a pty, rendered in the lab, brought back to `~/.cache/hyperbeam-shots/<time>/`; `--cols 35`, `--phone` = 42; `--screen main|pr|project|settings|merge|done`). Regenerate after every UI change and look at the PNGs. Findings below are from 35x40 and 42x40 runs on 2026-11-11 with 8 fixture projects (long names, a PR, a working and a waiting Claude).

## Constraints (design for these)
- **Width:** the laptop sidebar is `menu_width` columns, and the user wants **35**. The phone (Termux) shows roughly **42-46 columns** and loses about 4 rows to the key rows and keyboard. Anything that works at 35 works on the phone.
- **Input:** mostly mouse/touch and voice (RSI). Everything must be a visible button; keys are shortcuts only, never the only way.
- **Height:** the laptop sidebar is tall (48 rows), the phone is about 20-25 rows with the keyboard open. The list should not need blank space, and the buttons must stay reachable without scrolling.
- **One column of meaning:** a row is dot, name, branch, port. A name is never cut before the branch is.
- **Quiet by default:** colour carries state (dot colours, magenta = PR); text never carries a state that colour already shows.

## Status at 35 columns (after PR #28; pictures from `hyperbeam shot --cols 35`)
Fixed: modals fit with stacked buttons; Settings shows every value (and is only the six settings: the key sheet is its own Keys screen); the main button area is Open, Stop, Done, Update, More (Hide in the sidebar), with Merge/Fix full width only when they apply, and no key hints at 35 columns; the Project screen is a card of short lines cut with an ellipsis, with the verbs, Settings, Keys and Hide as buttons; rows show the branch only when it is not main/master and the port only when set (PR branch in light pink, readable on the blue selected row); the notice has a blank line above the buttons and is wrapped to two lines; the title line carries `update available (u)` or the 5-hour window.
Still open: the `[green] running` detail line and the notice both live under the list (two kinds of text in one place); the Project screen is a modal that hides the list; long PR titles are cut at about 30 characters; the sidebar has no scroll hint when there are more rows than fit; phone width (42 columns) is checked by `--phone` but not tuned.

## Redesign directions that remain
- One status area instead of detail line + notice; a thin separator before the buttons.
- Project screen as a half-height panel so the list stays visible.
- Look at `--phone` pictures with the keyboard height removed (about 20 rows) and trim rows accordingly.
- Test every change with `hyperbeam shot --cols 35` and `--phone`; the PNGs stay in `~/.cache`.
