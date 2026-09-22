# GVM Relay MVP v2

Target machine: `GVBSMEDIA`

## Transport

- Primary command queue: `GVibes767/N:relay/queue/<requestId>.json`
- Legacy fallback slot: `GVibes767/N:relay/command.json`
- Device reads commands through GitHub Git transport.
- Encrypted responses are published to:
  `mediagvibes-wq/gvm-relay:relay/responses/<requestId>.json`
- No inbound port on GVBSMEDIA is required.
- Local polling target: ~1 second.
- Windows execution and Git subprocesses must use no-window mode.

## Queue v2 dispatch protocol

Queue files are immutable command leases.

1. Generate a fresh requestId and one-time response key.
2. Create a new file at `relay/queue/<requestId>.json`; never overwrite an existing queue item.
3. The device fetches `origin/main`, skips expired items and requestIds already marked `published` in its local SQLite ledger.
4. The device executes up to 8 pending queue items per poll, sequentially.
5. Read the encrypted response from `relay/responses/<requestId>.json`.
6. After response receipt/decryption, delete the completed queue file from the command repository.
7. If cleanup is delayed, completed queue items do not block newer work because the device skips published requestIds locally.
8. A command lifetime must be bounded; the device rejects expired commands and lifetimes over 30 minutes.

## Legacy single-slot fallback

`relay/command.json` remains available as a compatibility fallback.

1. Fetch the file and current blob SHA.
2. Write only when `state == "idle"`, using that exact SHA.
3. Never replace an unexpired requestId.
4. On HTTP 409/conflict, refetch and reevaluate; never blind-retry.
5. After a verified response, reset the same requestId back to `idle`.

Idle slot:

```json
{
  "schemaVersion": 1,
  "target": "GVBSMEDIA",
  "state": "idle"
}
```

## Encryption

1. Generate a random 32-byte command key and random 32-byte response key.
2. Payload JSON:
   `{"requestId","tool","arguments","responseKey"}`
3. Encrypt payload with AES-256-GCM.
4. Command AAD:
   `gvm-relay:v1:command:GVBSMEDIA:<requestId>`
5. Encrypt the command key with `device-public.pem` using RSA-OAEP with SHA-256 / MGF1-SHA-256.
6. Envelope fields:
   `schemaVersion,target,requestId,expiresAt,wrappedKey,nonce,ciphertext`
7. Response uses AES-256-GCM with the one-time response key.
8. Response AAD:
   `gvm-relay:v1:response:<requestId>`

## Reliability

- GVM effect tools inherit the relay requestId.
- The local SQLite ledger makes replay of completed effects idempotent.
- Executed responses are persisted before GitHub publication.
- Failed publication is retried from SQLite without rerunning the effect.
- Published queue items are skipped even if repository cleanup is delayed.
- Response-tree retention is bounded.
- Relay and supervisor logs are bounded.
- A hidden supervisor keeps one relay child alive and restarts it after failure.
- If an orphan relay already owns the relay lock, a new supervisor waits instead of spawning duplicates.
- Startup uses `pythonw.exe` through a Windows Startup shortcut; no cmd/PowerShell console is required.

## Safety and trust boundary

- Only GVM Connect's declared tool allowlist is callable.
- GVM Connect remains loopback-only on `127.0.0.1:8765`.
- Device private RSA material is DPAPI-protected and never stored in GitHub.
- The response deploy key is scoped only to `mediagvibes-wq/gvm-relay`.
- GitHub stores ciphertext only for command/response payloads.
- Sensitive local writes and high-risk process classes keep GVM approval checks.
- No public listener or inbound firewall rule is required.
- In MVP v2, command authenticity relies on write access to the command repository. Encryption provides confidentiality; repository write permissions are the authorization boundary. A separate command-signing key is future hardening, not claimed as implemented.

## MVP verification gates

A release is usable only when all are true:

- Queue-v2 `system.status` succeeds end to end.
- At least one effect tool succeeds with readback/verification.
- Hidden process execution creates no visible console window.
- Supervisor restart and orphan/adopt behavior are verified.
- GVM Connect live regression passes.
- Relay regression passes.
- Completed queue items are cleaned, and legacy slot is `idle`.
- Startup shortcut exists and launches the supervisor successfully.
