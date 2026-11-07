import json
import signal
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from captivate.config import SessionConfig, load_preferences, save_preferences
from captivate.network import (
    NetworkSession,
    dnsmasq_config,
    firewall_rules,
    keyfile,
    matching_dnsmasq,
    signal_dnsmasq,
    uplink_dns,
)


@pytest.mark.parametrize("values", [
    {"interface": "wlan0; touch /tmp/x"},
    {"interface": "wlan0", "uplink": "wlan0"},
    {"gateway": "8.8.8.8/24"},
    {"gateway": "10.42.0.0/24"},
    {"gateway": "10.42.0.255/24"},
    {"gateway": "10.42.0.1/16"},
    {"session_minutes": 0},
    {"port": 80},
    {"password": "short"},
    {"ssid": "界" * 11},
    {"port": "8080"},
])
def test_invalid_network_configuration_rejected(values):
    config = SessionConfig(**{"interface": "wlan0", **values})
    with pytest.raises(ValueError):
        config.validate()


def test_preferences_never_persist_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_preferences(SessionConfig(ssid="Saved network", password="test-password", vouchers="test-code"))
    stored = (tmp_path / "captivate" / "settings.json").read_text()
    assert "test-password" not in stored and "test-code" not in stored
    loaded = load_preferences()
    assert loaded.ssid == "Saved network"
    assert loaded.password == loaded.vouchers == ""


