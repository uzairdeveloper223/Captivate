"""Unprivileged local portal server and offline visitor pages."""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import mimetypes
import secrets
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from captivate.config import SessionConfig

ASSETS = Path(__file__).parent / "assets"
MAX_FILE_BYTES = 32 * 1024 * 1024


def render_page(config: SessionConfig, token: str, *, preview=False, error="", completed=False) -> bytes:
    escape = html.escape
    sharing = bool(config.uplink)
    title = "Access granted" if completed else (config.title or "Network access")
    message = config.message
    if completed:
        message = (
            f"Internet access is available for {config.session_minutes} minutes. You may close this window."
            if sharing else "Your visit is confirmed. This hotspot hosts local content and does not provide internet access."
        )
    fields = ""
    if config.template == "terms":
        fields = f'''<div class="terms">{escape(config.terms)}</div>
<label class="agreement"><input type="checkbox" name="accept" value="yes" required>
<span>I accept the terms of access.</span></label>'''
    elif config.template == "voucher":
        fields = '''<label for="voucher">Access code</label>
<input id="voucher" name="voucher" autocomplete="off" maxlength="128" required placeholder="Enter your access code">'''
    form = f'''<form action="/captivate/continue" method="post">
<input type="hidden" name="token" value="{escape(token)}">{fields}
<button type="submit">{escape(config.button or "Continue")}</button></form>'''
    if completed:
        form = '<a class="secondary" href="/">Return to the portal</a>'
    note = '<div class="preview">Preview session · No network changes</div>' if preview else ""
    alert = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    mode = "Internet access after confirmation" if sharing else "Local hotspot · No internet connection"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · {escape(config.ssid)}</title><link rel="stylesheet" href="/captivate-assets/portal.css">
