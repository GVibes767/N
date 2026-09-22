# GVM Relay MVP Status

Status: **READY / MVP VERIFIED**

Target workstation: `GVBSMEDIA`

## Verified gates

- Queue v2 transport works end to end.
- Legacy `relay/command.json` remains idle fallback.
- Encrypted command/response transport works.
- Polling target is 1 second.
- `system.status` succeeds through relay.
- Effect tools succeed through GVM ledger/verifier.
- Hidden `process.start` uses no-window execution.
- `computer.screenshot` effect verification passed.
- Completed queue items are automatically cleaned.
- Local relay recovery/restart was verified.
- Detached launcher/supervisor was verified.
- Startup entry `GVM Relay.lnk` exists.
- Active relay components run under `pythonw.exe`.
- GVM Connect remains loopback-only at `127.0.0.1:8765`.
- No public listener or inbound firewall rule is required.
- GVM Connect and relay unit/live regression passed through queue v2.
- Obsolete OpenAI tunnel experiment was removed from the working path.

## Current runtime

- Relay protocol: `0.2.0-mvp`
- Transport: `github-queue-v2`
- Poll interval: `1.0s`
- Command repository: `GVibes767/N`
- Response repository: `mediagvibes-wq/gvm-relay`

## Trust boundary

Commands and responses are encrypted. GitHub stores ciphertext only.
Authorization in MVP relies on write access to the command repository.
Separate command-signing is recommended as post-MVP hardening.

## Post-MVP hardening

- Ed25519 command signing.
- Secondary fallback transport.
- Queue batching / latency optimization.
- Metrics and bounded retention dashboard.
- Optional cold-boot acceptance after a planned Windows reboot.
