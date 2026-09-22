# GVM Relay

Free encrypted command channel for the GVBSMEDIA workstation.

## Status

**MVP v2 accepted on 2026-09-22.**

Verified gates:
- Queue-v2 end-to-end command delivery.
- Read-only and effect-tool execution with readback.
- Hidden Windows process execution without console windows.
- Supervisor/restart path.
- GVM Connect regression.
- Relay regression.
- Completed queue cleanup.
- Legacy command slot returned to `idle`.

RDC is no longer the primary runtime path. It remains only as an emergency bootstrap/fallback while GVM Relay is maintained.

## Transport

- Primary queue: `relay/queue/<requestId>.json`
- Legacy fallback slot: `relay/command.json`
- Device public key: `relay/device-public.pem`
- Protocol: `relay/PROTOCOL.md`
- Encrypted responses:
  `mediagvibes-wq/gvm-relay/relay/responses/<requestId>.json`

The Windows agent only calls tools explicitly exposed by GVM Connect.
Commands and responses are encrypted; GitHub does not store plaintext payloads.
The relay uses a hidden `pythonw` supervisor and requires no inbound port on the workstation.
