# GVM Relay v1

Target machine: `GVBSMEDIA`

## Transport

- Command slot: `GVibes767/N:relay/command.json`
- Device reads the command through GitHub Git transport.
- Encrypted responses are published to:
  `mediagvibes-wq/gvm-relay:relay/responses/<requestId>.json`
- No inbound port on GVBSMEDIA is required.

## Encryption

1. Generate a random 32-byte command key and a random 32-byte response key.
2. Payload JSON:
   `{"requestId","tool","arguments","responseKey"}`
3. Encrypt payload with AES-256-GCM.
4. AAD:
   `gvm-relay:v1:command:GVBSMEDIA:<requestId>`
5. Encrypt the command key with the public key in `device-public.pem`,
   RSA-OAEP with SHA-256 / MGF1-SHA-256.
6. command.json envelope fields:
   `schemaVersion,target,requestId,expiresAt,wrappedKey,nonce,ciphertext`
7. Response is AES-256-GCM using the one-time response key.
8. Response AAD:
   `gvm-relay:v1:response:<requestId>`

## Safety

- Commands expire; the agent rejects expired or excessive lifetimes.
- Only GVM Connect's declared tool allowlist is callable.
- Effect tools inherit the relay requestId, so GVM's SQLite ledger provides idempotency.
- Device private RSA material is DPAPI-protected and never stored in GitHub.
- The response deploy key is scoped only to `mediagvibes-wq/gvm-relay`.
- GitHub contains ciphertext only for commands/responses.
