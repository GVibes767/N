# GVM Relay

Free encrypted command channel for the GVBSMEDIA workstation.

- Primary queue: `relay/queue/<requestId>.json`
- Legacy fallback slot: `relay/command.json`
- Device public key: `relay/device-public.pem`
- Protocol: `relay/PROTOCOL.md`
- Encrypted responses:
  `mediagvibes-wq/gvm-relay/relay/responses/<requestId>.json`

The Windows agent only calls tools explicitly exposed by GVM Connect.
Commands and responses are encrypted; GitHub does not store plaintext payloads.
The relay uses a hidden `pythonw` supervisor and requires no inbound port on the workstation.
