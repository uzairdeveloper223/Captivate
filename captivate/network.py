"""Session-owned NetworkManager, DHCP, and firewall configuration."""

from __future__ import annotations

import json
import os
import pwd
import shutil
import signal
import subprocess
import time
from collections.abc import Sequence
from ipaddress import IPv4Address
from pathlib import Path
from uuid import uuid4

from captivate.config import SessionConfig

TABLE = "captivate"
DNS_RUNTIME = Path("/run/dnsmasq")


def keyfile(config: SessionConfig, profile: str, uuid: str) -> str:
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t").replace(" ", "\\s")

    text = f'''[connection]
id={profile}
uuid={uuid}
type=wifi
interface-name={config.interface}
autoconnect=false

[wifi]
mode=ap
ssid={escape(config.ssid)}
band=bg
channel=6

[ipv4]
method=manual
address1={config.gateway}
never-default=true

[ipv6]
method=disabled
'''
    if config.password:
        text += f'\n[wifi-security]\nkey-mgmt=wpa-psk\nproto=rsn;\npsk={escape(config.password)}\n'
    return text


def run(arguments: list[str], *, input_text: str | None = None, check: bool = True) -> str:
    result = subprocess.run(arguments, input=input_text, text=True, capture_output=True, timeout=35)
    if check and result.returncode:
        # Do not echo arguments: nmcli may contain a Wi-Fi password.
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"{arguments[0]} failed.")
    return result.stdout.strip()


def uplink_dns(config: SessionConfig) -> list[str]:
    """Use the selected link's resolvers, not public DNS that an uplink may block."""
    if not config.uplink:
        return []
    output = run(["nmcli", "--get-values", "IP4.DNS", "device", "show", config.uplink])
    servers = []
    for value in output.splitlines():
        try:
            address = IPv4Address(value.strip())
        except ValueError:
            continue
        if not (address.is_loopback or address.is_unspecified or address.is_multicast or address in config.network):
            if str(address) not in servers:
                servers.append(str(address))
    if not servers:
        raise RuntimeError("The selected uplink has no usable IPv4 DNS server. Check its NetworkManager DNS settings.")
    return servers


def dnsmasq_config(config: SessionConfig, runtime: Path, *, upstream_dns: Sequence[str] = ()) -> str:
    prefix = str(config.network.network_address).rsplit(".", 1)[0]
    # Choose a pool that does not contain the configurable gateway.
    gateway_octet = int(config.address.rsplit(".", 1)[1])
    start, end = (20, 200) if not 20 <= gateway_octet <= 200 else (201, 250)
    lines = [
        "bind-dynamic", f"interface={config.interface}", "except-interface=lo",
        f"listen-address={config.address}", "no-resolv", "no-hosts", "dhcp-authoritative",
        f"dhcp-range={prefix}.{start},{prefix}.{end},255.255.255.0,1h",
        f"dhcp-option=option:router,{config.address}",
        f"dhcp-option=option:dns-server,{config.address}",
        f"dhcp-leasefile={runtime / 'captivate.leases'}", "log-facility=-", "user=nobody",
        "address=/portal.home.arpa/" + config.address,
        "local=/portal.home.arpa/", "cache-size=0",
    ]
    if config.uplink:
        if not upstream_dns:
            raise ValueError("Internet sharing requires the uplink's IPv4 DNS servers.")
        lines.extend(f"server={IPv4Address(server)}@{config.uplink}" for server in upstream_dns)
    else:
        lines.extend([f"address=/#/{config.address}", "local=/#/"])
    # Option 114 requires a trusted HTTPS API. Do not advertise a noncompliant HTTP URI.
    return "\n".join(lines) + "\n"


