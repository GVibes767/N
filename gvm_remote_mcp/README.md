# GVM Remote MCP

Remote MCP facade for ChatGPT -> GitHub Queue v2 -> Fast Transport -> GVBSMEDIA -> GVM Connect -> Production Runtime.

## Runtime path

```
ChatGPT custom MCP app
  -> /mcp
  -> encrypted queue item in GVibes767/N
  -> GitHub push webhook
  -> GVM Fast Transport
  -> GVBSMEDIA
  -> GVM Connect / Production Runtime
  -> encrypted response in mediagvibes-wq/gvm-relay
  -> MCP response to ChatGPT
```

GitHub Relay remains the fallback if Fast Transport delivery is unavailable. The server never stores the device private key. Each request has fresh AES command and response keys; only the AES command key is RSA-OAEP wrapped for GVBSMEDIA.

## Required environment

- `GVM_GITHUB_TOKEN` - fine-grained GitHub token with **Contents: Read and write** only for `GVibes767/N`.
- `PORT` - supplied by host, default 8010.

Optional:
- `GVM_COMMAND_REPO=GVibes767/N`
- `GVM_RESPONSE_REPO=mediagvibes-wq/gvm-relay`
- `GVM_TARGET=GVBSMEDIA`
- `GVM_FAST_HEALTH_URL=https://edge.rskbobr.ru/health`
- `GVM_CALL_TIMEOUT=35`

## Endpoint

Streamable HTTP MCP: `/mcp`.

## Tools

Read:
- `gvm.transport.health`
- `gvm.system.status`
- `gvm.context.compose`
- `gvm.runtime.state`
- `gvm.runtime.capabilities`
- `gvm.runtime.job.get`
- `gvm.runtime.mission.get`
- `gvm.runtime.progress`
- `gvm.artifact.get`
- `gvm.artifact.text`
- `gvm.task.route`

Runtime-controlled effects:
- `gvm.runtime.command.submit`
- `gvm.mission.create`
- `gvm.mission.approve`
- `gvm.mission.resume`
- `gvm.mission.cancel`

The MCP layer does not bypass Runtime approvals, permission profiles, idempotency, path scopes or verification.

## ChatGPT availability note

Full custom MCP write actions in ChatGPT require an eligible workspace/plan and custom-app developer access. The server itself is plan-agnostic.
