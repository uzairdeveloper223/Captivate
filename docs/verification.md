# Version 0.1.0 verification

Initial verification was performed on Ubuntu 24.04, x86_64, Python 3.12.3, with PySide6-Essentials 6.12.0. This record describes automated checks and the maintainer's manual acceptance of the release build.

## Automated checks

- 66 pytest cases passed, covering portal confirmation and rejection, terms, vouchers, escaped content, custom-file containment, invalid configuration, preference persistence, DHCP lease validation, rollback, bounded command parsing, asynchronous helper acknowledgments, AppImage helper staging/cleanup, uplink DNS selection, canonical portal origins, signal-failure recovery, and automatic orphan cleanup before startup.
- Ruff passed with the configured error, import, bugbear, and modernization rules.
- Welcome, terms, voucher, and custom-site flows were driven in headless Chrome at a 390×844 viewport. Voucher rejection and successful confirmation were checked. The welcome page was also captured at 1440×900 with keyboard focus. No JavaScript errors or horizontal page overflow were observed.
- Qt screens were captured offscreen at 1160×800 and 900×660. The minimum-size hotspot forms had no horizontal scroll range. Effective placeholder text was confirmed as opaque `#647386`.
- An independent UI finish review identified three material issues. A subsequent verdict scored placeholder contrast, minimum-width forms, and custom-site validation as resolved. The verdict applies to those fixes and does not certify hardware behavior.
- Desktop-entry validation and AppStream metadata validation passed.

## Isolated system checks

Offline and sharing-mode dnsmasq configurations passed the actual executable's syntax check. nftables rules were installed and grant-set add/delete/renewal commands succeeded inside disposable user, mount, and network namespaces.

The dnsmasq check used the permitted `/run/dnsmasq` pathname in a private mount namespace, exercising Ubuntu's installed AppArmor profile. The host network and firewall were not modified. Environments that prohibit user namespaces skip these optional system-plan tests.

A packet-level check connected a virtual visitor, router, and uplink in separate disposable network namespaces. It verified upstream DNS relay, HTTP interception before authorization, IPv4 forwarding and masquerading after an expiring grant, TCP port-443 blocking/allowance, and renewed blocking after expiry. Port 443 used a test TCP service; physical-device HTTPS browsing remains a manual check. A separate runtime regression started and stopped the real dnsmasq executable from Ubuntu's Nautilus AppArmor label.

During manual testing, the selected mobile uplink's DNS server answered a read-only query, while both previously forced public DNS servers timed out. Captivate now uses the uplink's NetworkManager-assigned IPv4 DNS servers. Kernel audit records also confirmed that AppArmor denied the old helper's dnsmasq stop signal; the targeted stop-signal retry and cleanup continuation are covered by regression checks.

A subsequent startup failed because the old orphan still held the hotspot's DNS/DHCP sockets. The maintainer-authorized recovery helper stopped that specific Captivate process successfully. Read-only process and socket checks confirmed its removal. Startup now performs the same targeted orphan cleanup before creating a new session, with regression checks for cleanup ordering, failure handling, and exclusion of unrelated executables/configurations.

## Manual acceptance

The first manual AppImage launch exposed a root-access failure inside the user-mounted FUSE filesystem. The corrected build stages the helper outside that mount. Regression tests verify its copied library payload, private directory permissions, failure cleanup, and removal after exit. A staged frozen helper also successfully loaded its bundled libraries and rejected unprivileged execution.

On 7 November 2026, the maintainer retested the rebuilt AppImage after the DNS, shutdown, and orphan-recovery fixes, reported that all tested functionality worked, and approved publication. This acceptance applies to the tested Ubuntu 24.04 x86_64 setup; a per-device result matrix was not supplied.

## Additional compatibility testing

The manual test matrix remains the procedure for validating other setups and recording device-specific results:

- AP activation and DHCP leases on the physical Wi-Fi adapter.
- Captive notifications on Android, iOS, Windows, macOS, and Linux.
- Internet blocking before confirmation, sharing afterward, and expiry under real traffic.
- Interaction with the host's existing firewall or VPN rules.
- PolicyKit authorization and cancellation in the graphical desktop.
- Connection restoration and recovery after an interrupted live session.
- Runtime compatibility on other distributions and architectures.

See [Manual testing and troubleshooting](testing.md) for the procedure.
