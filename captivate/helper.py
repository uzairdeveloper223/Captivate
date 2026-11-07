"""Privileged networking helper. JSON lines on stdin/stdout; no shell execution."""

from __future__ import annotations

import fcntl
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

from captivate.config import SessionConfig
from captivate.network import (
    DNS_RUNTIME,
    NetworkSession,
    run,
    stop_orphaned_dnsmasq,
    stop_recorded_dnsmasq,
)


class CommandReader:
    """Read bounded JSON lines from a pipe without Python's hidden read-ahead buffer."""

    def __init__(self, fd: int):
        self.fd = fd
        self.buffer = b""

    def readline(self, limit: int, timeout: float = 0.5) -> bytes | None:
        if b"\n" not in self.buffer:
            if len(self.buffer) > limit:
                raise ValueError("Helper command is too large.")
            readable, _, _ = select.select([self.fd], [], [], timeout)
            if not readable:
                return None
            chunk = os.read(self.fd, 4096)
            if not chunk:
                if self.buffer:
                    raise ValueError("Incomplete helper command.")
                return b""
            self.buffer += chunk
        if b"\n" not in self.buffer:
            if len(self.buffer) > limit:
                raise ValueError("Helper command is too large.")
            return None
        line, self.buffer = self.buffer.split(b"\n", 1)
        if len(line) > limit:
            raise ValueError("Helper command is too large.")
        return line + b"\n"


def parse_command(line: bytes) -> dict:
    message = json.loads(line)
    if not isinstance(message, dict):
        raise ValueError("Helper commands must be JSON objects.")
    return message


def emit(event: str, **values) -> None:
    try:
        print(json.dumps({"event": event, **values}), flush=True)
    except BrokenPipeError:
        # A closed GUI pipe must never prevent network cleanup.
        pass


def recovery_actions(state: dict):
    profile = state["profile"]

    def remove_profile():
        profiles = run(["nmcli", "--get-values", "NAME", "connection", "show"]).splitlines()
        if profile in profiles:
            run(["nmcli", "connection", "delete", profile])
        (Path("/run/NetworkManager/system-connections") / f"{profile}.nmconnection").unlink(missing_ok=True)

    def remove_table():
        result = subprocess.run(["nft", "list", "table", "inet", "captivate"], capture_output=True)
        if result.returncode == 0:
            run(["nft", "delete", "table", "inet", "captivate"])

    yield remove_profile
    yield remove_table
    if state.get("sharing", True) and state["forwarding"] == "0":
        yield lambda: Path("/proc/sys/net/ipv4/ip_forward").write_text("0\n")
    if state["previous"]:
        yield lambda: run(["nmcli", "--wait", "20", "connection", "up", "uuid", state["previous"],
                           "ifname", state["interface"]])


def recover(runtime: Path) -> None:
    journal = runtime / "session.json"
    if not journal.exists():
        # Older builds could remove the journal even when AppArmor denied the
        # dnsmasq stop signal. Match our exact executable/configuration only.
        removed = stop_orphaned_dnsmasq()
        if removed:
            for filename in ("captivate.conf", "captivate.leases", "captivate.log"):
                (DNS_RUNTIME / filename).unlink(missing_ok=True)
            emit("log", message="Removed an orphaned Captivate DHCP/DNS service.")
        else:
            emit("log", message="No interrupted session was found.")
        return
    state = json.loads(journal.read_text())
    profile = state["profile"]
    if not isinstance(profile, str) or not re.fullmatch(r"captivate-[0-9a-f]{32}", profile):
        raise ValueError("The session journal contains an invalid profile.")
    pid = state.get("dnsmasq_pid")
    errors = []
    if pid:
        try:
            stop_recorded_dnsmasq(int(pid))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc))
    try:
        stop_orphaned_dnsmasq()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        errors.append(str(exc))
    # Independently attempt each network action even if the DNS signal fails.
    for action in recovery_actions(state):
        try:
            action()
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc))
    if errors:
        raise RuntimeError("Recovery incomplete: " + "; ".join(errors))
    for filename in ("captivate.conf", "captivate.leases", "captivate.log"):
        (DNS_RUNTIME / filename).unlink(missing_ok=True)
    journal.unlink()
    emit("log", message="Interrupted session recovered.")


def main() -> int:
    if os.geteuid() != 0:
        emit("error", message="The network helper requires administrator authorization through pkexec.")
        return 1
    os.umask(0o077)
    # Restrict subprocess lookup to the system's executable directories.
    os.environ["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"
    os.environ["LC_ALL"] = "C"
    original_library_path = os.environ.pop("LD_LIBRARY_PATH_ORIG", "")
    os.environ.pop("LD_LIBRARY_PATH", None)
    if original_library_path:
        os.environ["LD_LIBRARY_PATH"] = original_library_path
    runtime = Path("/run/captivate")
    runtime.mkdir(mode=0o755, exist_ok=True)
    runtime.chmod(0o755)
    lock = (runtime / "lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        emit("error", message="Another Captivate session is already running.")
        return 1
    session = None
    stopping = False
    exit_code = 0

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        reader = CommandReader(sys.stdin.fileno())
        line = None
        while line is None and not stopping:
            line = reader.readline(65536)
        if stopping or not line:
            return 0
        request = parse_command(line)
        if request.get("command") == "recover":
            recover(runtime)
            return 0
        if request.get("command") != "start":
            raise ValueError("Unsupported helper command.")
        if (runtime / "session.json").exists():
            raise RuntimeError("An interrupted session needs recovery. Open Diagnostics and select Recover session.")
        allowed = SessionConfig().network_payload().keys()
        values = request["config"]
        if not isinstance(values, dict) or values.keys() - allowed:
            raise ValueError("Unsupported network configuration fields.")
        config = SessionConfig(**values)
        config.validate()
        removed = stop_orphaned_dnsmasq()
        if removed:
            emit("log", message=f"Removed {removed} leftover Captivate DHCP/DNS service(s) before startup.")
        session = NetworkSession(config, runtime, emit)
        session.start()
        last_clients = 0.0
        while not stopping:
            if session.dnsmasq.poll() is not None:
                raise RuntimeError("The DHCP/DNS service stopped unexpectedly.")
            if time.monotonic() - last_clients >= 3:
                emit("clients", clients=session.clients())
                last_clients = time.monotonic()
            line = reader.readline(4096)
            if line is None:
                continue
            if not line:
                break
            message = parse_command(line)
            if message.get("command") == "stop":
                break
            if message.get("command") == "allow":
                try:
                    session.allow(message["ip"])
                    emit("allowed", request_id=message["request_id"], ip=message["ip"], ok=True)
                except (ValueError, RuntimeError) as exc:
                    emit("allowed", request_id=message.get("request_id"), ok=False, message=str(exc))
            else:
                raise ValueError("Unsupported helper command.")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        emit("error", message=str(exc))
        exit_code = 1
    finally:
        if session:
            emit("stopping")
            success = session.cleanup()
            emit("stopped", clean=success)
            if not success:
                exit_code = 1
        lock.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
