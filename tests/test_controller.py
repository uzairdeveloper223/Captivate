"""Verify asynchronous helper orchestration with a harmless stand-in process."""

import os
import socket
import threading
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from captivate.config import SessionConfig  # noqa: E402
from captivate.controller import SessionController  # noqa: E402
from captivate.ui import create_application  # noqa: E402


@pytest.fixture(scope="session")
def application():
    return create_application()


@pytest.fixture
def controller(application, monkeypatch, tmp_path):
    fake_authority = tmp_path / "fake-authority"
    fake_authority.write_text('''#!/usr/bin/python3
import json
import sys
for line in sys.stdin:
    message = json.loads(line)
    if message['command'] == 'start':
        print(json.dumps({'event': 'started', 'address': '10.42.0.1', 'sharing': False}), flush=True)
    elif message['command'] == 'allow':
        print(json.dumps({'event': 'allowed', 'request_id': message['request_id'], 'ok': True}), flush=True)
    elif message['command'] == 'stop':
        print(json.dumps({'event': 'stopping'}), flush=True)
        break
    elif message['command'] == 'recover':
        print(json.dumps({'event': 'log', 'message': 'No interrupted session was found.'}), flush=True)
        break
''')
    fake_authority.chmod(0o755)
    monkeypatch.setattr("captivate.controller.shutil.which", lambda _name: str(fake_authority))
    session = SessionController(application)
    yield application, session
    if session.busy:
        session.stop()
        wait_for(application, lambda: not session.busy)
    session.close_preview()


def wait_for(application, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert predicate(), "The asynchronous helper did not reach the expected state."


def test_helper_lifecycle_and_concurrent_http_grant_acknowledgments(controller):
    application, session = controller
    with socket.socket() as socket_:
        socket_.bind(("127.0.0.1", 0))
        port = socket_.getsockname()[1]
    states = []
    session.status.connect(states.append)
    session.start(SessionConfig(interface="wlan0", port=port))
    wait_for(application, lambda: session.state == "running")
    errors = []

    def grant(address):
        try:
            session.grant(address)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=grant, args=(f"10.42.0.{20 + index}",)) for index in range(3)]
    for thread in threads:
        thread.start()
    wait_for(application, lambda: all(not thread.is_alive() for thread in threads))
    for thread in threads:
        thread.join()
    assert not errors
    assert not session.pending
    session.stop()
    wait_for(application, lambda: not session.busy)
    assert session.portal is None
    assert states[0] == "authorizing"
    assert "running" in states and "stopping" in states
    assert states[-1] == "idle"


def test_appimage_stages_helper_and_libraries_outside_fuse_mount(controller, monkeypatch, tmp_path):
    application, session = controller
    image = tmp_path / ".mount_Captivate" / "usr" / "lib" / "captivate"
    bundle = image / "helper"
    (bundle / "_internal").mkdir(parents=True)
    (bundle / "captivate-helper").write_text("stand-in helper executable")
    (bundle / "_internal" / "libpython.so").write_bytes(b"stand-in Python library")
    monkeypatch.setattr("captivate.controller.sys.frozen", True, raising=False)
    monkeypatch.setattr("captivate.controller.sys.executable", str(image / "captivate"))
    monkeypatch.setenv("APPIMAGE", str(tmp_path / "Captivate.AppImage"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    session.recover()
    helper = Path(session.process.arguments()[0])
    staging = Path(session.helper_directory.name)
    assert not helper.is_relative_to(image)
    assert helper.is_relative_to(tmp_path / "cache")
    assert helper.read_text() == "stand-in helper executable"
    assert (helper.parent / "_internal" / "libpython.so").read_bytes() == b"stand-in Python library"
    assert staging.stat().st_mode & 0o777 == 0o700
    wait_for(application, lambda: not session.busy)
    assert session.helper_directory is None
    assert not staging.exists()


def test_appimage_staging_failure_closes_portal_and_removes_partial_copy(controller, monkeypatch, tmp_path):
    _application, session = controller
    monkeypatch.setattr("captivate.controller.sys.frozen", True, raising=False)
    monkeypatch.setattr("captivate.controller.sys.executable", str(tmp_path / "missing" / "captivate"))
    monkeypatch.setenv("APPIMAGE", str(tmp_path / "Captivate.AppImage"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    with socket.socket() as socket_:
        socket_.bind(("127.0.0.1", 0))
        port = socket_.getsockname()[1]
    with pytest.raises(OSError):
        session.start(SessionConfig(interface="wlan0", port=port))
    assert session.portal is None
    assert session.helper_directory is None
    assert not session.busy
    assert not list((tmp_path / "cache" / "captivate").iterdir())
