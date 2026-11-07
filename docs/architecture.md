# Architecture

Captivate has an unprivileged desktop process and an administrator-authorized networking helper.

## Desktop process

`captivate/ui.py` provides the Qt Widgets interface. `controller.py` manages the helper through asynchronous QProcess signals and JSON-line messages. `portal.py` serves visitor pages using a bounded, threaded HTTP server. Custom website files are read as the desktop user, never as root. File resolution rejects traversal, hidden paths, and symlinks escaping the selected root.

Previews bind only to `127.0.0.1` on a dynamically assigned port. Live serving uses a configurable unprivileged port, defaulting to 8080. The live server accepts hotspot-subnet peers only; the firewall additionally limits access on the hotspot interface. Built-in pages use local assets, escaped content, a peer-bound random form token, security headers, and confirmation rate limiting.

Local captive HTTP is necessary for legacy device detection. Do not use the local portal to collect reusable account passwords, card details, or sensitive personal information. Voucher codes and Wi-Fi passwords are not persisted by the desktop. The temporary NetworkManager keyfile containing the Wi-Fi password is root-readable and is removed during cleanup. Custom websites are operator-controlled static content and use a permissive script policy so local workflows can run.

## Networking helper

`helper.py` runs through `pkexec`. Configuration arrives over stdin, is independently validated, and is never executed as shell input. The source helper uses the system Python interpreter in isolated mode. Frozen packages contain a separate helper executable. AppImage launches stage that executable and its libraries in a private cache directory outside the user-mounted FUSE filesystem, then remove the copy after exit. Privilege authorization covers executing the helper; the desktop does not run as root.

The helper obtains an exclusive lock in `/run/captivate`, checks interface capabilities and subnet conflicts, records recovery state, and performs these operations:

Before mutation, sharing sessions obtain and validate IPv4 DNS server addresses from the selected uplink's NetworkManager configuration. Loopback resolvers and addresses in the hotspot subnet are excluded. The upstreams are bound to the selected uplink; public DNS servers are not forced.

After taking the exclusive helper lock and validating the request, startup removes leftover Captivate dnsmasq processes before creating a new session. Matching requires the system dnsmasq executable and exact Captivate configuration argument. A recorded interrupted session requires explicit recovery to restore its journaled network state.

1. Create and load a root-readable session-specific AP profile under `/run/NetworkManager/system-connections`, with manual IPv4 and disabled IPv6.
2. Install a dedicated `inet captivate` nftables table before accepting Wi-Fi clients.
3. Activate a 2.4 GHz hotspot on channel 6.
4. Enable IPv4 forwarding when an uplink is selected.
5. Start an interface-bound dnsmasq child for DHCP and DNS, with Captivate-prefixed configuration, lease, and log files under `/run/dnsmasq`. This path is permitted by Ubuntu's stock dnsmasq AppArmor profile.

Captivate does not use NetworkManager's `ipv4.method=shared`: its automatic DHCP/NAT would conflict with the portal's DNS and access policy.

## Access policy

The firewall redirects hotspot port-80 traffic to the portal until the source IP enters the expiring `allowed` set. DNS is served through the gateway. Direct gateway HTTP remains available after confirmation. Other incoming hotspot traffic to laptop services is blocked, and IPv6 forwarding is blocked. In sharing mode, only allowed clients may forward IPv4 traffic through the selected uplink; replies require established/related connection state. NAT is scoped to the hotspot subnet and selected uplink.

Intercepted HTTP requests for foreign origins redirect to the gateway before serving forms or assets. This keeps the confirmation flow on an origin that remains local after forwarding is granted.

Confirmation is evaluated server-side. The source address comes from the TCP peer, not a form field or forwarded header. The helper requires an active DHCP lease before allowing an address. Access is IP/lease-based and is intended for a small local utility; it is not resistant to deliberate IP/MAC spoofing or a replacement for enterprise gateway authentication. AP isolation is requested when NetworkManager supports it.

Welcome pages grant access after confirmation. Terms pages also require acceptance. Voucher pages require a configured reusable code. Custom websites can call the confirmation endpoint with a valid token; any stronger custom access policy requires a separate trusted server-side integration.

## Cleanup and recovery

Normal stop, GUI pipe closure, SIGINT, and SIGTERM trigger cleanup. dnsmasq is stopped, the temporary AP profile is deleted, the dedicated firewall table is removed, the original forwarding setting is restored, and the previous Wi-Fi profile is reactivated when one was present.

SIGKILL and power loss cannot run cleanup. **Recover interrupted session** reads the root-owned journal, terminates a matching recorded dnsmasq process, removes session resources, and restores the prior connection. Cleanup errors retain the journal and are displayed in the log.

On Ubuntu, a helper launched from Files can inherit Nautilus's named unconfined AppArmor label, which dnsmasq's receive-signal rule does not match. If a direct stop signal is denied and the inherited label is explicitly unconfined, the helper retries only the signal utility through `aa-exec -p unconfined`. Enforced profiles are not normalized. Each cleanup action is attempted independently; a DNS failure cannot prevent AP/firewall restoration. Recovery also locates an orphan using the exact dnsmasq executable and Captivate configuration argument when an older build removed its journal prematurely.

Existing UFW, firewalld, VPN, Docker, or other firewall policies can still block DHCP, DNS, redirected HTTP, or forwarding. An accept verdict in Captivate's table does not override drops in another base chain. Captivate does not flush or rewrite third-party firewall tables. Review the existing policy when troubleshooting.

Forwarding is a host-wide setting. Avoid concurrently starting another tool that changes it during a Captivate sharing session.
