# Research sources

The initial implementation was informed by the following primary documentation, consulted in November 2026.

| Source | Implementation relevance |
| --- | --- |
| [NetworkManager Wi-Fi settings](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html) | AP mode, 2.4 GHz band, channel selection, and optional client isolation. |
| [NetworkManager IPv4 settings](https://networkmanager.dev/docs/api/latest/settings-ipv4.html) | Manual addressing instead of automatic shared-mode DHCP/NAT. |
| [dnsmasq manual](https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html) | Interface binding, DHCP pool/options, wildcard offline DNS, and explicit upstream DNS. |
| [nftables NAT documentation](https://wiki.nftables.org/wiki-nftables/index.php/Performing_Network_Address_Translation_(NAT)) | HTTP redirect and uplink-scoped masquerading. |
| [RFC 8908: Captive Portal API](https://www.rfc-editor.org/rfc/rfc8908) | Captive status format and trusted HTTPS requirement. |
| [RFC 8910: Captive-Portal Identification](https://www.rfc-editor.org/rfc/rfc8910) | DHCP option 114 advertises an API URI; legacy interception remains necessary. |
| [Android captive portal API support](https://developer.android.com/about/versions/11/features/captive-portal) | API support and fallback HTTP/HTTPS probe detection. |
| [Android Custom Tabs captive portal guidance](https://source.android.com/docs/core/connect/android-custom-tabs-captive-portal) | Valid HTTPS certificates and probe-result inconsistencies. |
| [Apple: Modernize your captive network](https://developer.apple.com/news?id=q78sq5rv) | iOS/macOS captive identification and session-status requirements. |
| [Apple: Use captive Wi-Fi networks](https://support.apple.com/en-us/102554) | Visitor options for remaining on a network without internet. |
| [Microsoft captive portal detection](https://learn.microsoft.com/en-us/windows-hardware/drivers/mobilebroadband/captive-portals) | Windows captive-network behavior and HTTP redirection. |
| [Qt for Python QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html) | Asynchronous helper I/O and GUI responsiveness. |
| [Qt for Python deployment](https://doc.qt.io/qtforpython-6/deployment/index.html) | Desktop bundling approaches and Linux dependencies. |
| [PyInstaller specification files](https://pyinstaller.org/en/stable/spec-files.html) | Separate frozen GUI/helper executables and resource collection. |
| [AppImage manual packaging](https://docs.appimage.org/packaging-guide/manual.html) | AppDir layout, launcher, icons, and appimagetool. |
| [Ubuntu aa-exec manual](https://manpages.ubuntu.com/manpages/noble/en/man1/aa-exec.1.html) | Profile selection for a stop-signal utility when a named unconfined desktop-launcher label is inherited. |

These sources explain the network mechanisms and platform constraints. They do not establish tested compatibility for Captivate on every operating system or distribution.
