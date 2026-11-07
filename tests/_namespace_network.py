"""Packet-level integration runner, restricted to disposable user/network namespaces."""

import json
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from captivate.config import SessionConfig
from captivate.network import dnsmasq_config, firewall_rules, signal_dnsmasq


def command(*arguments):
    subprocess.run(arguments, check=True, stdout=subprocess.DEVNULL)


def http_server(address, port, body):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer((address, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def query_dns():
    name = b"".join(bytes([len(part)]) + part.encode() for part in "connectivitycheck.gstatic.com".split(".")) + b"\0"
    query = struct.pack("!HHHHHH", 123, 0x100, 1, 0, 0, 0) + name + struct.pack("!HH", 1, 1)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.settimeout(2)
        connection.sendto(query, ("10.42.0.1", 53))
        response, _ = connection.recvfrom(4096)
    assert struct.unpack("!HHHHHH", response[:12])[3] == 1
    answer = question_end(response)
    assert response[answer + 12:answer + 16] == socket.inet_aton("192.0.2.53"), response.hex()


def question_end(packet):
    offset = 12
    while packet[offset]:
        offset += packet[offset] + 1
    return offset + 5


def request(port):
    try:
        with socket.create_connection(("192.0.2.53", port), timeout=0.6) as connection:
            connection.sendall(b"GET /generate_204 HTTP/1.0\r\nHost: connectivitycheck.gstatic.com\r\n\r\n")
            response = b""
            while chunk := connection.recv(4096):
                response += chunk
            return response.split(b"\r\n\r\n", 1)[1].decode()
    except TimeoutError:
        return "blocked"


def peer(role):
    print("namespace-ready", flush=True)
    assert sys.stdin.readline().strip() == "configure"
    command("ip", "link", "set", "lo", "up")
    interface, address = ("client0", "10.42.0.20/24") if role == "visitor" else ("server0", "192.0.2.53/24")
    command("ip", "address", "add", address, "dev", interface)
    command("ip", "link", "set", interface, "up")
    if role == "visitor":
        command("ip", "route", "add", "default", "via", "10.42.0.1")
    else:
        http_server("192.0.2.53", 80, b"uplink")
        http_server("192.0.2.53", 443, b"uplink")
        dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dns.bind(("192.0.2.53", 53))

        def answer_dns():
            while True:
                query, client = dns.recvfrom(4096)
                response = query[:2] + struct.pack("!HHHHH", 0x8180, 1, 1, 0, 0) + query[12:question_end(query)]
                response += b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 0, 4) + socket.inet_aton("192.0.2.53")
                dns.sendto(response, client)

        threading.Thread(target=answer_dns, daemon=True).start()
    print("ready", flush=True)
    for _line in sys.stdin:
        query_dns()
        print(json.dumps({"http": request(80), "tcp443": request(443)}), flush=True)


def router(runtime):
    command("mount", "--bind", runtime, "/run/dnsmasq")
    command("ip", "link", "set", "lo", "up")
    children = []
    dnsmasq = None
    try:
        for role, interface, other, address in [
            ("uplink", "usb0", "server0", "192.0.2.1/24"),
            ("visitor", "wlan0", "client0", "10.42.0.1/24"),
        ]:
            child = subprocess.Popen(["unshare", "--net", sys.executable, __file__, role],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            children.append(child)
            assert child.stdout.readline().strip() == "namespace-ready"
            command("ip", "link", "add", interface, "type", "veth", "peer", "name", other)
            command("ip", "link", "set", other, "netns", str(child.pid))
            command("ip", "address", "add", address, "dev", interface)
            command("ip", "link", "set", interface, "up")
            child.stdin.write("configure\n")
            child.stdin.flush()
            assert child.stdout.readline().strip() == "ready"
        Path("/proc/sys/net/ipv4/ip_forward").write_text("1\n")
        config = SessionConfig(interface="wlan0", uplink="usb0")
        Path("/run/dnsmasq/captivate.conf").write_text(dnsmasq_config(config, Path("/run/dnsmasq"), upstream_dns=["192.0.2.53"]))
        subprocess.run(["nft", "-f", "-"], input=firewall_rules(config), text=True, check=True)
        http_server("10.42.0.1", 8080, b"portal")
        dnsmasq = subprocess.Popen(["dnsmasq", "--no-daemon", "--conf-file=/run/dnsmasq/captivate.conf", "--pid-file="],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(0.3)
        assert dnsmasq.poll() is None, dnsmasq.communicate()[1]
        visitor = children[-1]

        def check(expected):
            visitor.stdin.write("check\n")
            visitor.stdin.flush()
            result = json.loads(visitor.stdout.readline())
            assert result == expected, result

        check({"http": "portal", "tcp443": "blocked"})
        command("nft", "add", "element", "inet", "captivate", "allowed", "{", "10.42.0.20", "timeout", "2s", "}")
        check({"http": "uplink", "tcp443": "uplink"})
        time.sleep(2.1)
        check({"http": "portal", "tcp443": "blocked"})
        print("DNS relay, captive HTTP interception, gated forwarding/NAT, and access expiry passed.")
    finally:
        if dnsmasq and dnsmasq.poll() is None:
            signal_dnsmasq(dnsmasq.pid, signal.SIGTERM)
            dnsmasq.wait(timeout=5)
        for child in children:
            child.terminate()
            child.wait(timeout=5)


if __name__ == "__main__":
    assert os.stat("/proc/self/ns/net").st_ino != int(os.environ["CAPTIVATE_TEST_HOST_NETNS"]), "A disposable network namespace is required."
    mapping = Path("/proc/self/uid_map").read_text().split()
    assert len(mapping) == 3 and mapping[0] == "0" and mapping[2] == "1", "A mapped-root user namespace is required."
    if sys.argv[1] == "router":
        router(sys.argv[2])
    else:
        peer(sys.argv[1])
