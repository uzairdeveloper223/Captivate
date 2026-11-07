"""Validated session configuration and local preferences."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from ipaddress import IPv4Interface, ip_network
from pathlib import Path

TEMPLATES = {
    "welcome": ("Welcome", "A simple welcome page with a continue button."),
    "terms": ("Terms of access", "Require visitors to accept your terms."),
    "voucher": ("Voucher access", "Require an access code before granting access."),
    "custom": ("Custom website", "Serve a local folder containing index.html."),
}
INTERFACE_RE = re.compile(r"[a-zA-Z0-9_.:-]{1,15}\Z")


@dataclass
class SessionConfig:
    interface: str = ""
    ssid: str = "Captivate"
    password: str = ""
    gateway: str = "10.42.0.1/24"
    uplink: str = ""
    template: str = "welcome"
    title: str = "Welcome to our network"
    message: str = "You are connected to a local hotspot. Continue to access this network."
    button: str = "Continue"
    terms: str = "Please use this network responsibly and respect other visitors."
    vouchers: str = ""
    custom_directory: str = ""
    session_minutes: int = 60
    port: int = 8080

    @property
    def address(self) -> str:
        return str(IPv4Interface(self.gateway).ip)

    @property
    def network(self):
        return IPv4Interface(self.gateway).network

    def validate(self, *, networking: bool = True) -> None:
        for key in self.__dataclass_fields__:
            value = getattr(self, key)
            expected = int if key in ("session_minutes", "port") else str
            if type(value) is not expected:
                raise ValueError(f"Invalid configuration value for {key}.")
        if networking:
            for name in (self.interface, self.uplink):
                if name and not INTERFACE_RE.fullmatch(name):
                    raise ValueError("Select a valid network interface.")
            if not self.interface:
                raise ValueError("Select a Wi-Fi adapter with hotspot support.")
            if self.interface == self.uplink:
                raise ValueError("The internet uplink must be a different network interface.")
        if not 1 <= len(self.ssid.encode("utf-8")) <= 32 or any(ord(c) < 32 for c in self.ssid):
            raise ValueError("The network name must contain 1–32 UTF-8 bytes and no control characters.")
        if self.password and not (
            8 <= len(self.password) <= 63 and all(32 <= ord(c) <= 126 for c in self.password)
        ):
            raise ValueError("The Wi-Fi password must contain 8–63 printable ASCII characters.")
        try:
            interface = IPv4Interface(self.gateway)
        except ValueError as exc:
            raise ValueError("Enter a private IPv4 gateway such as 10.42.0.1/24.") from exc
        private_ranges = (ip_network("10.0.0.0/8"), ip_network("172.16.0.0/12"), ip_network("192.168.0.0/16"))
        if interface.network.prefixlen != 24 or not any(
            interface.network.subnet_of(net) for net in private_ranges
        ) or interface.ip in (interface.network.network_address, interface.network.broadcast_address):
            raise ValueError("The gateway must be a usable address in a private /24 subnet.")
        if self.template not in TEMPLATES:
            raise ValueError("Select a supported portal template.")
        if not 1 <= self.session_minutes <= 1440:
            raise ValueError("Access duration must be between 1 and 1440 minutes.")
        if not 1024 <= self.port <= 65535:
            raise ValueError("The portal port must be between 1024 and 65535.")
        for value in (self.title, self.message, self.button, self.terms, self.vouchers):
            if not isinstance(value, str) or len(value) > 16000:
                raise ValueError("Portal text must be at most 16,000 characters per field.")
        if self.template != "custom" and (not self.title.strip() or not self.button.strip()):
            raise ValueError("Enter a portal title and button label.")
        if self.template == "voucher" and not self.vouchers.split():
            raise ValueError("Add at least one voucher code, one code per line.")
        if self.template == "custom":
            directory = Path(self.custom_directory).expanduser()
            if not directory.is_dir() or not (directory / "index.html").is_file():
                raise ValueError("Choose a website folder containing index.html.")

    def network_payload(self) -> dict:
        return {key: getattr(self, key) for key in (
            "interface", "ssid", "password", "gateway", "uplink", "session_minutes", "port"
        )}


def preferences_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "captivate" / "settings.json"


def save_preferences(config: SessionConfig) -> None:
    """Passwords and vouchers are session-only; persist only nonsensitive preferences."""
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    values = asdict(config)
    values.pop("password")
    values.pop("vouchers")
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(values, handle, indent=2)
    temporary.replace(path)


def load_preferences() -> SessionConfig:
    try:
        values = json.loads(preferences_path().read_text())
        allowed = SessionConfig.__dataclass_fields__.keys() - {"password", "vouchers"}
        defaults = SessionConfig()
        config = SessionConfig(**{key: value for key, value in values.items()
                                  if key in allowed and type(value) is type(getattr(defaults, key))})
        # Session-only vouchers and missing custom directories must not invalidate saved text.
        from dataclasses import replace
        replace(config, template="welcome", title=config.title or defaults.title,
                button=config.button or defaults.button).validate(networking=False)
        return config
    except (OSError, ValueError, TypeError, AttributeError):
        return SessionConfig()
