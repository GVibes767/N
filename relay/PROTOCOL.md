# GVM Relay Production RC 0.3

Target machine: `GVBSMEDIA`

## Transport

- Primary command queue: `GVibes767/N:relay/queue/<requestId>.json`
- Legacy fallback slot: `GVibes767/N:relay/command.json`
- Device reads commands through GitHub Git transport.
- Encrypted responses are published to:
  `mediagvibes-wq/gvm-relay:relay/responses/<requestId>.json`
- No inbound port on GVBSMEDIA is required.
- Adaptive local polling: 1.5 s idle; 0.5 s for 10 s after command/publish activity.
- Windows execution and Git subprocesses use no-window mode.

## Queue v2 dispatch protocol

Queue files are immutable command leases.

1. Generate a fresh requestId and one-time response key.
2. Create a new file at `relay/queue/<requestId>.json`; never overwrite an existing queue item.
3. The device fetches `origin/main`, skips expired items and requestIds already terminal in its local SQLite ledger.
4. The device executes up to 8 pending queue items per poll, sequentially.
5. Read the encrypted response from `relay/responses/<requestId>.json`.
6. After response receipt/decryption, delete the completed queue file from the command repository.
7. Completed queue items do not block newer work because terminal requestIds are skipped locally.
8. A malformed command is persisted as `rejected`, logged, and isolated; later commands continue.
9. A command lifetime is bounded; the device rejects expired commands and lifetimes over 30 minutes.

## Long-running process policy

- Synchronous `process.start` through the relay is limited to 45 seconds.
- Longer work must use `timeout=0` (detached) and expose completion through an artifact/readback.
- This prevents one long process from occupying the relay until a transport/client timeout.
- The guard is enforced before execution, so an invalid long synchronous request does not start the process.

## Legacy single-slot fallback

`relay/command.json` remains available only as a compatibility fallback.

1. Fetch the file and current blob SHA.
2. Write only when `state == "idle"`, using that exact SHA.
3. Never replace an unexpired requestId.
4. On HTTP 409/conflict, refetch and reevaluate; never blind-retry.
5. After a verified response, reset the same requestId back to `idle`.

## Encryption

1. Generate a random 32-byte command key and random 32-byte response key.
2. Payload JSON: `{"requestId","tool","arguments","responseKey"}`.
3. Encrypt payload with AES-256-GCM.
4. Command AAD: `gvm-relay:v1:command:GVBSMEDIA:<requestId>`.
5. Encrypt the command key with `device-public.pem` using RSA-OAEP SHA-256 / MGF1-SHA-256.
6. Envelope fields: `schemaVersion,target,requestId,expiresAt,wrappedKey,nonce,ciphertext`.
7. Response uses AES-256-GCM with the one-time response key.
8. Response AAD: `gvm-relay:v1:response:<requestId>`.

## Reliability and health

- GVM effect tools inherit the relay requestId.
- SQLite ledger makes completed effects idempotent.
- Executed responses are persisted before GitHub publication.
- Failed publication is retried without rerunning the effect.
- `published` and `rejected` requestIds are skipped on later polls.
- Response retention and logs are bounded.
- Hidden supervisor restarts a failed relay child with backoff.
- Orphan/adopt lock behavior prevents duplicate relay children.
- Startup uses `pythonw.exe` via `GVM Relay.lnk`; no cmd/PowerShell console is required.
- `relay-status.json` reports version, state, failures, effective poll delay, queue depth, and last fetch/command/publish timestamps.

## Safety and trust boundary

- Only GVM Connect's declared tool allowlist is callable.
- GVM Connect remains loopback-only on `127.0.0.1:8765`.
- Device private RSA material is DPAPI-protected and never stored in GitHub.
- The response deploy key is scoped only to `mediagvibes-wq/gvm-relay`.
- GitHub stores ciphertext only for command/response payloads.
- Sensitive local writes and high-risk process classes keep GVM approval checks.
- No public listener or inbound firewall rule is required.
- Command authenticity currently relies on write access to the command repository. Encryption provides confidentiality; repository write permissions are the authorization boundary.
- A separate sender-signing key is intentionally not claimed until there is a secure persistent sender-key workflow.

## Production RC verification gates

Verified:
- Queue-v2 `system.status` succeeds end to end.
- Effect tool execution succeeds with readback.
- Hidden process execution creates no visible console window.
- Supervisor restart path works.
- Malformed-item isolation was tested live: a deliberately invalid command did not block the valid command behind it.
- Long synchronous process guard was tested live: `timeout=46` was rejected before process execution.
- Relay unit regression: 12/12 PASS.
- GVM Connect regression: 9/9 PASS.
- Full workspace checks: `.ai/logs/checks-20260922T165257275Z.json` status `ok`.
- Final `system.status`: host `GVBSMEDIA`, `fullLocal=true`, `publicListener=false`.
- Startup shortcut target/arguments/working directory were verified.
- Hardening queue was cleaned.

Not automatically executed:
- Full Windows reboot/login acceptance, because it is disruptive to the user's active workstation.
