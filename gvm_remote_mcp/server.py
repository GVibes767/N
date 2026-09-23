from __future__ import annotations

import base64
import datetime as dt
import json
import os
import time
import uuid
from functools import lru_cache
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastmcp import FastMCP

COMMAND_REPO = os.getenv("GVM_COMMAND_REPO", "GVibes767/N")
RESPONSE_REPO = os.getenv("GVM_RESPONSE_REPO", "mediagvibes-wq/gvm-relay")
COMMAND_BRANCH = os.getenv("GVM_COMMAND_BRANCH", "main")
RESPONSE_BRANCH = os.getenv("GVM_RESPONSE_BRANCH", "main")
TARGET = os.getenv("GVM_TARGET", "GVBSMEDIA")
DEVICE_PUBLIC_KEY_URL = os.getenv(
    "GVM_DEVICE_PUBLIC_KEY_URL",
    "https://raw.githubusercontent.com/GVibes767/N/main/relay/device-public.pem",
)
FAST_HEALTH_URL = os.getenv("GVM_FAST_HEALTH_URL", "https://edge.rskbobr.ru/health")
GITHUB_TOKEN = os.getenv("GVM_GITHUB_TOKEN", "")
CALL_TIMEOUT = float(os.getenv("GVM_CALL_TIMEOUT", "35"))
POLL_SECONDS = float(os.getenv("GVM_POLL_SECONDS", "0.5"))
MAX_LIFETIME_SECONDS = int(os.getenv("GVM_MAX_LIFETIME_SECONDS", "600"))

mcp = FastMCP(
    "GVM Remote",
    instructions=(
        "Remote control and context bridge for the user's GVBSMEDIA workstation. "
        "Use read/status/context tools before effects. Production Runtime keeps approval, "
        "idempotency and verification authority."
    ),
    stateless_http=True,
    json_response=True,
)


def _headers(auth: bool = False) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gvm-remote-mcp/0.1",
    }
    if auth:
        if not GITHUB_TOKEN:
            raise RuntimeError(
                "GVM_GITHUB_TOKEN is not configured on the remote MCP server. "
                "Use a fine-grained GitHub token limited to contents:write on GVibes767/N."
            )
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


@lru_cache(maxsize=1)
def _device_public_key():
    with httpx.Client(timeout=10, follow_redirects=True) as client:
        r = client.get(DEVICE_PUBLIC_KEY_URL)
        r.raise_for_status()
    return serialization.load_pem_public_key(r.content)


def _envelope(tool: str, arguments: dict[str, Any]) -> tuple[str, bytes, dict[str, Any]]:
    request_id = "gvm-mcp-" + uuid.uuid4().hex
    command_key = os.urandom(32)
    response_key = os.urandom(32)
    nonce = os.urandom(12)
    payload = {
        "requestId": request_id,
        "tool": tool,
        "arguments": arguments,
        "responseKey": base64.b64encode(response_key).decode("ascii"),
    }
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    aad = f"gvm-relay:v1:command:{TARGET}:{request_id}".encode("utf-8")
    ciphertext = AESGCM(command_key).encrypt(nonce, plaintext, aad)
    wrapped_key = _device_public_key().encrypt(
        command_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
        seconds=min(MAX_LIFETIME_SECONDS, 1800)
    )
    envelope = {
        "schemaVersion": 1,
        "target": TARGET,
        "requestId": request_id,
        "expiresAt": expires.isoformat(),
        "wrappedKey": base64.b64encode(wrapped_key).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return request_id, response_key, envelope


def _create_queue_item(request_id: str, envelope: dict[str, Any]) -> str:
    path = f"relay/queue/{request_id}.json"
    url = f"https://api.github.com/repos/{COMMAND_REPO}/contents/{path}"
    raw = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    body = {
        "message": f"GVM MCP {request_id}",
        "content": base64.b64encode(raw).decode("ascii"),
        "branch": COMMAND_BRANCH,
    }
    with httpx.Client(timeout=15) as client:
        r = client.put(url, headers=_headers(auth=True), json=body)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"GitHub queue write failed: HTTP {r.status_code}")
        data = r.json()
    return str((data.get("content") or {}).get("sha") or "")


def _read_response(request_id: str) -> dict[str, Any] | None:
    path = f"relay/responses/{request_id}.json"
    url = f"https://api.github.com/repos/{RESPONSE_REPO}/contents/{path}"
    with httpx.Client(timeout=10) as client:
        r = client.get(url, headers=_headers(auth=bool(GITHUB_TOKEN)), params={"ref": RESPONSE_BRANCH})
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise RuntimeError(f"GitHub response read failed: HTTP {r.status_code}")
    item = r.json()
    return json.loads(base64.b64decode(item["content"]).decode("utf-8"))


def _delete_queue_item(request_id: str, sha: str) -> None:
    if not sha:
        return
    path = f"relay/queue/{request_id}.json"
    url = f"https://api.github.com/repos/{COMMAND_REPO}/contents/{path}"
    body = {
        "message": f"Complete GVM MCP {request_id}",
        "sha": sha,
        "branch": COMMAND_BRANCH,
    }
    try:
        with httpx.Client(timeout=10) as client:
            client.request("DELETE", url, headers=_headers(auth=True), json=body)
    except Exception:
        # Expiry + device ledger keep an orphaned queue item safe.
        pass