def signal_dnsmasq(pid: int, signum: int) -> None:
    try:
        os.kill(pid, signum)
    except PermissionError:
        # Ubuntu's named *unconfined* launcher labels (e.g. Nautilus) are not
        # matched by dnsmasq's `signal (receive) peer=unconfined` rule. Only
        # normalize that already-unconfined label for this signal utility.
        label = Path("/proc/self/attr/current").read_text().strip()
        aa_exec = shutil.which("aa-exec")
        if not label.endswith(" (unconfined)") or not aa_exec:
            raise
        run([aa_exec, "-p", "unconfined", "--", "/bin/kill",
             f"-{signal.Signals(signum).name}", "--", str(pid)])
    except ProcessLookupError:
        pass


def matching_dnsmasq(pid: int) -> bool:
    try:
        process = Path(f"/proc/{pid}")
        return (b"--conf-file=/run/dnsmasq/captivate.conf" in process.joinpath("cmdline").read_bytes().split(b"\0")
                and process.joinpath("exe").resolve(strict=True) == Path(shutil.which("dnsmasq") or "/usr/sbin/dnsmasq").resolve(strict=True)
                and process.joinpath("stat").read_text().split(")", 1)[1].split()[0] != "Z")
    except (FileNotFoundError, ProcessLookupError):
        return False


