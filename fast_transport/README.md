# GVM Fast Transport v1

Fast notification/dispatch layer for the existing encrypted GVM GitHub Relay.

## Goal

Keep GitHub Queue v2 as the authorization, audit and fallback path, but remove local polling from the critical path:

```
ChatGPT -> GitHub queue commit
              |
              +-> GitHub webhook -> Helsinki VPS -> persistent WSS -> GVBSMEDIA
              |
              +-> existing Git polling fallback
```

The command envelope remains encrypted exactly as in GVM Relay Production RC 0.3.
The VPS never receives plaintext tool arguments.

## Security

- VPS webhook accepts only GitHub `push` events with a valid `X-Hub-Signature-256` HMAC.
- Repository and branch are pinned to `GVibes767/N` and `main`.
- Device uses a separate random bearer token for its outbound WebSocket.
- VPS forwards the existing encrypted envelope; decryption still happens only on GVBSMEDIA.
- Existing SQLite idempotency makes duplicate delivery from WebSocket + Git fallback safe.
- Existing GitHub polling remains fallback and authoritative recovery.
- No inbound port is opened on GVBSMEDIA.

## VPS process

The Python service listens on loopback `127.0.0.1:8789`.
TLS/WSS should be terminated by the VPS's existing reverse proxy; do not replace existing VPN/site configuration.

Endpoints:

- `GET /health`
- `GET /v1/device/ws?device=GVBSMEDIA`
- `POST /v1/github/webhook`

Required environment:

```
GVM_GITHUB_WEBHOOK_SECRET=<random 32+ bytes>
GVM_DEVICE_TOKEN=<random 32+ bytes>
GVM_COMMAND_REPO=GVibes767/N
GVM_TARGET_DEVICE=GVBSMEDIA
GVM_FAST_HOST=127.0.0.1
GVM_FAST_PORT=8789
```

## Local client integration

The Windows client will:

1. start hidden with `pythonw.exe`;
2. maintain one outbound WSS connection to the VPS;
3. authenticate with the device token stored locally using Windows DPAPI;
4. on a `command` message, base64-decode the envelope and call the existing
   `github_relay.handle(raw)`;
5. rely on the existing response publisher / SQLite ledger;
6. reconnect with bounded exponential backoff;
7. leave Git polling running as fallback.

## Acceptance targets

- no console windows;
- no inbound Windows firewall rule;
- WSS reconnect after network loss;
- invalid webhook signature rejected;
- duplicate WebSocket/Git delivery executes an effect once;
- WebSocket delivery reaches GVBSMEDIA faster than the 1.5 s idle poll path;
- disabling Fast Transport leaves GitHub Relay fully functional.

Deployment is intentionally additive; do not remove the Production RC Git transport.
