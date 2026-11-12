---
id: 2026-11-11-settings-in-config-hyperbeam-config-toml
status: implemented
prs: [12]
topic: install
---
# Settings in `~/.config/hyperbeam/config.toml`, defaults in the repo

- **Decision:** user settings are written to the user's file and laid over `config.default.toml`; hyperbeam never writes into the repo.
- **Why:** the Settings screen used to dirty the checkout, which blocks `hyperbeam update`.
