---
id: 2026-11-12-one-click-to-ship-and-update
status: implemented
prs: [28]
topic: unsorted
---
# One click to ship and update: standard verbs, Merge then update, a sidebar that fits, usage windows

- **Decision:** every project gets the same verbs (`hyperbeam NAME install|update|test|version|help|restart`), derived from its lockfile unless the project defines them; the project's name plus `update` is all the user needs to remember, and after Merge the project's update runs by itself. The sidebar is rebuilt for 35 columns: Open, Stop, Done, Update, More (and Merge/Fix only when they apply), rows with only the information that matters, a card-style Project screen, Settings without the key sheet (Keys is its own screen). `hyperbeam usage` shows the 5-hour windows from Claude's own conversation files (the reset time is exact, a percentage only once the limit can be estimated). Done leaves running any project whose Claude is working or waiting.
- **Why:** the user wants to click Merge and be done; handing over work in small pieces and asking for rituals (a verify merge, a manual update) cost more time than the work. Prototypes that become projects lack the common verbs exactly when they need them. The cost of a window is context size times requests, so the user needs to see the window, not guess it. Git-clean is not the same as finished.
- **Rejected:** a verb DSL (manifest `[commands]` only overrides); updating projects without a lockfile check (installs every time are slow); a percentage from one limit hit; closing the sidebar while any Claude is busy.
