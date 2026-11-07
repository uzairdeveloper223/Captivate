# Manual testing and troubleshooting

Live hotspot testing is performed manually. Automated tests do not activate Wi-Fi profiles or change the firewall.

## Initial development machine

- Lenovo ThinkPad X390, Ubuntu 24.04, x86_64.
- Intel CNVi / Wireless-AC, iwlwifi driver, interface `wlp0s20f3`.
- AP mode supported on 2.4 GHz.
- Initial 5 GHz channels reported `no IR`; the implementation uses 2.4 GHz.
- A phone Ethernet/USB uplink was later detected as `enxc6bd1b939c85` with a default IPv4 route. Interface names may change between connections.
- Wi-Fi was software-blocked after switching to phone tethering. Enable it from system network settings before testing.

## Offline session

1. Choose the offline uplink option and a welcome page.
2. Start the hotspot and join it from a second device.
3. Check whether a sign-in notification or mini-browser appears.
4. If needed, open the gateway's `http://` address explicitly.
5. Verify the title, message, and button. Confirm the visit and verify that the page states no internet is provided.
6. On the phone, choose the option to stay connected without internet.
7. Confirm the device appears in **Devices** and that its access status changes after confirmation.
8. Stop the hotspot; confirm the AP disappears and the previous connection returns.

## Internet-sharing session

1. Connect a separate uplink and ensure the laptop can use it.
2. Choose that interface in Captivate and select the terms or voucher template.
3. Join from another device. Verify that internet traffic is blocked before confirmation.
4. Try an invalid voucher or missing terms acceptance. Access must remain blocked.
5. Complete the valid flow and check both HTTP and HTTPS internet access.
6. Use a short duration to verify that access expires and a new HTTP request returns to the portal.
7. Stop the session and confirm that the phone uplink remains usable on the laptop.

Test Android, iOS, Windows, macOS, and Linux separately. Record OS version, notification behavior, and whether the direct address works. Do not treat one device's result as universal compatibility.

## Custom page

Select `examples/custom-portal`. Verify local CSS and JavaScript load, the button becomes available, and confirmation works. Try your own folder with nested assets. A static paywall should be evaluated separately from access-policy enforcement.

## Failure paths

- Cancel administrator authorization and verify the GUI returns to a stopped/error state.
- Choose an overlapping subnet and verify startup refuses it before changing the adapter.
- Occupy the portal port and verify startup reports the conflict.
- Close the application during a live session and verify cleanup.
- If a helper was killed abruptly, use **Recover interrupted session** before starting again.

## Common issues

**Adapter unavailable:** enable Wi-Fi, check hardware airplane-mode controls, and refresh adapters. `nmcli radio wifi` and `rfkill list` are read-only diagnostics.

**No prompt:** devices cache connectivity results, use vendor-specific probes, or prefer cellular data. Forget and rejoin the hotspot, then open the gateway's HTTP address. A prompt is not guaranteed.

**No DHCP address:** inspect the session log, existing firewall policy, and dnsmasq availability. Captivate's dnsmasq binds only to the selected interface; other services using wildcard DNS/DHCP sockets can conflict.

**DNS address already in use:** the current helper removes leftover Captivate dnsmasq processes under its exclusive session lock before creating a new hotspot. It checks the system dnsmasq executable and exact Captivate configuration argument. A journaled interrupted session still requires the recovery action. Other DNS services retain their own configuration; a remaining conflict is reported in the startup log.

**Sharing fails after confirmation:** verify the selected interface has a default IPv4 route. The startup log identifies the uplink and its IPv4 DNS servers, obtained from NetworkManager. Some mobile uplinks block public DNS; use the current build rather than earlier builds that forced Cloudflare and Quad9. If no usable IPv4 DNS server is assigned, startup fails before network configuration is changed. Check UFW/firewalld/VPN forwarding policies. Captivate's allow rule cannot override a drop in another firewall table.

**Port conflict:** the source configuration supports a `port` value in the local settings file; the default is 8080. Change it while Captivate is stopped. The desktop preserves this advanced setting.

**PolicyKit dialog does not appear:** install/start the desktop's authentication agent and run Captivate from the graphical session.

**AppImage helper permission denied:** close the application and use the latest build, which stages the helper outside the FUSE mount. For an earlier build, launch it using `APPIMAGE_EXTRACT_AND_RUN=1 ./Captivate-0.1.0-x86_64.AppImage`.

**Permission denied when stopping dnsmasq:** Ubuntu may give applications launched from Files an inherited, named unconfined AppArmor label. The current build uses `aa-exec`, supplied by the AppArmor package, to normalize that already-unconfined label for the stop-signal utility when necessary. Stop failures are reported without preventing AP/firewall restoration, and retain the journal for recovery. The recovery action also checks for Captivate's orphaned dnsmasq process left by earlier builds, even when their journal was already removed.

**Cleanup requires recovery:** leave the recorded journal intact and use the recovery action. Session state is stored under `/run/captivate`, not in the project directory.
