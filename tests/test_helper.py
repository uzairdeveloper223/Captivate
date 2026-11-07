import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from captivate.helper import CommandReader, main, parse_command, recover


@pytest.fixture
def command_pipe():
    reader_fd, writer_fd = os.pipe()
    yield CommandReader(reader_fd), writer_fd
    os.close(reader_fd)
    try:
        os.close(writer_fd)
    except OSError:
        pass


def test_commands_in_one_write_are_not_stranded_in_a_read_buffer(command_pipe):
    reader, writer = command_pipe
    os.write(writer, b'{"command":"allow"}\n{"command":"stop"}\n')
    assert parse_command(reader.readline(4096, 0))["command"] == "allow"
    assert parse_command(reader.readline(4096, 0))["command"] == "stop"
    assert reader.readline(4096, 0) is None


def test_fragmented_command_does_not_block_monitoring(command_pipe):
    reader, writer = command_pipe
    os.write(writer, b'{"command":')
    assert reader.readline(4096, 0) is None
    os.write(writer, b'"stop"}\n')
    assert parse_command(reader.readline(4096, 0)) == {"command": "stop"}


def test_closed_pipe_triggers_shutdown(command_pipe):
    reader, writer = command_pipe
    os.close(writer)
    assert reader.readline(4096, 0) == b""


def test_incomplete_command_on_closed_pipe_is_rejected(command_pipe):
    reader, writer = command_pipe
    os.write(writer, b'{"command":')
    assert reader.readline(4096, 0) is None
    os.close(writer)
    with pytest.raises(ValueError, match="Incomplete"):
        reader.readline(4096, 0)


def test_size_limit_applies_to_each_line(command_pipe):
    reader, writer = command_pipe
    os.write(writer, b'123456789\n')
    with pytest.raises(ValueError, match="large"):
        reader.readline(8, 0)


def test_helper_rejects_non_object_json():
    with pytest.raises(ValueError, match="objects"):
        parse_command(b'[]\n')


def test_recovery_attempts_network_restoration_and_retains_journal_on_signal_failure(monkeypatch, tmp_path):
    state = {"profile": "captivate-" + "a" * 32, "dnsmasq_pid": 123}
    journal = tmp_path / "session.json"
    journal.write_text(json.dumps(state))
    restored = []

    def denied(_pid):
        raise PermissionError("signal denied")

    monkeypatch.setattr("captivate.helper.stop_recorded_dnsmasq", denied)
    monkeypatch.setattr("captivate.helper.stop_orphaned_dnsmasq", lambda: 0)
    monkeypatch.setattr("captivate.helper.recovery_actions", lambda _state: [lambda: restored.append("network")])
    with pytest.raises(RuntimeError, match="Recovery incomplete: signal denied"):
        recover(tmp_path)
    assert restored == ["network"]
    assert journal.exists()


def test_recovery_checks_orphaned_dnsmasq_when_old_build_lost_journal(monkeypatch, tmp_path):
    stopped = []
    monkeypatch.setattr("captivate.network.stop_recorded_dnsmasq", lambda pid: stopped.append(pid))
    monkeypatch.setattr("captivate.helper.Path.glob", lambda _path, _pattern: [tmp_path / "123", tmp_path / "456"])
    recover(tmp_path)
    assert stopped == [123, 456]


@pytest.mark.parametrize("stop_error", [False, True], ids=["stale-service-removed", "cleanup-denied"])
def test_start_clears_orphan_before_creating_session_and_aborts_on_failure(monkeypatch, tmp_path, stop_error):
    actions = []
    messages = [json.dumps({"command": "start", "config": {"interface": "wlan0"}}).encode(), b'{"command":"stop"}']

    class FakeSession:
        def __init__(self, *_args):
            actions.append("created")
            self.dnsmasq = SimpleNamespace(poll=lambda: None)

        def start(self):
            actions.append("started")

        def clients(self):
            return []

        def cleanup(self):
            actions.append("cleaned")
            return True

    def remove_orphan():
        actions.append("removed-orphan")
        if stop_error:
            raise PermissionError("stop denied")
        return 1

    monkeypatch.setattr("captivate.helper.os.geteuid", lambda: 0)
    monkeypatch.setattr("captivate.helper.os.umask", lambda _mask: None)
    monkeypatch.setattr("captivate.helper.os.environ", os.environ.copy())
    monkeypatch.setattr("captivate.helper.signal.signal", lambda *_args: None)
    monkeypatch.setattr("captivate.helper.Path", lambda path: tmp_path if path == "/run/captivate" else Path(path))
    monkeypatch.setattr("captivate.helper.sys.stdin", SimpleNamespace(fileno=lambda: 0))
    monkeypatch.setattr("captivate.helper.CommandReader", lambda _fd: SimpleNamespace(readline=lambda _limit: messages.pop(0)))
    monkeypatch.setattr("captivate.helper.NetworkSession", FakeSession)
    monkeypatch.setattr("captivate.helper.stop_orphaned_dnsmasq", remove_orphan)
    monkeypatch.setattr("captivate.helper.emit", lambda *_args, **_kwargs: None)
    assert main() == (1 if stop_error else 0)
    assert actions == (["removed-orphan"] if stop_error else ["removed-orphan", "created", "started", "cleaned"])
