# INVENTORY — ~/projects (2026-11-08)

Read-only survey. `git fetch` was run in every repo; nothing else was changed. No .env contents were read.
Verdicts: **runnable** (a start/test command works as documented) / **real but not runnable** (real work, no way to run it as-is) / **prune candidate**.

## Summary

| entry | git remote | last commit | unpushed / dirty | default port | verdict |
|---|---|---|---|---|---|
| algoviewz-decal-designer | github-algoviewz/algoviewz-decal-designer | 2026-06-29 | clean | 3000 (playwright 3200) | runnable |
| algoviewz-platform | github-algoviewz/algoviewz-platform | 2026-06-28 | clean, in sync (dev) | 3000 (playwright 3100), supabase db 54322 | runnable — **keep** |
| algoviewz-prod | same remote as platform | 2026-06-28 | 1 stash, local `dev` 23 behind, `main` 2 behind | 3000 | **prune candidate** (after saving its .env.local) |
| automatr | github-trifactoria/automatr | 2026-05-20 | clean, in sync (staging) | 3000, 8766, 5900, 6080 | real but not runnable |
| business-cards | none (not a repo) | files 2026-06-29 | not versioned | – | real but not runnable |
| data-organize | none | 2026-11-06 | all commits local only | – | real but not runnable |
| homesync | none | 2026-10-04 | all commits local only | – | runnable |
| hyperbeam | skillkraftz/hyperbeam | today | this PR | – | (new) |
| inkcut | inkcut/inkcut (upstream clone) | 2026-06-21 | clean, 18 behind upstream | – (desktop app) | runnable |
| moduponics | none | 2026-07-06 | 2 uncommitted (docs edit, untracked cad/); commits local only | – | real but not runnable |
| phone-dock | github-skillkraftz/phone-dock | 2026-11-08 | clean, in sync | – (adb 5037) | runnable |
| phone-dock.zip | – | 2026-11-08 | – | – | **prune candidate** |
| plantlab | github-trifactoria/plantlab | 2026-07-16 | clean, in sync (dev) | 3000 | runnable |
| pocketjournal | none (not a repo) | files 2026-11-02 | not versioned | 5173 (dotwork) | runnable |
| QR-sheets | none (not a repo) | files 2026-06-28 | not versioned | – | real but not runnable |
| resume-2026 | github.com:skillkraftz/resume-2026 | 2026-11-02 | clean, in sync | – | real but not runnable |
| scantailor-advanced | 4lex4/scantailor-advanced (upstream clone) | 2020-05-31 | untracked build/ (51 MB) | – (desktop app) | **prune candidate** |
| stenographr | github-skillkraftz/stenographr | 2026-11-08 | clean, in sync (feat/engine-and-clips) | – | runnable |
| storywheel | github-skillkraftz/storywheel | 2026-10-12 | clean, in sync; 7 stale local branches | grammar server 18081 (optional) | runnable |
| trifactoria-public | none (container of 6 repos) | 2026-06-01 newest repo | repos-cli: 1 uncommitted | 3000/3002/8765/8766 | see sub-entries |
| vevor-linux-cutter | github-trifactoria/vevor-cutter-linux | 2026-07-02 | **15 uncommitted** (README + calibration files) | – | real but not runnable |
| yt-search | none (not a repo) | files 2026-11-04 | not versioned | – | runnable |
| loose files in ~/projects | – | – | – | – | see "Loose files" |

## Entries

### algoviewz-decal-designer
- **What:** Next.js tool for designing vinyl decals (AlgoViewz).
- **Git:** `git@github-algoviewz:algoviewz/algoviewz-decal-designer.git`, main, 2026-06-29, clean and pushed.
- **Runs:** `pnpm dev` (3000). Tests: `pnpm test` (= typecheck + lint); e2e via `docker-compose.playwright.yml` (service `playwright`, image mcr.microsoft.com/playwright, app on 3200). Has CLAUDE.md and AGENTS.md.
- **Verdict:** runnable. Standard pnpm project; port 3000 clashes with others (give it a fixed port).

