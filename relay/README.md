# GVM Relay

Free encrypted command channel for the GVBSMEDIA workstation.

## Status

**Production RC 0.3.0 accepted locally on 2026-09-22.**

Verified:
- Queue-v2 end-to-end command delivery.
- Read-only and effect-tool execution with readback.
- Hidden Windows process execution without console windows.
- Hidden pythonw supervisor and automatic relay-child restart.
- Adaptive polling: 1.5 s idle / 0.5 s for 10 s after activity.
- Health telemetry in `E:\AppCaches\GVMRelay\relay-status.json`.
- Malformed queue-item isolation: rejected commands no longer block later work.
- Long synchronous process protection: >45 s must use detached execution + artifact/readback.
- Relay regression 12/12 PASS; GVM Connect regression 9/9 PASS.
- Full workspace checks report `.ai/logs/checks-20260922T165257275Z.json` has `status: ok`.
- Final health: `GVBSMEDIA`, `fullLocal=true`, `publicListener=false`.
- Completed hardening queue items were cleaned.
- Legacy command slot is retained only as a fallback.

RDC is no longer the primary runtime path. It is an emergency bootstrap/diagnostic fallback.

## Transport

- Primary queue: `relay/queue/<requestId>.json`
- Legacy fallback slot: `relay/command.json`
- Device public key: `relay/device-public.pem`
- Protocol: `relay/PROTOCOL.md`
- Encrypted responses:
  `mediagvibes-wq/gvm-relay:relay/responses/<requestId>.json`

The Windows agent only calls tools explicitly exposed by GVM Connect.
Commands and responses are encrypted; GitHub does not store plaintext payloads.
The relay uses a hidden `pythonw` supervisor and requires no inbound port on the workstation.

A full Windows reboot/login acceptance is intentionally not performed automatically because it interrupts the user's workstation. The Startup shortcut itself and live supervisor restart path are verified.
