"""Middleware: batas body (TC-1), CSRF header, rate limit, security header, log JSON (§13, §20)."""
from __future__ import annotations

import json
import sys
import time
import uuid
from collections import defaultdict, deque

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.errors import body as err_body

MAX_BODY_BYTES = 65536
RATE_LIMIT_PER_MIN = 60
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = b"x-payray-csrf"
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'"
SECURITY_HEADERS = [
    (b"content-security-policy", CSP.encode()),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
]
SESSION_COOKIE = "payray_session"


def _cookie(headers: dict[bytes, bytes], name: str) -> str | None:
    raw = headers.get(b"cookie", b"").decode("latin-1")
    for part in raw.split(";"):
        k, _, v = part.strip().partition("=")
        if k == name:
            return v
    return None


async def _json(send: Send, status: int, code: str, message: str) -> None:
    payload = json.dumps(err_body(code, message)).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode()),
                            *SECURITY_HEADERS]})
    await send({"type": "http.response.body", "body": payload})


class GuardMiddleware:
    """ASGI murni supaya batas body bisa ditegakkan saat stream dibaca (TC-6: in-memory, single instance)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def _rate_limited(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT_PER_MIN:
            return True
        q.append(now)
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        t0 = time.perf_counter()
        rid = uuid.uuid4().hex[:16]
        headers = dict(scope["headers"])
        method, path = scope["method"], scope["path"]
        state: dict[str, int] = {"status": 500, "too_large": 0, "replaced": 0}

        async def send_wrapped(msg: Message) -> None:
            if state["replaced"]:
                return
            if msg["type"] == "http.response.start" and state["too_large"]:
                # Body melebihi batas saat stream dibaca: ganti respons apa pun dengan 413.
                state["replaced"] = 1
                payload = json.dumps(err_body("payload_too_large", "Body request melebihi 64 KB.")).encode()
                state["status"] = 413
                await send({"type": "http.response.start", "status": 413,
                            "headers": [(b"content-type", b"application/json"),
                                        (b"content-length", str(len(payload)).encode()), *SECURITY_HEADERS,
                                        (b"x-request-id", rid.encode())]})
                await send({"type": "http.response.body", "body": payload})
                return
            if msg["type"] == "http.response.start":
                state["status"] = msg["status"]
                existing = {k.lower() for k, _ in msg.get("headers", [])}
                extra = [(k, v) for k, v in SECURITY_HEADERS if k not in existing]
                if b"cache-control" not in existing:
                    # API: jangan di-cache. Aset web: selalu validasi ulang via ETag supaya versi baru langsung tampil.
                    extra.append((b"cache-control", b"no-store" if path.startswith("/api/") else b"no-cache"))
                msg["headers"] = [*msg.get("headers", []), *extra, (b"x-request-id", rid.encode())]
            await send(msg)

        try:
            if path.startswith("/api/"):
                session = _cookie(headers, SESSION_COOKIE)
                if session and self._rate_limited(session):
                    await _json(send_wrapped, 429, "rate_limited", "Terlalu banyak permintaan. Tunggu sebentar.")
                    return
                if method in MUTATING and headers.get(CSRF_HEADER) != b"1":
                    await _json(send_wrapped, 403, "csrf", "Header X-PayRay-CSRF wajib untuk perubahan data.")
                    return
                declared = headers.get(b"content-length")
                if declared is not None and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
                    await _json(send_wrapped, 413, "payload_too_large", "Body request melebihi 64 KB.")
                    return

            received = 0

            async def receive_limited() -> Message:
                nonlocal received
                msg = await receive()
                if msg["type"] == "http.request":
                    received += len(msg.get("body", b""))
                    if received > MAX_BODY_BYTES:
                        state["too_large"] = 1
                        return {"type": "http.request", "body": b"", "more_body": False}
                return msg

            await self.app(scope, receive_limited, send_wrapped)
        finally:
            user = scope.get("state", {}).get("user")
            print(json.dumps({
                "request_id": rid, "method": method, "path": path, "status": state["status"],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "user_id": getattr(user, "id", None), "role": getattr(user, "role", None),
            }), file=sys.stdout, flush=True)
