# GVM Relay

Free encrypted command channel for the GVBSMEDIA workstation.

- Command slot: `relay/command.json`
- Device public key: `relay/device-public.pem`
- Protocol: `relay/PROTOCOL.md`
- Encrypted responses:
  `mediagvibes-wq/gvm-relay/relay/responses/<requestId>.json`

The Windows agent only calls tools explicitly exposed by GVM Connect.
Commands and responses are encrypted; GitHub never contains the plaintext payload.
