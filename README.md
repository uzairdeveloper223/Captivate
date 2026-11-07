# Captivate

<img src="captivate/assets/captivate.svg" alt="Captivate icon" width="80" height="80">

**Customizable Wi-Fi captive portals from a Linux desktop.**

Captivate turns a compatible Wi-Fi adapter into a hotspot and publishes a page to visitors joining it. Use a built-in welcome, terms, or voucher page, or serve a local website. With a separate internet connection, visitor confirmation can unlock timed internet access.

Maintained by **Uzair** · [Website](https://uzair.is-a.dev) · [GitHub](https://github.com/uzairdeveloper223) · MIT license

## Features

- Python desktop application built with PySide6 / Qt Widgets.
- Offline-first pages with bundled styles and SVG icons.
- Welcome, terms-of-access, and reusable voucher templates.
- Custom static websites, including HTML, CSS, JavaScript, and local assets.
- Browser preview without administrator privileges or hotspot activation.
- Optional gated IPv4 internet sharing through Ethernet, USB tethering, or a second network adapter.
- Configurable session duration, active DHCP lease list, and session logs.
- Administrator-authorized network helper, automatic shutdown cleanup, and interrupted-session recovery.
- Debian/Ubuntu and AppImage build tooling.

## Requirements

- Linux with NetworkManager and a Wi-Fi adapter supporting AP mode.
- Python 3.11+ for source installations.
- `nmcli`, `dnsmasq`, `nft`, `pkexec`, and `ip`; `iw` is optional for additional diagnostics.
- A graphical desktop with a working PolicyKit authentication agent.
- A separate network uplink for internet sharing. Offline page hosting does not need one.

The initial development target is Ubuntu 24.04 on x86_64. Other NetworkManager-based distributions are expected to work when the dependencies are available, but require independent testing. Client devices can use Android, iOS, Windows, macOS, or Linux; Captivate itself runs on Linux.

## Install a release

Download the AppImage or Debian package from [GitHub Releases](https://github.com/uzairdeveloper223/Captivate/releases/latest). Version 0.1.0 packages target **x86_64, Ubuntu 24.04+ or Debian 13+, and glibc 2.39+**.

For Debian or Ubuntu, install the downloaded package:

```bash
sudo apt install ./captivate_0.1.0_amd64.deb
captivate
```

For the AppImage, install its system networking dependencies, then run it:

```bash
sudo apt install network-manager dnsmasq-base nftables pkexec iproute2 iw
chmod +x Captivate-0.1.0-x86_64.AppImage
./Captivate-0.1.0-x86_64.AppImage
```

Each release includes `SHA256SUMS`. Place it beside the downloaded assets and verify the files present in that directory:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

See [Packaging](docs/packaging.md) for AppImage extraction mode and build instructions.

## Run from source

On Debian or Ubuntu:

```bash
sudo apt install python3-venv network-manager dnsmasq-base nftables pkexec iproute2 iw libxcb-cursor0 libxkbcommon-x11-0 libegl1 libgl1
git clone https://github.com/uzairdeveloper223/Captivate.git
cd Captivate
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m captivate
```

Run the desktop as a normal user. Captivate requests administrator authorization only when starting or recovering a network session.

Read-only system diagnostics:

```bash
.venv/bin/python -m captivate --diagnose
```

## Host a portal

1. Enable Wi-Fi in the operating system's network settings.
2. Open **Hotspot**, select a compatible adapter, and enter the network name. An empty password creates an open hotspot; a password enables WPA2-Personal.
3. Leave the uplink set to **Offline** for local hosting, or select a separate connected interface for internet sharing.
4. Open **Portal page**, select a template, and edit its content. For a custom site, select a folder containing `index.html`.
5. Select **Preview in browser** to verify the page without changing networking.
6. Select **Start hotspot** and authorize the helper.
7. Join the hotspot from a visitor device. If the operating system does not show a sign-in prompt, open `http://10.42.0.1/` or the configured gateway address.
8. Select **Stop hotspot** to remove the session and restore the previous connection.

Starting a hotspot replaces the selected adapter's existing Wi-Fi connection. Download source dependencies and build tools before switching a single-adapter laptop into hotspot mode.

## Captive-portal behavior

Captivate uses DHCP, local DNS, and HTTP redirection to trigger legacy captive-network detection. In offline mode, DNS resolves names to the hotspot gateway and forwarding is blocked. In sharing mode, DNS uses the selected uplink's IPv4 resolvers; unauthenticated HTTP requests are redirected and forwarding is blocked until confirmation. Authorized clients can use the selected uplink for the configured duration.

Automatic prompts are device-dependent. HTTPS is not intercepted. A fully offline hotspot continues to have no internet after confirmation, and phones may offer to keep using mobile data or leave the network. Select the device's option to stay connected when testing local content.

The local `/captivate/api` endpoint exposes portal state for inspection. Captivate does **not** advertise DHCP option 114: RFC 8908 requires a trusted HTTPS API, which an arbitrary offline laptop cannot provide by default.

## Paid access and custom workflows

Voucher pages support manually issued access codes, including codes sold separately by an operator. Codes are reusable throughout the running session and are not payment receipts.

Custom pages can display a paywall, event information, a consent flow, or another locally hosted experience. Automated payment verification is not included in version 0.1.0. A payment button alone cannot confirm a transaction or enforce paid access. External checkout also requires reachable internet, such as the visitor's mobile connection; the unauthenticated hotspot does not include a payment-provider allowlist.

See [Custom portals](docs/custom-portals.md) and [the included example](examples/custom-portal).

## Build packages

```bash
.venv/bin/python scripts/build_linux.py --format deb
.venv/bin/python scripts/build_linux.py --format all --appimagetool /path/to/appimagetool-x86_64.AppImage
```

Outputs are written to `dist/`. See [Packaging](docs/packaging.md) for dependencies, compatibility, and installation instructions.

## Testing

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

The automated suite checks portal flows, rejection paths, file containment, configuration validation, asynchronous helper acknowledgments, and cleanup behavior. Optional system checks exercise dnsmasq and nftables inside disposable user, mount, and network namespaces. It does not activate a hotspot or change the host firewall. Hardware and operating-system detection require [manual testing](docs/testing.md).

## Documentation

- [Architecture and networking](docs/architecture.md)
- [Custom portals](docs/custom-portals.md)
- [Manual testing and troubleshooting](docs/testing.md)
- [Version 0.1.0 verification](docs/verification.md)
- [Version 0.1.0 release notes](docs/releases/v0.1.0.md)
- [Linux packaging](docs/packaging.md)
- [Research sources](docs/research.md)
- [Contributing](CONTRIBUTING.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## License

Captivate is released under the [MIT license](LICENSE). Qt, PySide6, Shiboken, and other dependencies retain their own licenses.
