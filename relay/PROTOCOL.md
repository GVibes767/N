# GVM Relay MVP v1

Target machine: `GVBSMEDIA`

## Transport

- Command slot: `GVibes767/N:relay/command.json`
- Device reads the command through GitHub Git transport.
- Encrypted responses are published to:
  `mediagvibes-wq/gvm-relay:relay/responses/<requestId>.json`
- No inbound port on GVBSMEDIA is required.
- Local polling target: ~1 second.
- Windows execution and Git subprocesses must use no-window mode.

## Dispatch / lease protocol

The command file is a single leased slot. Never blindly overwrite it.

1. Fetch `relay/command.json` and its current blob SHA.
2. If `state == "idle"`, a new command may be written using that exact SHA.
3. If an unexpired `requestId` is present, do not replace it.
4. First check `relay/responses/<requestId>.json`.
5. After receiving/decrypting the response, refetch the slot and reset it to `idle`
   only when the same requestId is still present.
6. On GitHub HTTP 409/conflict, refetch the slot and reevaluate; never blind-retry a write.
7. Every new command uses a fresh requestId and one-time response key.
8. Keep command lifetime bounded; the device rejects expired commands and lifetimes over 30 minutes.

Idle slot:

```json
{
  "schemaVersion": 1,
  "target": "GVBSMEDIA",
  "state": "idle"
}
```

## Encryption

1. Generate a random 32-byte command key and a random 32-byte response key.
2. Payload JSON:
   `{"requestId","tool","arguments","responseKey"}`
3. Encrypt payload with AES-256-GCM.
4. AAD:
   `gvm-relay:v1:command:GVBSMEDIA:<requestId>`
5. Encrypt the command key with the public key in `device-public.pem`,
   RSA-OAEP with SHA-256 / MGF1-SHA-256.
6. Envelope fields:
   `schemaVersion,target,requestId,expiresAt,wrappedKey,nonce,ciphertext`
7. Response uses AES-256-GCM with the one-time response key.
8. Response AAD:
   `gvm-relay:v1:response:<requestId>`

## Reliability

- GVM effect tools inherit the relay requestId.
- The local SQLite ledger makes replay of an already-completed effect idempotent.
- An executed response is persisted before GitHub publication.
- If publication fails, the agent retries delivery from SQLite without re-running the effect.
- Response working tree retention is bounded; old response files are pruned from the current tree.
- Relay status is written locally and log size is bounded.
- A hidden launcher is the intended autostart entry and must not use cmd/PowerShell windows.

## Safety

- Only GVM Connect's declared tool allowlist is callable.
- GVM Connect remains loopback-only on `127.0.0.1:8765`.
- Device private RSA material is DPAPI-protected and never stored in GitHub.
- The response deploy key is scoped only to `mediagvibes-wq/gvm-relay`.
- GitHub stores ciphertext only for commands/responses.
- Sensitive local writes and high-risk process classes keep GVM's approval checks.
- No public listener or inbound firewall rule is required.

## MVP verification gates

A release is considered usable only when all are true:

- `system.status` succeeds through the relay.
- At least one effect tool succeeds with readback/verification.
- Hidden process execution creates no visible console window.
- GVM Connect live regression passes.
- Relay regression passes.
- Command slot returns to `idle`.
- Autostart entry exists and launcher/relay syntax checks pass.
