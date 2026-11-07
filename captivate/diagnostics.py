"""Read-only system capability discovery."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass

from captivate.environment import system_environment


def read_command(arguments: list[str]) -> str:
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=8, check=False,
                                env={**system_environment(), "LC_ALL": "C", "NO_COLOR": "1"})
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


@dataclass
class Adapter:
    name: str
    kind: str
    state: str
    ap: bool = False


def adapters() -> list[Adapter]:
    output = read_command(["nmcli", "--terse", "--escape", "no", "--fields", "DEVICE,TYPE,STATE", "device"])
    devices = []
    for line in output.splitlines():
        parts = line.rsplit(":", 2)
        if len(parts) != 3 or parts[1] not in ("wifi", "ethernet", "gsm"):
            continue
        name, kind, state = parts
        support = read_command(["nmcli", "--get-values", "WIFI-PROPERTIES.AP", "device", "show", name])
        devices.append(Adapter(name, kind, state, kind == "wifi" and support == "yes"))
    return devices


def report() -> dict:
    tools = {name: shutil.which(name) for name in ("nmcli", "dnsmasq", "nft", "pkexec", "ip", "iw")}
    devices = adapters()
    return {
        "system": platform.platform(),
        "python": platform.python_version(),
        "tools": tools,
        "adapters": [asdict(device) for device in devices],
        "ready": all(tools[name] for name in ("nmcli", "dnsmasq", "nft", "pkexec", "ip"))
        and any(device.ap for device in devices),
        "networkmanager": read_command(["nmcli", "--version"]),
        "routes": json.loads(read_command(["ip", "-json", "-4", "route"]) or "[]"),
    }