def stop_recorded_dnsmasq(pid: int) -> bool:
    if not matching_dnsmasq(pid):
        return False
    signal_dnsmasq(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while matching_dnsmasq(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    if matching_dnsmasq(pid):
        signal_dnsmasq(pid, signal.SIGKILL)
        deadline = time.monotonic() + 5
        while matching_dnsmasq(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        if matching_dnsmasq(pid):
            raise RuntimeError("The recorded DHCP/DNS process could not be stopped.")
    return True


def stop_orphaned_dnsmasq() -> int:
    """Called under the helper lock, before a new session owns any DNS process."""
    removed = 0
    for process in Path("/proc").glob("[0-9]*"):
        if stop_recorded_dnsmasq(int(process.name)):
            removed += 1
    return removed


def firewall_rules(config: SessionConfig) -> str:
    interface = config.interface
    sharing = ""
    nat = ""
    if config.uplink:
        sharing = f'''
        iifname "{interface}" oifname "{config.uplink}" ip saddr @allowed accept
        iifname "{config.uplink}" oifname "{interface}" ip daddr @allowed ct state established,related accept
'''
        nat = f'''chain postrouting {{
        type nat hook postrouting priority srcnat; policy accept;
        oifname "{config.uplink}" ip saddr {config.network} masquerade
    }}'''
    return f'''table inet {TABLE} {{
    set allowed {{ type ipv4_addr; flags timeout; }}
    chain prerouting {{
        type nat hook prerouting priority dstnat - 10; policy accept;
        iifname "{interface}" ip daddr {config.address} tcp dport 80 redirect to :{config.port}
        iifname "{interface}" ip saddr != @allowed tcp dport 80 redirect to :{config.port}
        iifname "{interface}" udp dport 53 redirect to :53
        iifname "{interface}" tcp dport 53 redirect to :53
    }}
    chain input {{
        type filter hook input priority filter - 10; policy accept;
        iifname "{interface}" ip saddr {config.network} tcp dport {{ 53, {config.port} }} accept
        iifname "{interface}" udp dport {{ 53, 67 }} accept
        iifname "{interface}" ip protocol icmp accept
        iifname "{interface}" drop
    }}
    chain forward {{
        type filter hook forward priority filter - 10; policy accept;
        {sharing}
        iifname "{interface}" drop
        oifname "{interface}" drop
    }}
    {nat}
}}
'''


class NetworkSession:
    def __init__(self, config: SessionConfig, runtime: Path, emit, *, dns_runtime: Path = DNS_RUNTIME):
        self.config = config
        self.runtime = runtime
        self.emit = emit
        self.dns_runtime = dns_runtime
        self.uuid = str(uuid4())
        self.profile = "captivate-" + self.uuid.replace("-", "")
        self.profile_path = Path("/run/NetworkManager/system-connections") / f"{self.profile}.nmconnection"
        self.previous = ""
        self.forwarding = Path("/proc/sys/net/ipv4/ip_forward").read_text().strip()
        self.dnsmasq: subprocess.Popen | None = None
        self.table_created = False
        self.profile_created = False

    def check_routes(self) -> None:
        routes = json.loads(run(["ip", "-json", "-4", "route"]))
        for route in routes:
            destination = route.get("dst", "default")
            if destination == "default":
                continue
            from ipaddress import ip_network
            if ip_network(destination, strict=False).overlaps(self.config.network):
                raise RuntimeError(f"The hotspot subnet overlaps {destination}. Choose another private /24 gateway.")
        names = {item["ifname"] for item in json.loads(run(["ip", "-json", "link"]))}
        if self.config.interface not in names or (self.config.uplink and self.config.uplink not in names):
            raise RuntimeError("A selected network interface is no longer available. Refresh the adapter list.")
        support = run(["nmcli", "--get-values", "WIFI-PROPERTIES.AP", "device", "show", self.config.interface])
        if support != "yes":
            raise RuntimeError("The selected Wi-Fi adapter does not support access-point mode.")
        if self.config.uplink and not any(
            route.get("dst") == "default" and route.get("dev") == self.config.uplink for route in routes
        ):
            raise RuntimeError("The selected uplink has no default IPv4 route. Connect it before starting.")
        result = subprocess.run(["nft", "list", "table", "inet", TABLE], capture_output=True)
        if result.returncode == 0:
            raise RuntimeError("A Captivate firewall table already exists. Use Recover session in Diagnostics.")

    def journal(self) -> None:
        (self.runtime / "session.json").write_text(json.dumps({
            "profile": self.profile, "previous": self.previous,
            "interface": self.config.interface, "forwarding": self.forwarding,
            "dnsmasq_pid": self.dnsmasq.pid if self.dnsmasq else None,
            "sharing": bool(self.config.uplink),
        }))

    def start(self) -> None:
        self.check_routes()
        servers = uplink_dns(self.config)
        if servers:
            self.emit("log", message=f"Internet uplink: {self.config.uplink}; DNS: {', '.join(servers)}.")
        else:
            self.emit("log", message="Offline session: visitor confirmation does not enable internet access.")
        self.previous = run(["nmcli", "--get-values", "GENERAL.CON-UUID", "device", "show", self.config.interface])
        if self.previous == "--":
            self.previous = ""
        self.journal()
        self.emit("log", message="Creating a temporary NetworkManager hotspot profile.")
        self.profile_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.profile_path.write_text(keyfile(self.config, self.profile, self.uuid))
        self.profile_path.chmod(0o600)
        self.profile_created = True
        run(["nmcli", "connection", "load", str(self.profile_path)])
        # AP isolation is not available on every NetworkManager version.
        run(["nmcli", "connection", "modify", "--temporary", self.profile,
             "802-11-wireless.ap-isolation", "1"], check=False)
        self.emit("log", message="Installing Captivate's session firewall rules before activating Wi-Fi.")
        self.table_created = True
        run(["nft", "-f", "-"], input_text=firewall_rules(self.config))
        run(["nmcli", "--wait", "25", "connection", "up", self.profile])
        if self.config.uplink:
            Path("/proc/sys/net/ipv4/ip_forward").write_text("1\n")
        self.dns_runtime.mkdir(parents=True, exist_ok=True, mode=0o755)
        config_path = self.dns_runtime / "captivate.conf"
        config_path.write_text(dnsmasq_config(self.config, self.dns_runtime, upstream_dns=servers))
        # dnsmasq drops to nobody. This directory contains leases, not configuration secrets.
        leases = self.dns_runtime / "captivate.leases"
        leases.write_text("")
        os.chown(leases, pwd.getpwnam("nobody").pw_uid, -1)
        leases.chmod(0o600)
        run(["dnsmasq", "--test", f"--conf-file={config_path}"])
        self.dnsmasq = subprocess.Popen(
            ["dnsmasq", "--keep-in-foreground", f"--conf-file={config_path}", "--pid-file="],
            stdout=subprocess.DEVNULL, stderr=(self.dns_runtime / "captivate.log").open("w"),
        )
        self.journal()
        time.sleep(0.4)
        if self.dnsmasq.poll() is not None:
            raise RuntimeError((self.dns_runtime / "captivate.log").read_text().strip() or "dnsmasq failed to start.")
        self.emit("started", address=self.config.address, sharing=bool(self.config.uplink))

    def allow(self, address: str) -> None:
        from ipaddress import IPv4Address
        ip = IPv4Address(address)
        if ip not in self.config.network or str(ip) == self.config.address:
            raise ValueError("The visitor address is outside the hotspot network.")
        # Leases bind access to a DHCP-assigned peer, not a client-supplied form field.
        if str(ip) not in {client["ip"] for client in self.clients()}:
            raise ValueError("The visitor does not have an active hotspot DHCP lease.")
        run(["nft", "delete", "element", "inet", TABLE, "allowed", "{", str(ip), "}"], check=False)
        run(["nft", "add", "element", "inet", TABLE, "allowed",
             "{", str(ip), "timeout", f"{self.config.session_minutes * 60}s", "}"])

    def clients(self) -> list[dict]:
        clients = []
        try:
            lines = (self.dns_runtime / "captivate.leases").read_text().splitlines()
        except OSError:
            return clients
        for line in lines:
            fields = line.split()
            if len(fields) >= 4:
                expires, mac, address, hostname = fields[:4]
                if expires.isdigit() and (int(expires) == 0 or int(expires) > time.time()):
                    clients.append({"ip": address, "mac": mac, "hostname": hostname if hostname != "*" else "Unnamed device"})
        return clients

    def cleanup(self) -> bool:
        errors = []
        for action in self._cleanup_actions():
            try:
                action()
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                errors.append(str(exc))
        if errors:
            self.emit("error", message="Cleanup requires recovery: " + "; ".join(errors))
            return False
        try:
            self.profile_path.unlink(missing_ok=True)
            for filename in ("captivate.conf", "captivate.leases", "captivate.log"):
                (self.dns_runtime / filename).unlink(missing_ok=True)
            (self.runtime / "session.json").unlink(missing_ok=True)
        except OSError as exc:
            self.emit("error", message="Cleanup requires recovery: " + str(exc))
            return False
        self.emit("log", message="Session removed. The previous Wi-Fi connection has been restored.")
        return True

    def _cleanup_actions(self):
        yield self.stop_dnsmasq
        if self.profile_created:
            yield self.remove_profile
        if self.table_created:
            yield self.remove_table
        if self.config.uplink and self.forwarding == "0":
            yield lambda: Path("/proc/sys/net/ipv4/ip_forward").write_text("0\n")
        if self.previous:
            yield lambda: run(["nmcli", "--wait", "20", "connection", "up", "uuid", self.previous,
             "ifname", self.config.interface])

    def stop_dnsmasq(self):
        if self.dnsmasq and self.dnsmasq.poll() is None:
            signal_dnsmasq(self.dnsmasq.pid, signal.SIGTERM)
            try:
                self.dnsmasq.wait(timeout=5)
            except subprocess.TimeoutExpired:
                signal_dnsmasq(self.dnsmasq.pid, signal.SIGKILL)
                self.dnsmasq.wait(timeout=5)

    def remove_table(self):
        result = subprocess.run(["nft", "list", "table", "inet", TABLE], capture_output=True)
        if result.returncode == 0:
            run(["nft", "delete", "table", "inet", TABLE])

    def remove_profile(self):
        profiles = run(["nmcli", "--get-values", "UUID", "connection", "show"]).splitlines()
        if self.uuid in profiles:
            run(["nmcli", "connection", "delete", "uuid", self.uuid])
        self.profile_path.unlink(missing_ok=True)