### algoviewz-platform
- **What:** Next.js App Router + TypeScript + Supabase MVP: local business pages, permanent QR codes, engagement tracking.
- **Git:** `git@github-algoviewz:algoviewz/algoviewz-platform.git`, on `dev` (e97bdd6), 2026-06-28, clean, in sync with origin/dev. `main` is 2 behind origin/main (PR #7 merge).
- **Runs:** `pnpm supabase:start` (Supabase CLI, local db on 54322), then `pnpm dev` (3000). Tests: `pnpm test` (typecheck + lint); `pnpm test:e2e`, `pnpm test:e2e:docker` (playwright container, app on 3100). Needs `.env.local` (exists; contents not read). CLAUDE.md and AGENTS.md present.
- **Verdict:** runnable. Whether the `supabase` CLI is installed was not checked.

### algoviewz-prod
- **What:** A second clone of the same repo as algoviewz-platform, checked out on `main`.
- **Git:** same remote. `main` 6afe026 (2 behind origin/main), local `dev` 49ef678 is 23 behind origin/dev with no unique commits. One stash (WIP on main: a 2-line .gitignore change). Tree clean.
- **Runs:** same as platform. Its `.env.local` is larger than platform's and `supabase/.temp/linked-project.json` differs, so it looks linked to a different (probably production) Supabase project.
- **Verdict:** prune candidate. All its commits are on origin; the only things unique to it are the stash and the local env/link files. See duplicates.

### automatr
- **What:** Browser-automation platform: FastAPI host API (8766), Next.js UI (3000), runtime containers (Xvfb, x11vnc 5900, noVNC 6080, Firefox), Caddy, XMPP experiment.
- **Git:** `git@github-trifactoria:trifactoria/automatr.git`, on `staging` (770bafe, 2026-05-20), clean, in sync. Branches dev/main/staging.
- **Runs:** No README or CLAUDE.md in this clone. `restart-all` hard-codes `cd /home/andy/Downloads/automatr2/` (stale path) and calls `./bin/build`; image from Dockerfile.runtime. The public clone's README documents `uvicorn app:app --host 127.0.0.1 --port 8766` and the UI on 127.0.0.1:3000.
- **Verdict:** real but not runnable as-is (stale path, no docs here). Local-only ignored dirs: certs/, config/, caddy/config, caddy/data.

### business-cards
- **What:** Business-card print/cut files and `bidnezcard.py`. 56 KB.
- **Git:** not a repo, not backed up. **Runs:** one-off script. **Verdict:** real but not runnable. Suggest `git init` or fold into an AlgoViewz repo.

### data-organize
- **What:** Read-only inspection of the Samsung T9 backup (`backup_t9`) to plan what goes in `/data`; output is `roster.md`.
- **Git:** no remote, branch master, last 2026-11-06, clean, nothing pushed. **Runs:** Python tools in `tools/` (classify, dedup_hash, categories). `seed.zip` (13 MB) next to `seed/`.
- **Verdict:** real but not runnable (one-shot analysis, not a service).

### homesync
- **What:** One bash script that syncs two Linux machines (xps and a Raspberry Pi "typewriter") over SSH + git. No services.
- **Git:** no remote, main, 2026-10-04, clean, never pushed. **Runs:** `homesync` on demand; tests in `tests/` with fake binaries.
- **Verdict:** runnable. Unpushed means the only copy is this disk.

### inkcut
- **What:** Upstream Inkcut: GUI for plotters, cutters, engravers.
- **Git:** `https://github.com/inkcut/inkcut.git`, master, 2026-06-21, clean, 18 behind upstream. Python 3.12 venv in `.venv` (uv).
- **Runs:** `.venv/bin/inkcut`. Used with vevor-linux-cutter.
- **Verdict:** runnable.

### moduponics
- **What:** Open-source modular hydroponic grow-rack system (docs + CAD).
- **Git:** no remote, main, 2026-07-06; uncommitted: docs/00_project_overview.md modified, `cad/` untracked. Never pushed. AGENTS.md, README.
- **Runs:** nothing to run. **Verdict:** real but not runnable. The untracked `cad/` is the most at-risk item here.

### phone-dock
- **What:** Plug in the Samsung: new camera files pulled over adb (md5-verified), scrcpy mirror, kitty menu.
- **Git:** `git@github-skillkraftz:skillkraftz/phone-dock.git`, main, 2026-11-08, clean, in sync.
- **Runs:** udev starts `phone-pull.service` (user systemd, linked from `systemd/`) which runs `bin/phone-session`. Tests: `bash tests/run-tests.sh` (offline). CLAUDE.md present.
- **Verdict:** runnable. Auto-starts on device plug-in, not on project open.

### phone-dock.zip
- **What:** 93 KB zip of the phone-dock tree (89 files), made 2026-11-08, presumably to move it to another machine.
- **Verdict:** prune candidate. The repo is pushed and identical in purpose.

### plantlab
- **What:** Local-first experiment tracking for biological projects (plants, breeding, mycology); Next.js + Prisma (sqlite) + an edge agent.
- **Git:** `git@github-trifactoria:trifactoria/plantlab.git`, dev, 2026-07-16, clean, in sync.
- **Runs:** `pnpm dev` (3000); `pnpm typecheck`, `pnpm test:unit` (vitest), `pnpm test:e2e` (playwright); `pnpm db:push|generate|migrate`; `bin/plantlab` CLI (`plantlab install`, `node attach`) which writes `plantlab-agent.service` (user systemd). `.env`, `.env.local` exist. CLAUDE.md + AGENTS.md.
- **Verdict:** runnable. Dev server and agent may share the sqlite file.

### pocketjournal
- **What:** Two sub-projects: `dotwork` (Vite + TypeScript app, 153 MB with node_modules/dist) and `journal-system` (Python: print-ready PDFs for a hand-bound pocket notebook, 100 MB).
- **Git:** not a repo, not backed up. Files last touched 2026-11-02.
- **Runs:** dotwork: `npm run dev` (vite, 5173), `npm test` (vitest), `npm run build`. journal-system: `pip install -e '.[dev]'`, `python -m pocketjournal`. Each has CLAUDE.md/README.
- **Verdict:** runnable, but unversioned. Highest "no backup" risk after moduponics.

### QR-sheets
- **What:** Generated HPGL/SVG cut sheets and `make-qr-final.py`. 352 KB.
- **Git:** not a repo. **Verdict:** real but not runnable (outputs of the QR/decal work).

### resume-2026
- **What:** Resume and job-search materials (goal: remote engineering role).
- **Git:** `git@github.com:skillkraftz/resume-2026.git`, main, 2026-11-02, clean, in sync. Contains `jobs14.zip`.
- **Verdict:** real but not runnable (documents; nothing to start).

### scantailor-advanced
- **What:** Upstream ScanTailor Advanced (C++/CMake).
- **Git:** `https://github.com/4lex4/scantailor-advanced.git`, master, last commit 2020-05-31, only `build/` untracked (51 MB). A `scantailor` is on PATH at /usr/local/bin and the build dir has its own binary.
- **Verdict:** prune candidate. Clone of an upstream project with no local commits. Keep only if /usr/local/bin/scantailor was installed from this build (not checked).

### stenographr
- **What:** Local speech-to-text (Parakeet TDT 0.6B via sherpa-onnx); `stenographr clip|srt`.
- **Git:** `git@github-skillkraftz:skillkraftz/stenographr.git`, on `feat/engine-and-clips` (also `main`), 2026-11-08, clean, in sync.
- **Runs:** `uv tool install --editable .` (CPU) or `".[gpu]"`; tests `bash tests/run-tests.sh` (offline, fake engine). CLAUDE.md present. Chooses GPU or CPU per file (busy-process aware).
- **Verdict:** runnable.

### storywheel
- **What:** Personal full-screen terminal writing program, from idea to manuscript.
- **Git:** `git@github-skillkraftz:skillkraftz/storywheel.git`, main, 2026-10-12, clean, in sync. Local branches: batch-20..24, polish-1, stable (stale, not checked for unmerged work).
- **Runs:** `./install.sh` or `pipx install --editable .`, then `storywheel`; tests `./.venv/bin/python -m pytest -m "not slow"` (use temp dirs; never touch ~/.storywheel). Optional LanguageTool grammar server on 18081. CLAUDE.md present.
- **Verdict:** runnable.

### trifactoria-public (container, not a repo)
Six independent clones, 438 MB total (373 MB of it is one zip):

| sub-entry | remote | last commit | state | run | verdict |
|---|---|---|---|---|---|
| automatr | trifactoria/automatr | 2026-05-24 (main 3a20e7e) | clean, in sync | README: `uvicorn app:app --port 8766`, UI 3000 | duplicate of ~/projects/automatr |
| midi-mapper | trifactoria/midi-mapper | 2026-06-01 | clean | `scripts/dev-desktop.sh` (needs cargo; Tauri-style), docs mention 8765 | runnable if Rust installed |
| repos-cli | trifactoria/repos-cli | 2026-05-25 | **1 uncommitted** | Python package `pip install repos-cli` | runnable |
| repos-landing | trifactoria/repos-landing | 2026-05-25 | clean | `pnpm dev` (3000) | runnable |
| skillkraftz-site | skillkraftz/skillkraftz-llc | 2026-05-25 | clean | `pnpm dev` (3000) | runnable |
| trifactoria-landing | trifactoria/trifactoria-landing | 2026-05-24 | clean | `npm run dev` (3000) | runnable |
| midi-mapper-before-claude.zip | – | – | 373 MB | – | **prune candidate** (backup snapshot of a repo that is on GitHub) |
Also `PUBLIC_PORTFOLIO_AUDIT.md`. The container has no CLAUDE.md. hyperbeam will need to treat each sub-repo as its own project, or exclude the folder.

### vevor-linux-cutter
- **What:** Linux setup notes and tools for a VEVOR SK720T USB vinyl cutter via Inkcut/HPGL (native USB HPGL sender, install scripts, Inkcut patches).
- **Git:** `github-trifactoria:trifactoria/vevor-cutter-linux.git`, main, 2026-07-02, in sync with origin but **15 modified files** (README + calibration HPGL/SVG).
- **Runs:** `scripts/install.sh`, `scripts/build-vevor-cut.sh`, `scripts/check-install.sh`; no long-running process.
- **Verdict:** real but not runnable on its own (hardware-dependent tooling). Commit or discard the 15 changes.

### yt-search
- **What:** Searches YouTube for a list of books/people/podcasts and writes a report of the best English videos.
- **Git:** not a repo. In-repo `.venv` (Python 3.14), `test_yt_search_rank.py`.
- **Runs:** `./Start\ YouTube\ Search.sh` (also .command/.bat). **Verdict:** runnable, unversioned.

### Loose files in ~/projects (not directories)
AlgoViewz logo/brand PNG+SVG variants (about 14 files), QR SVGs (`QR sheet.svg`, `QR-test.svg`, `my-qr-primary.svg`, `figgy*.svg`), `master_12x12_decal_template.svg`, `test.svg`, `test_sheet.svg`, scripts `generate_decal_template.py`, `send-cutter-usb.py`, `send-vevor-hpgl.py`, `generate-algoviewz-brand-assets.sh`, `fix_repo.sh`.
- **Verdict:** real but not runnable as projects; hyperbeam's picker should ignore non-directories. The `fix_repo.sh` also exists inside automatr (same name; contents not compared). `my-qr-primary.svg` also appears in business-cards.

## Duplicates

**algoviewz-platform vs algoviewz-prod (same repo, two clones).** Neither has commits the other lacks that are not on origin. platform is on `dev` = origin/dev; prod is on `main` 2 behind origin/main, with a stale local `dev` 23 behind. prod has one stash (a 2-line .gitignore change) and a different, larger `.env.local` and Supabase link. platform has ignored extras (`.claude/`, `.agents/`, `skills-lock.json`, `supabase/snippets`). **Keep algoviewz-platform.** Before deleting prod: save its `.env.local` and `supabase/.temp` link somewhere safe if it targets production, and apply or drop the stash.

**automatr vs trifactoria-public/automatr (same remote).** The public clone is on `main` 3a20e7e = origin/main (README, requirements.txt, .github, lint fixes, 2 commits the other lacks). ~/projects/automatr is on `staging` 770bafe, which has 1 commit (secret/artifact cleanup) not on main, and holds ignored local runtime state (certs/, config/, caddy data, .bak files) plus a stale `restart-all`. **Keep ~/projects/automatr** (it is where hyperbeam looks and holds the local state), but check out and pull `main` first; the staging commit is on origin so nothing is lost. Prune trifactoria-public/automatr (fully pushed, re-clonable). This is a judgment call: if the ignored certs/config are not needed, either clone could go.

**Other pairs spotted:**
- phone-dock vs phone-dock.zip: keep the repo, prune the zip.
- trifactoria-public/midi-mapper vs midi-mapper-before-claude.zip: keep the repo, prune the zip (373 MB).
- data-organize/seed vs seed.zip, algoviewz-decal-designer vs print-studio-2.zip, resume-2026/jobs14.zip: zips beside extracted data; not compared. Keep unless confirmed redundant.
- inkcut and vevor-linux-cutter are related (the latter patches the former) but not duplicates.

## Prune list
1. `algoviewz-prod` (after saving `.env.local`/Supabase link and handling the stash)
2. `trifactoria-public/automatr` (keep ~/projects/automatr)
3. `phone-dock.zip`
4. `trifactoria-public/midi-mapper-before-claude.zip` (373 MB)
5. `scantailor-advanced` (unless /usr/local/bin/scantailor depends on its build/)

Not prune, but needs attention: pocketjournal, yt-search, business-cards, QR-sheets (no git); homesync, moduponics, data-organize (no remote); vevor-linux-cutter (15 uncommitted); repos-cli (1 uncommitted); storywheel stale branches.

## Findings

1. **Which tmux config loads.** tmux 3.6 reads `/etc/tmux.conf`, `~/.tmux.conf`, `$XDG_CONFIG_HOME/tmux/tmux.conf`, `~/.config/tmux/tmux.conf` (from the binary's own strings). `~/.config/tmux/tmux.conf` (4 KB, Dec 2025) exists and is the one used. The earlier scan only tested `~/.tmux.conf`, so it wrongly reported "none". Its settings: prefix C-a, mouse off with an Alt+` toggle, vi mode-keys, `v`/`y` copy (to the tmux buffer only; the wl-copy line is commented out), escape-time 0, history 5000, dark theme, status bar with session name. `set-clipboard` is not set, so tmux's default (`external`) applies.
2. **TERM and truecolor.** The shell Claude Code runs in is not inside kitty (`KITTY_WINDOW_ID` empty, `TERM=xterm-256color`, `COLORTERM=truecolor`), so it says nothing about kitty. There is no `~/.config/kitty/kitty.conf`, so kitty uses its default `TERM=xterm-kitty` (terminfo installed). A throwaway tmux server on a separate socket, attached with `TERM=xterm-kitty`, reported client features `bpaste,ccolour,clipboard,cstyle,focus,RGB,title`. So **truecolor is active in tmux under kitty**; tmux gets RGB from xterm-kitty's `Tc/setrgbf` terminfo capabilities. The conf's `xterm-256color:RGB` line does not apply to kitty; it covers terminals that report `xterm-256color` (likely Termux). I did not test inside a real interactive kitty window or Termux.
3. **Tools.** fzf **missing**. kitty, tmux 3.6 and wl-copy are installed (`/usr/bin`); gh is also present, logged in as skillkraftz and trifactoria. The picker will need `sudo apt install fzf` (not done).

## Could not determine
- Whether the `supabase` CLI is installed, and the docker daemon state.
- Whether `/usr/local/bin/scantailor` came from `scantailor-advanced/build`.
- Contents of any .env file (deliberately not read); whether prod's `.env.local` holds production keys (inferred from size and the differing Supabase link only).
- Whether the stale storywheel branches hold unmerged work; whether the loose zips are redundant.
- Port 33525's owner (from the earlier scan).
