import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from captivate.config import SessionConfig
from captivate.portal import PortalServer


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, url):
        return None


@pytest.fixture
def portal():
    servers = []

    def create(**kwargs):
        server = PortalServer(SessionConfig(**kwargs), preview=True)
        server.start()
        servers.append(server)
        return server

    yield create
    for server in servers:
        server.stop()


def get(server, path=""):
    try:
        return urllib.request.urlopen(server.url + path, timeout=3)
    except urllib.error.HTTPError as response:
        return response


def post(server, **values):
    data = urllib.parse.urlencode(values).encode()
    opener = urllib.request.build_opener(NoRedirect())
    try:
        return opener.open(server.url + "captivate/continue", data=data, timeout=3)
    except urllib.error.HTTPError as response:
        return response


def token(server):
    page = get(server).read().decode()
    return re.search(r'name="token" value="([^"]+)"', page)[1]


def test_welcome_requires_valid_token_and_confirms_visit(portal):
    server = portal()
    assert post(server, token="wrong").status == 403
    response = post(server, token=token(server))
    assert response.status == 303
    assert server.state.is_authorized("127.0.0.1")
    assert b"does not provide internet" in get(server, "captivate/success").read()


def test_non_ascii_invalid_token_returns_rejection_not_a_server_error(portal):
    server = portal()
    assert post(server, token="界").status == 403
    assert not server.state.is_authorized("127.0.0.1")


@pytest.mark.parametrize("empty_field", ["title", "button"])
def test_custom_site_previews_with_empty_unused_builtin_fields(portal, tmp_path, empty_field):
    (tmp_path / "index.html").write_text("<h1>My website</h1>")
    server = portal(template="custom", custom_directory=str(tmp_path), **{empty_field: ""})
    assert get(server).status == 200
    assert b"My website" in get(server).read()


def test_terms_enforced_server_side(portal):
    server = portal(template="terms")
    assert post(server, token=token(server)).status == 400
    assert not server.state.is_authorized("127.0.0.1")
    assert post(server, token=token(server), accept="yes").status == 303


def test_voucher_rejection_and_success(portal):
    server = portal(template="voucher", vouchers="valid-test-voucher")
    assert b"valid-test-voucher" not in get(server).read()
    assert post(server, token=token(server), voucher="incorrect").status == 403
    assert not server.state.is_authorized("127.0.0.1")
    assert post(server, token=token(server), voucher="valid-test-voucher").status == 303


def test_confirmation_rate_limit(portal):
    server = portal()
    for _ in range(10):
        assert post(server, token="wrong").status == 403
    assert post(server, token="wrong").status == 429


def test_user_text_is_escaped(portal):
    server = portal(title='<script>alert("x")</script>')
    page = get(server).read()
    assert b"<script>" not in page
    assert b"&lt;script&gt;" in page


def test_captive_probe_redirects_to_canonical_page(portal):
    server = portal()
    opener = urllib.request.build_opener(NoRedirect())
    with pytest.raises(urllib.error.HTTPError) as caught:
        opener.open(server.url + "generate_204")
    assert caught.value.code == 302
    assert caught.value.headers["Location"] == server.url


@pytest.mark.parametrize("path", ["/", "/index.html", "/generate_204"])
def test_live_intercepted_origins_redirect_forms_to_gateway(portal, path):
    server = portal()
    server.state.preview = False
    server.state.config.gateway = "127.0.0.1/24"
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(server.url.rstrip("/") + path, headers={"Host": "connectivitycheck.gstatic.com"})
    with pytest.raises(urllib.error.HTTPError) as caught:
        opener.open(request, timeout=3)
    assert caught.value.code == 302
    assert caught.value.headers["Location"] == "http://127.0.0.1/"
    assert b"<form" not in caught.value.read()


def test_offline_api_remains_captive_after_confirmation(portal):
    server = portal()
    post(server, token=token(server))
    assert b'"captive": true' in get(server, "captivate/api").read()


def test_static_website_and_path_containment(portal, tmp_path):
    website = tmp_path / "site"
    website.mkdir()
    (website / "index.html").write_text("<h1>Local website</h1>")
    (website / "style.css").write_text("body { color: blue; }")
    secret = tmp_path / "secret.txt"
    secret.write_text("outside-root")
    (website / "leak.txt").symlink_to(secret)
    (website / ".env").write_text("hidden-file")
    server = portal(template="custom", custom_directory=str(website))
    assert b"Local website" in get(server).read()
    assert get(server, "style.css").status == 200
    assert get(server, "%2e%2e/secret.txt").status == 403
    assert get(server, "leak.txt").status == 403
    assert get(server, ".env").status == 403
    assert get(server, "missing.html").status == 404


def test_grant_failure_does_not_mark_authorized(portal):
    server = portal()
    server.state.preview = False
    server.state.config.gateway = "127.0.0.1/24"

    def fail(_address):
        raise RuntimeError("helper unavailable")

    server.state.grant = fail
    assert post(server, token=token(server)).status == 503
    assert not server.state.is_authorized("127.0.0.1")


def test_headers_and_local_assets(portal):
    server = portal()
    response = get(server)
    assert response.headers["Cache-Control"] == "no-store"
    assert "form-action 'self'" in response.headers["Content-Security-Policy"]
    assert get(server, "captivate-assets/portal.css").status == 200
    assert get(server, "captivate-assets/captivate.svg").status == 200


def test_static_directory_index_symlink_cannot_escape(portal, tmp_path):
    (tmp_path / "index.html").write_text("home")
    subdirectory = tmp_path / "sub"
    subdirectory.mkdir()
    (subdirectory / "index.html").symlink_to(Path("/etc/passwd"))
    server = portal(template="custom", custom_directory=str(tmp_path))
    assert get(server, "sub/").status == 403