<link rel="icon" href="/captivate-assets/captivate.svg" type="image/svg+xml"></head>
<body>{note}<main><header><img src="/captivate-assets/captivate.svg" width="48" height="48" alt="">
<span>{escape(config.ssid)}</span></header><h1>{escape(title)}</h1><p class="message">{escape(message)}</p>
{alert}{form}<footer>{mode}<br>Powered by <a href="https://uzair.is-a.dev">Captivate</a></footer></main></body></html>'''.encode()


class PortalState:
    def __init__(self, config: SessionConfig, grant, log, preview: bool):
        self.config = config
        self.grant = grant
        self.log = log
        self.preview = preview
        self.secret = secrets.token_bytes(32)
        self.authorized: dict[str, float] = {}
        self.attempts: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()
        # Hash high-entropy vouchers with a session secret; raw codes never enter logs or pages.
        self.voucher_hashes = {self.voucher_hash(code) for code in config.vouchers.split()}

    def voucher_hash(self, code: str) -> str:
        return hmac.new(self.secret, code.encode(), hashlib.sha256).hexdigest()

    def token(self, address: str) -> str:
        return hmac.new(self.secret, address.encode(), hashlib.sha256).hexdigest()

    def is_authorized(self, address: str) -> bool:
        with self.lock:
            return self.authorized.get(address, 0) > time.monotonic()

    def rate_limited(self, address: str) -> bool:
        with self.lock:
            queue = self.attempts[address]
            now = time.monotonic()
            while queue and now - queue[0] > 60:
                queue.popleft()
            if len(queue) >= 10:
                return True
            queue.append(now)
            return False


class PortalHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, state: PortalState):
        self.state = state
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(address, PortalHandler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "Captivate"
    sys_version = ""

    @property
    def state(self) -> PortalState:
        return self.server.state

    @property
    def peer(self) -> str:
        return self.client_address[0]

    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def log_message(self, _format, *_args):
        # Avoid logging arbitrary URLs, query strings, vouchers, and visitor form values.
        pass

    def allowed_peer(self) -> bool:
        return self.state.preview or ip_address(self.peer) in self.state.config.network

    def respond(self, status: int, body: bytes = b"", content_type="text/html; charset=utf-8", **headers):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if self.state.config.template != "custom":
            self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        else:
            self.send_header("Content-Security-Policy", "object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        for key, value in headers.items():
            self.send_header(key.replace("_", "-"), value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def page(self, *, error="", completed=False, status=200):
        self.respond(status, render_page(
            self.state.config, self.state.token(self.peer), preview=self.state.preview,
            error=error, completed=completed,
        ))

    def redirect(self, path="/"):
        host = f"127.0.0.1:{self.server.server_port}" if self.state.preview else self.state.config.address
        self.respond(302, Location=f"http://{host}{path}")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.allowed_peer():
            self.respond(403, b"This portal is available to hotspot clients only.", "text/plain")
            return
        path = unquote(urlsplit(self.path).path)
        if not self.state.preview:
            host = self.headers.get("Host", "").lower().split(":", 1)[0]
            if host not in (self.state.config.address, "portal.home.arpa"):
                # An intercepted site's origin stops being intercepted after
                # confirmation. Move forms/assets to the gateway beforehand.
                self.redirect()
                return
        if path.startswith("/captivate-assets/"):
            self.serve_file(ASSETS, path.removeprefix("/captivate-assets/"))
        elif path == "/captivate/api":
            self.respond(200, json.dumps({
                "captive": not (bool(self.state.config.uplink) and self.state.is_authorized(self.peer)),
                "user-portal-url": f"http://{self.state.config.address}/",
            }).encode(), "application/captive+json")
        elif path == "/captivate/token":
            self.respond(200, json.dumps({"token": self.state.token(self.peer)}).encode(), "application/json")
        elif path == "/captivate/success":
            self.page(completed=self.state.is_authorized(self.peer))
        elif path in ("/generate_204", "/gen_204", "/hotspot-detect.html", "/connecttest.txt", "/ncsi.txt", "/canonical.html", "/success.txt"):
            # These normally leave through the uplink once authorized. Never claim online in offline mode.
            self.redirect()
        elif self.state.config.template == "custom":
            self.serve_file(Path(self.state.config.custom_directory).expanduser(), path.lstrip("/") or "index.html")
        elif path in ("/", "/index.html"):
            self.page()
        else:
            self.redirect()

    def serve_file(self, root: Path, relative: str):
        root = root.resolve()
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root) or any(part.startswith(".") for part in Path(relative).parts):
            self.respond(403, b"File access denied.", "text/plain")
            return
        if candidate.is_dir():
            candidate = (candidate / "index.html").resolve()
        if not candidate.is_relative_to(root):
            self.respond(403, b"File access denied.", "text/plain")
            return
        try:
            if candidate.stat().st_size > MAX_FILE_BYTES:
                self.respond(413, b"File exceeds the 32 MiB serving limit.", "text/plain")
                return
            data = candidate.read_bytes()
        except (OSError, ValueError):
            self.respond(404, b"File not found.", "text/plain")
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.respond(200, data, content_type)

    def do_POST(self):
        if not self.allowed_peer():
            self.respond(403)
            return
        if urlsplit(self.path).path != "/captivate/continue":
            self.respond(404)
            return
        if self.state.rate_limited(self.peer):
            self.respond(429, b"Too many attempts. Try again in one minute.", "text/plain", Retry_After="60")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                self.respond(413)
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/x-www-form-urlencoded":
                self.respond(415)
                return
            values = parse_qs(self.rfile.read(length).decode("utf-8"), max_num_fields=8)
        except (ValueError, UnicodeError):
            self.respond(400)
            return
        token = values.get("token", [""])[0]
        if not hmac.compare_digest(token.encode(), self.state.token(self.peer).encode()):
            self.state.log("Portal confirmation rejected: invalid form token.")
            self.page(error="The page expired. Reload it and try again.", status=403)
            return
        config = self.state.config
        if config.template == "terms" and values.get("accept") != ["yes"]:
            self.page(error="Accept the terms to continue.", status=400)
            return
        if config.template == "voucher":
            code = values.get("voucher", [""])[0].strip()
            if self.state.voucher_hash(code) not in self.state.voucher_hashes:
                self.state.log("Portal confirmation rejected: invalid voucher.")
                self.page(error="That access code is not valid. Check the code and try again.", status=403)
                return
        try:
            if not self.state.preview:
                self.state.grant(self.peer)
            with self.state.lock:
                self.state.authorized[self.peer] = time.monotonic() + config.session_minutes * 60
            self.state.log("Visitor access confirmed.")
            self.respond(303, Location="/captivate/success")
        except (RuntimeError, TimeoutError, ValueError):
            self.state.log("Portal confirmation failed: the network helper could not grant access.")
            self.page(error="Access could not be granted. Ask the hotspot operator to check the session.", status=503)


class PortalServer:
    def __init__(self, config: SessionConfig, *, preview=False, grant=lambda _ip: None, log=lambda _msg: None):
        config.validate(networking=not preview)
        self.state = PortalState(config, grant, log, preview)
        host = "127.0.0.1" if preview else "0.0.0.0"
        port = 0 if preview else config.port
        self.httpd = PortalHTTPServer((host, port), self.state)
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="captivate-portal", daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_port}/"

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)
