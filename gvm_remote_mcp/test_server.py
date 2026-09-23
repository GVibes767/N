import base64
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import server


def test_envelope_shape_and_lifetime():
    request_id, response_key, env = server._envelope("system.status", {})
    assert request_id.startswith("gvm-mcp-")
    assert len(response_key) == 32
    assert env["schemaVersion"] == 1
    assert env["target"] == server.TARGET
    assert env["requestId"] == request_id
    assert base64.b64decode(env["nonce"])
    assert base64.b64decode(env["wrappedKey"])
    assert base64.b64decode(env["ciphertext"])


def test_response_decrypt_roundtrip():
    request_id = "gvm-mcp-test"
    key = os.urandom(32)
    nonce = os.urandom(12)
    payload = {"requestId": request_id, "ok": True, "result": {"value": 7}}
    aad = f"gvm-relay:v1:response:{request_id}".encode()
    ciphertext = AESGCM(key).encrypt(
        nonce, json.dumps(payload, separators=(",", ":")).encode(), aad
    )
    env = {
        "schemaVersion": 1,
        "requestId": request_id,
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }
    assert server._decrypt_response(request_id, key, env) == payload


def test_write_requires_token(monkeypatch):
    monkeypatch.setattr(server, "GITHUB_TOKEN", "")
    try:
        server._headers(auth=True)
    except RuntimeError as exc:
        assert "GVM_GITHUB_TOKEN" in str(exc)
    else:
        raise AssertionError("write path must require GVM_GITHUB_TOKEN")
