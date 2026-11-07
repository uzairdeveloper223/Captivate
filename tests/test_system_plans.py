"""Exercise system parsers in disposable namespaces, never on the host network."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from captivate.config import SessionConfig
from captivate.network import dnsmasq_config, firewall_rules


@pytest.fixture(scope="module")
def isolated_namespace():
    for command in ("unshare", "nft", "dnsmasq", "mount"):
        if not shutil.which(command):
            pytest.skip(f"Optional system-plan check requires {command}.")
    command = ["unshare", "--user", "--map-root-user", "--mount", "--net"]
    probe = subprocess.run([*command, "true"], capture_output=True, text=True, timeout=5)
    if probe.returncode:
        pytest.skip("Disposable user/network namespaces are unavailable on this host.")
    if not Path("/run/dnsmasq").is_dir():
        pytest.skip("Stock dnsmasq runtime directory is unavailable for the isolated bind mount.")
    return command


@pytest.mark.parametrize("uplink", ["", "usb0"], ids=["offline", "sharing"])
def test_system_parsers_and_grant_commands_in_disposable_namespace(isolated_namespace, tmp_path, uplink):
    config = SessionConfig(interface="wlan0", uplink=uplink)
    (tmp_path / "captivate.conf").write_text(dnsmasq_config(config, Path("/run/dnsmasq"), upstream_dns=["192.168.199.158"] if uplink else []))
    script = r'''
import subprocess
import sys
subprocess.run(['mount', '--bind', sys.argv[1], '/run/dnsmasq'], check=True)
subprocess.run(['dnsmasq', '--test', '--conf-file=/run/dnsmasq/captivate.conf'], check=True)
subprocess.run(['nft', '-f', '-'], input=sys.stdin.read(), text=True, check=True)
subprocess.run(['nft', 'add', 'element', 'inet', 'captivate', 'allowed', '{', '10.42.0.20', 'timeout', '3600s', '}'], check=True)
output = subprocess.check_output(['nft', '--json', 'list', 'set', 'inet', 'captivate', 'allowed'], text=True)
assert '10.42.0.20' in output
subprocess.run(['nft', 'delete', 'element', 'inet', 'captivate', 'allowed', '{', '10.42.0.20', '}'], check=True)
subprocess.run(['nft', 'add', 'element', 'inet', 'captivate', 'allowed', '{', '10.42.0.20', 'timeout', '60s', '}'], check=True)
subprocess.run(['nft', 'delete', 'table', 'inet', 'captivate'], check=True)
'''
    result = subprocess.run([*isolated_namespace, "/usr/bin/python3", "-I", "-c", script, str(tmp_path)],
                            input=firewall_rules(config), text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, json.dumps({"stdout": result.stdout, "stderr": result.stderr})


def test_dnsmasq_can_stop_from_nautilus_label_in_disposable_namespace(isolated_namespace, tmp_path):
    if not shutil.which("aa-exec"):
        pytest.skip("AppArmor signal regression requires aa-exec.")
    probe = subprocess.run(["aa-exec", "-p", "nautilus", "--", "true"], capture_output=True, timeout=5)
    if probe.returncode:
        pytest.skip("The Ubuntu Nautilus AppArmor profile is not loaded.")
    (tmp_path / "captivate.conf").write_text("port=0\nno-resolv\nno-hosts\n")
    script = r'''
import subprocess
import sys
import time
from captivate.network import stop_recorded_dnsmasq
subprocess.run(['mount', '--bind', sys.argv[1], '/run/dnsmasq'], check=True)
process = subprocess.Popen(['dnsmasq', '--no-daemon', '--conf-file=/run/dnsmasq/captivate.conf', '--pid-file='], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
try:
    time.sleep(0.3)
    assert process.poll() is None, process.communicate()[1]
    assert stop_recorded_dnsmasq(process.pid)
    process.wait(timeout=5)
finally:
    if process.poll() is None:
        subprocess.run(['aa-exec', '-p', 'unconfined', '--', '/bin/kill', '-KILL', str(process.pid)], check=False)
        process.wait(timeout=5)
'''
    result = subprocess.run(["aa-exec", "-p", "nautilus", "--", *isolated_namespace,
                             sys.executable, "-c", script, str(tmp_path)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, json.dumps({"stdout": result.stdout, "stderr": result.stderr})


def test_packet_level_dns_forwarding_captive_gate_and_expiry(isolated_namespace, tmp_path):
    script = Path(__file__).with_name("_namespace_network.py")
    result = subprocess.run([*isolated_namespace, sys.executable, str(script), "router", str(tmp_path)],
                            capture_output=True, text=True, timeout=25,
                            env={**os.environ, "CAPTIVATE_TEST_HOST_NETNS": str(os.stat("/proc/self/ns/net").st_ino)})
    assert result.returncode == 0, json.dumps({"stdout": result.stdout, "stderr": result.stderr})