def test_wrong_types_in_preferences_do_not_crash_the_desktop(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    folder = tmp_path / "captivate"
    folder.mkdir()
    (folder / "settings.json").write_text(json.dumps({"ssid": [], "session_minutes": "invalid", "title": "Saved title"}))
    loaded = load_preferences()
    assert loaded.ssid == "Captivate"
    assert loaded.session_minutes == 60
    assert loaded.title == "Saved title"


def test_invalid_advanced_preferences_fall_back_to_valid_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    folder = tmp_path / "captivate"
    folder.mkdir()
    (folder / "settings.json").write_text('{"gateway": "not-an-ip", "port": 80}')
    loaded = load_preferences()
    loaded.validate(networking=False)
    assert loaded.gateway == "10.42.0.1/24"


def test_offline_dns_and_dhcp_do_not_claim_https_capport(tmp_path):
    config = dnsmasq_config(SessionConfig(interface="wlan0"), tmp_path)
    assert "address=/#/10.42.0.1" in config
    assert "local=/#/" in config
    assert "except-interface=lo" in config
    assert "114" not in config


def test_sharing_uses_real_dns_and_gates_forwarding(tmp_path):
    config = SessionConfig(interface="wlan0", uplink="usb0")
    dns = dnsmasq_config(config, tmp_path, upstream_dns=["192.168.199.158"])
    rules = firewall_rules(config)
    assert "address=/#/" not in dns
    assert "server=192.168.199.158@usb0" in dns
    assert "1.1.1.1" not in dns and "9.9.9.9" not in dns
    assert 'iifname "wlan0" oifname "usb0" ip saddr @allowed accept' in rules
    assert 'iifname "wlan0" drop' in rules
    assert "443" not in rules
    assert "flush ruleset" not in rules


def test_dns_comes_from_selected_uplink_and_rejects_local_or_invalid_values(monkeypatch):
    calls = []

    def fake_run(arguments):
        calls.append(arguments)
        return "127.0.0.53\n::1\ninvalid\n10.42.0.1\n192.168.199.158\n192.168.199.158\n"

    monkeypatch.setattr("captivate.network.run", fake_run)
    assert uplink_dns(SessionConfig(interface="wlan0", uplink="usb0")) == ["192.168.199.158"]
    assert calls == [["nmcli", "--get-values", "IP4.DNS", "device", "show", "usb0"]]
    calls.clear()
    assert uplink_dns(SessionConfig(interface="wlan0")) == []
    assert not calls


def test_missing_uplink_dns_fails_before_network_mutation(monkeypatch, tmp_path):
    calls = []
    session = NetworkSession(SessionConfig(interface="wlan0", uplink="usb0"), tmp_path, lambda *_a, **_kw: None)
    monkeypatch.setattr(session, "check_routes", lambda: None)
    monkeypatch.setattr("captivate.network.run", lambda args, **_kw: calls.append(args) or "127.0.0.53")
    with pytest.raises(RuntimeError, match="DNS server"):
        session.start()
    assert calls == [["nmcli", "--get-values", "IP4.DNS", "device", "show", "usb0"]]
    assert not (tmp_path / "session.json").exists()


@pytest.mark.parametrize("label,normalizes", [("nautilus (unconfined)", True), ("restricted (enforce)", False)])
def test_apparmor_signal_fallback_only_normalizes_already_unconfined_labels(monkeypatch, label, normalizes):
    calls = []

    def denied(*_args):
        raise PermissionError("AppArmor denied the signal")

    monkeypatch.setattr("captivate.network.os.kill", denied)
    monkeypatch.setattr("captivate.network.Path.read_text", lambda _path: label)
    monkeypatch.setattr("captivate.network.shutil.which", lambda _name: "/usr/bin/aa-exec")
    monkeypatch.setattr("captivate.network.run", lambda args, **_kw: calls.append(args))
    if normalizes:
        signal_dnsmasq(123, signal.SIGTERM)
        assert calls == [["/usr/bin/aa-exec", "-p", "unconfined", "--", "/bin/kill", "-SIGTERM", "--", "123"]]
    else:
        with pytest.raises(PermissionError):
            signal_dnsmasq(123, signal.SIGTERM)
        assert not calls


@pytest.mark.parametrize("kind", ["captivate", "libvirt", "different-executable", "zombie"])
def test_orphan_identity_requires_system_dnsmasq_and_exact_captivate_config(monkeypatch, tmp_path, kind):
    binary = tmp_path / "system" / "dnsmasq"
    binary.parent.mkdir()
    binary.touch()
    process = tmp_path / "123"
    process.mkdir()
    config = "/var/lib/libvirt/dnsmasq/default.conf" if kind == "libvirt" else "/run/dnsmasq/captivate.conf"
    (process / "cmdline").write_bytes(f"dnsmasq\0--conf-file={config}\0".encode())
    target = binary
    if kind == "different-executable":
        target = tmp_path / "other" / "dnsmasq"
        target.parent.mkdir()
        target.touch()
    (process / "exe").symlink_to(target)
    (process / "stat").write_text("123 (dnsmasq) " + ("Z" if kind == "zombie" else "S"))
    monkeypatch.setattr("captivate.network.Path", lambda path: process if path == "/proc/123" else Path(path))
    monkeypatch.setattr("captivate.network.shutil.which", lambda _name: str(binary))
    assert matching_dnsmasq(123) == (kind == "captivate")


def test_keyfile_escapes_values_and_contains_no_extra_settings():
    config = SessionConfig(interface="wlan0", ssid="A network", password="pass\\word")
    content = keyfile(config, "captivate-test", "test-uuid")
    assert "ssid=A\\snetwork" in content
    assert "psk=pass\\\\word" in content
    assert "method=manual" in content


def test_gateway_excluded_from_dhcp_pool(tmp_path):
    config = SessionConfig(interface="wlan0", gateway="10.42.0.100/24")
    assert "dhcp-range=10.42.0.201,10.42.0.250" in dnsmasq_config(config, tmp_path)


def test_route_overlap_stops_before_mutation(monkeypatch, tmp_path):
    calls = []

    def fake_run(arguments, **_kwargs):
        calls.append(arguments)
        return json.dumps([{"dst": "10.42.0.0/24", "dev": "other0"}])

    monkeypatch.setattr("captivate.network.run", fake_run)
    session = NetworkSession(SessionConfig(interface="wlan0"), tmp_path, lambda *_a, **_k: None, dns_runtime=tmp_path)
    with pytest.raises(RuntimeError, match="overlaps"):
        session.check_routes()
    assert calls == [["ip", "-json", "-4", "route"]]


def test_cleanup_continues_after_firewall_failure(monkeypatch, tmp_path):
    calls = []
    events = []

    def fake_run(arguments, **_kwargs):
        calls.append(arguments)
        if arguments[0] == "nft":
            raise RuntimeError("firewall deletion failed")
        return ""

    monkeypatch.setattr("captivate.network.run", fake_run)
    monkeypatch.setattr("captivate.network.subprocess.run", lambda *_a, **_k: SimpleNamespace(returncode=0))
    session = NetworkSession(SessionConfig(interface="wlan0"), tmp_path, lambda event, **_k: events.append(event), dns_runtime=tmp_path)
    session.previous = "previous-uuid"
    session.table_created = True
    session.profile_created = True
    session.profile_path = tmp_path / "profile.nmconnection"
    session.journal()
    assert not session.cleanup()
    assert any("previous-uuid" in arguments for arguments in calls)
    assert (tmp_path / "session.json").exists()
    assert events[-1] == "error"


def test_cleanup_stops_ap_and_firewall_after_dnsmasq_permission_failure(monkeypatch, tmp_path):
    calls, events = [], []
    session = NetworkSession(SessionConfig(interface="wlan0"), tmp_path, lambda event, **kw: events.append((event, kw)), dns_runtime=tmp_path)
    session.dnsmasq = SimpleNamespace(pid=123, poll=lambda: None)
    session.profile_created = session.table_created = True
    session.profile_path = tmp_path / "profile.nmconnection"
    session.previous = "previous-uuid"
    session.journal()

    def denied(*_args):
        raise PermissionError("AppArmor denied the signal")

    monkeypatch.setattr("captivate.network.signal_dnsmasq", denied)
    monkeypatch.setattr("captivate.network.run", lambda args, **_kw: calls.append(args) or session.uuid)
    monkeypatch.setattr("captivate.network.subprocess.run", lambda *_a, **_kw: SimpleNamespace(returncode=0))
    assert not session.cleanup()
    assert ["nft", "delete", "table", "inet", "captivate"] in calls
    assert any("previous-uuid" in args for args in calls)
    assert (tmp_path / "session.json").exists()
    assert events[-1][0] == "error"


def test_access_grant_requires_active_dhcp_peer(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("captivate.network.run", lambda args, **_kw: calls.append(args))
    session = NetworkSession(SessionConfig(interface="wlan0"), tmp_path, lambda *_a, **_k: None, dns_runtime=tmp_path)
    (tmp_path / "captivate.leases").write_text(f"{int(time.time()) + 600} aa:bb:cc:dd:ee:ff 10.42.0.20 device *\n")
    with pytest.raises(ValueError, match="lease"):
        session.allow("10.42.0.21")
    assert not calls
    session.allow("10.42.0.20")
    assert "add" in calls[-1]
    assert "10.42.0.20" in calls[-1]
    assert "3600s" in calls[-1]


def test_expired_leases_excluded(tmp_path):
    session = NetworkSession(SessionConfig(interface="wlan0"), tmp_path, lambda *_a, **_k: None, dns_runtime=tmp_path)
    (tmp_path / "captivate.leases").write_text("1 aa:bb:cc:dd:ee:ff 10.42.0.20 stale *\n")
    assert session.clients() == []


def test_start_installs_firewall_before_ap_and_clears_stale_leases(monkeypatch, tmp_path):
    calls = []
    session = NetworkSession(SessionConfig(interface="wlan0"), tmp_path, lambda *_a, **_k: None, dns_runtime=tmp_path)
    session.profile_path = tmp_path / "profile.nmconnection"
    monkeypatch.setattr(session, "check_routes", lambda: None)

    def fake_run(arguments, **_kwargs):
        calls.append(arguments)
        if "GENERAL.CON-UUID" in arguments:
            return "--"
        if "UUID" in arguments:
            return session.uuid
        return ""

    process = SimpleNamespace(pid=123, poll=lambda: None, terminate=lambda: None, wait=lambda **_k: None)
    monkeypatch.setattr("captivate.network.run", fake_run)
    monkeypatch.setattr("captivate.network.subprocess.Popen", lambda *_a, **_k: process)
    monkeypatch.setattr("captivate.network.signal_dnsmasq", lambda *_a: None)
    monkeypatch.setattr("captivate.network.subprocess.run", lambda *_a, **_k: SimpleNamespace(returncode=0))
    monkeypatch.setattr("captivate.network.os.chown", lambda *_a: None)
    monkeypatch.setattr("captivate.network.time.sleep", lambda *_a: None)
    (tmp_path / "captivate.leases").write_text("stale lease")
    session.start()
    firewall = calls.index(["nft", "-f", "-"])
    activate = calls.index(["nmcli", "--wait", "25", "connection", "up", session.profile])
    assert firewall < activate
    assert (tmp_path / "captivate.leases").read_text() == ""
    assert session.profile_path.stat().st_mode & 0o777 == 0o600
    assert session.cleanup()
    assert not session.profile_path.exists()
    assert not (tmp_path / "session.json").exists()
