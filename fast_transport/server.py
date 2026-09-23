from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Dict

import aiohttp
from aiohttp import web

HOST = os.environ.get("GVM_FAST_HOST", "127.0.0.1")
PORT = int(os.environ.get("GVM_FAST_PORT", "8789"))
WEBHOOK_SECRET = os.environ["GVM_GITHUB_WEBHOOK_SECRET"].encode("utf-8")
DEVICE_TOKEN = os.environ["GVM_DEVICE_TOKEN"]
COMMAND_REPO = os.environ.get("GVM_COMMAND_REPO", "GVibes767/N")
TARGET_DEVICE = os.environ.get("GVM_TARGET_DEVICE", "GVBSMEDIA")
MAX_BODY = 2 * 1024 * 1024

@dataclass
class DeviceSession:
    ws: web.WebSocketResponse
    connected_at: float

devices: Dict[str, DeviceSession] = {}

def verify_github_signature(body: bytes, signature: str | None) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature[7:], expected)

async def health(_: web.Request) -> web.Response:
    return web.json_response({
        "ok": True,
        "service": "gvm-fast-transport",
        "version": "0.1.0",
        "target": TARGET_DEVICE,
        "deviceConnected": TARGET_DEVICE in devices,
    })

async def device_ws(request: web.Request) -> web.StreamResponse:
    auth = request.headers.get("Authorization", "")
    if not hmac.compare_digest(auth, f"Bearer {DEVICE_TOKEN}"):
        raise web.HTTPUnauthorized()
    device = request.query.get("device", "")
    if device != TARGET_DEVICE:
        raise web.HTTPForbidden()

    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=MAX_BODY)
    await ws.prepare(request)
    devices[device] = DeviceSession(ws=ws, connected_at=asyncio.get_running_loop().time())
    try:
        await ws.send_json({"type": "hello", "device": device, "version": "0.1.0"})
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    value = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                if value.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                break
    finally:
        current = devices.get(device)
        if current and current.ws is ws:
            devices.pop(device, None)
    return ws

async def fetch_command(session: aiohttp.ClientSession, sha: str, path: str) -> bytes:
    url = f"https://raw.githubusercontent.com/{COMMAND_REPO}/{sha}/{path}"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub raw fetch failed: {response.status}")
        body = await response.read()
        if len(body) > MAX_BODY:
            raise RuntimeError("queue item too large")
        return body

async def github_webhook(request: web.Request) -> web.Response:
    body = await request.read()
    if len(body) > MAX_BODY:
        raise web.HTTPRequestEntityTooLarge(max_size=MAX_BODY, actual_size=len(body))
    if not verify_github_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise web.HTTPUnauthorized()
    if request.headers.get("X-GitHub-Event") != "push":
        return web.json_response({"ok": True, "ignored": "event"})
    payload = json.loads(body)
    if payload.get("ref") != "refs/heads/main":
        return web.json_response({"ok": True, "ignored": "ref"})
    full_name = ((payload.get("repository") or {}).get("full_name") or "")
    if full_name != COMMAND_REPO:
        raise web.HTTPForbidden()

    after = str(payload.get("after") or "")
    paths = []
    for commit in payload.get("commits") or []:
        for path in (commit.get("added") or []) + (commit.get("modified") or []):
            if path.startswith("relay/queue/") and path.endswith(".json"):
                paths.append(path)
    paths = list(dict.fromkeys(paths))[-16:]
    session_state = devices.get(TARGET_DEVICE)
    if not paths or not session_state:
        return web.json_response({
            "ok": True,
            "forwarded": 0,
            "deviceConnected": bool(session_state),
        })

    forwarded = 0
    async with aiohttp.ClientSession() as session:
        for path in paths:
            try:
                raw = await fetch_command(session, after, path)
                await session_state.ws.send_json({
                    "type": "command",
                    "path": path,
                    "sha": after,
                    "envelopeB64": base64.b64encode(raw).decode("ascii"),
                })
                forwarded += 1
            except Exception:
                # GitHub polling remains the authoritative fallback.
                continue
    return web.json_response({"ok": True, "forwarded": forwarded, "deviceConnected": True})

def build_app() -> web.Application:
    app = web.Application(client_max_size=MAX_BODY)
    app.router.add_get("/health", health)
    app.router.add_get("/v1/device/ws", device_ws)
    app.router.add_post("/v1/github/webhook", github_webhook)
    return app

if __name__ == "__main__":
    web.run_app(build_app(), host=HOST, port=PORT, access_log=None)
