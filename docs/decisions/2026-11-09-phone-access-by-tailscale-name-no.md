---
id: 2026-11-09-phone-access-by-tailscale-name-no
status: implemented
prs: [4]
topic: unsorted
---
# Phone access by Tailscale name, no tunnels

- **Decision:** dev servers bind all interfaces (set in each manifest, never in the project) and the phone uses `http://<MagicDNS name>:<port>`.
- **Why:** simplest; no tunnels to run. Vite needs `--host` and an allowed-hosts variable.