def _decrypt_response(request_id: str, response_key: bytes, envelope: dict[str, Any]) -> dict[str, Any]:
    if envelope.get("schemaVersion") != 1 or envelope.get("requestId") != request_id:
        raise RuntimeError("Unexpected GVM response envelope")
    nonce = base64.b64decode(envelope["nonce"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    aad = f"gvm-relay:v1:response:{request_id}".encode("utf-8")
    plaintext = AESGCM(response_key).decrypt(nonce, ciphertext, aad)
    value = json.loads(plaintext.decode("utf-8"))
    if value.get("requestId") != request_id:
        raise RuntimeError("GVM response requestId mismatch")
    return value


def _call(tool: str, arguments: dict[str, Any], timeout: float | None = None) -> Any:
    request_id, response_key, env = _envelope(tool, arguments)
    queue_sha = _create_queue_item(request_id, env)
    deadline = time.monotonic() + (timeout or CALL_TIMEOUT)
    try:
        while time.monotonic() < deadline:
            response = _read_response(request_id)
            if response is not None:
                decoded = _decrypt_response(request_id, response_key, response)
                if not decoded.get("ok"):
                    raise RuntimeError(str(decoded.get("error") or "GVM tool failed"))
                return decoded.get("result")
            time.sleep(POLL_SECONDS)
        raise TimeoutError(
            f"GVM request {request_id} timed out after {timeout or CALL_TIMEOUT:.0f}s"
        )
    finally:
        _delete_queue_item(request_id, queue_sha)


@mcp.tool(name="gvm.transport.health")
def transport_health() -> dict[str, Any]:
    """Read the public Fast Transport health endpoint; no workstation effect."""
    with httpx.Client(timeout=8, follow_redirects=True) as client:
        r = client.get(FAST_HEALTH_URL)
        r.raise_for_status()
        value = r.json()
    return {"source": FAST_HEALTH_URL, **value}


@mcp.tool(name="gvm.system.status")
def system_status() -> Any:
    """Live read-only GVM Connect / GVBSMEDIA status."""
    return _call("system.status", {})


@mcp.tool(name="gvm.context.compose")
def context_compose(projectId: str, intent: str = "", query: str = "", budget: int = 8000) -> Any:
    """Build compact project-scoped context for a new ChatGPT turn."""
    return _call(
        "context.compose",
        {"projectId": projectId, "intent": intent, "query": query, "budget": budget},
    )


@mcp.tool(name="gvm.runtime.state")
def runtime_state() -> Any:
    """Read production Runtime state."""
    return _call("runtime.state", {})


@mcp.tool(name="gvm.runtime.capabilities")
def runtime_capabilities() -> Any:
    """Read verified Runtime capability states."""
    return _call("runtime.capabilities", {})


@mcp.tool(name="gvm.runtime.job.get")
def runtime_job_get(id: str) -> Any:
    """Read a durable Runtime job by jobId or requestId."""
    return _call("runtime.job.get", {"id": id})


@mcp.tool(name="gvm.runtime.mission.get")
def runtime_mission_get(id: str) -> Any:
    """Read a durable Runtime mission and progress."""
    return _call("runtime.mission.get", {"id": id})


@mcp.tool(name="gvm.runtime.progress")
def runtime_progress(kind: str, id: str) -> Any:
    """Read normalized durable progress for a Runtime job or mission."""
    if kind not in ("job", "mission"):
        raise ValueError("kind must be job or mission")
    return _call("runtime.progress", {"kind": kind, "id": id})


@mcp.tool(name="gvm.artifact.get")
def artifact_get(id: str) -> Any:
    """Read verified artifact metadata."""
    return _call("runtime.artifact.get", {"id": id})


@mcp.tool(name="gvm.artifact.text")
def artifact_text(id: str) -> Any:
    """Read a registered bounded text artifact."""
    return _call("runtime.artifact.text", {"id": id})


@mcp.tool(name="gvm.task.route")
def task_route(task: str, hints: list[str] | None = None) -> Any:
    """Advisory deterministic route; does not itself execute an effect."""
    return _call("task.route", {"task": task, "hints": hints or []})


@mcp.tool(name="gvm.runtime.command.submit")
def runtime_command_submit(command: dict[str, Any]) -> Any:
    """Submit an explicit production Runtime command; Runtime policy/approval remains authoritative."""
    return _call("runtime.command.submit", {"command": command})


@mcp.tool(name="gvm.mission.create")
def mission_create(mission: dict[str, Any]) -> Any:
    """Create an explicit production Runtime mission draft."""
    return _call("runtime.mission.create", {"mission": mission})


@mcp.tool(name="gvm.mission.approve")
def mission_approve(
    missionId: str,
    planRevision: int,
    planDigest: str,
    actor: str,
    evidence: str,
) -> Any:
    """Approve the exact current mission revision/digest through Runtime's approval mechanism."""
    return _call(
        "runtime.mission.approve",
        {
            "missionId": missionId,
            "planRevision": planRevision,
            "planDigest": planDigest,
            "actor": actor,
            "evidence": evidence,
        },
    )


@mcp.tool(name="gvm.mission.resume")
def mission_resume(missionId: str, planRevision: int, planDigest: str) -> Any:
    """Resume an already-approved exact Runtime mission revision."""
    return _call(
        "runtime.mission.resume",
        {"missionId": missionId, "planRevision": planRevision, "planDigest": planDigest},
    )


@mcp.tool(name="gvm.mission.cancel")
def mission_cancel(missionId: str) -> Any:
    """Request safe-boundary cancellation through production Runtime."""
    return _call("runtime.mission.cancel", {"missionId": missionId})


if __name__ == "__main__":
    host = os.getenv("GVM_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("GVM_MCP_PORT", "8010")))
    mcp.run(transport="http", host=host, port=port, path="/mcp")
