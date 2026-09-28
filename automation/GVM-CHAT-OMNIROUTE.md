# GVM + ChatGPT + OmniRoute

Target: ChatGPT remains the main supervisor/director; GVM performs durable local work; OmniRoute supplies background/fallback model calls.

Flow:
ChatGPT -> GVM Mission -> GVM Runtime -> local tools/Resolve/files/browser
                         -> OmniRoute for routine/fallback model calls
                         -> checkpoints/artifacts -> ChatGPT review

Rules:
- ChatGPT handles user intent, high-value planning, creative critique and final acceptance.
- GVM owns durable state, execution, retries, watchdog, verification and artifact delivery.
- OmniRoute is a local model gateway, not a replacement for ChatGPT.
- Every substantial edit produces a checkpoint.
- DONE requires verified output artifact, not a model statement.
- Paid API routes are fallback-only unless the user explicitly approves a budget.
- Keep existing transport: GVibes767/N -> GVM Relay -> GVBSMEDIA -> mediagvibes-wq/gvm-relay.
