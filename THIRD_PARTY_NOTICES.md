# Third-party notices

Captivate's original source code and authored SVG icons are released under the MIT license, copyright 2026 Uzair.

## Qt for Python

PySide6 and Shiboken are provided by The Qt Company under LGPLv3/GPLv3 and commercial license options. Qt modules retain their respective licenses. Captivate uses Qt Core, Gui, Widgets, and SVG support through PySide6-Essentials.

Frozen releases include LGPLv3/GPLv3/GPLv2 texts, installed dependency metadata, and available wheel notices under `usr/share/doc/captivate/bundled` in the package payload. The application bundles dynamically loaded Qt libraries. Rebuild instructions are in `docs/packaging.md`; `build-versions.json` records exact Python, PySide, Shiboken, and PyInstaller versions. Obtain matching Qt/PySide/Shiboken sources through [Qt for Python](https://code.qt.io/cgit/pyside/pyside-setup.git/) and [Qt source archives](https://download.qt.io/archive/qt/).

## Python and packaging

Python is distributed under the Python Software Foundation license and associated notices. PyInstaller uses the GPL license with its bootloader exception permitting distribution of frozen applications under the application's own license. Other bundled libraries retain their licenses, as included by their distributions.

## System tools

NetworkManager, dnsmasq, nftables, PolicyKit, and iproute2 are installed and maintained by the operating system. Captivate calls their system executables and does not redistribute them in its application bundle.

## Desktop metadata

The AppStream metadata file `packaging/dev.uzair.Captivate.metainfo.xml` is dedicated to the public domain under CC0-1.0.
