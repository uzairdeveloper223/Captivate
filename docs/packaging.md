# Linux packaging

Captivate's build script freezes the GUI and networking helper separately using PyInstaller. The helper does not bundle Qt. The packages contain Python and the required Python/Qt modules; networking executables remain system dependencies.

## Build dependencies

```bash
.venv/bin/python -m pip install -e '.[dev]'
sudo apt install binutils dpkg-dev libxcb-cursor0 libxkbcommon-x11-0 libegl1 libgl1
```

Build on the oldest supported Linux base. PyInstaller does not bundle glibc, and an AppImage does not eliminate glibc compatibility limits. The initial Ubuntu 24.04 build conservatively requires glibc 2.39 or later, targeting Ubuntu 24.04+ and Debian 13+ on the matching architecture; these package targets still require runtime testing. Source installation or a rebuild on an older base is required for older distributions. Non-NetworkManager systems are not established targets.

## Debian / Ubuntu

```bash
.venv/bin/python scripts/build_linux.py --format deb
sudo apt install ./dist/captivate_0.1.0_amd64.deb
captivate
```

The application is installed in `/opt/captivate`, with a launcher and desktop integration in `/usr`. The Debian package declares runtime networking and graphics dependencies. Installation does not start a hotspot or change the firewall.

## AppImage

Download the architecture-matching appimagetool from [the official releases](https://github.com/AppImage/appimagetool/releases). Verify its SHA-256 against the release asset's published digest before use, then make it executable.

```bash
chmod +x /path/to/appimagetool-x86_64.AppImage
.venv/bin/python scripts/build_linux.py --format all --appimagetool /path/to/appimagetool-x86_64.AppImage
chmod +x dist/Captivate-0.1.0-x86_64.AppImage
./dist/Captivate-0.1.0-x86_64.AppImage
```

The AppImage still requires NetworkManager, dnsmasq, nftables, iproute2, pkexec, and a working graphical authentication agent. On a host without FUSE support, use AppImage's extraction-and-run mode:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./dist/Captivate-0.1.0-x86_64.AppImage
```

The bundle includes the helper inside the AppImage payload. Before authorization, Captivate copies the helper and its Python libraries into a private session directory under `${XDG_CACHE_HOME:-~/.cache}/captivate`. pkexec executes this copy because root cannot access an ordinary user's FUSE mount. The temporary helper directory is removed after the helper exits. Keep the desktop running for the duration of the session.

## Reuse an existing bundle

```bash
.venv/bin/python scripts/build_linux.py --format deb --reuse-bundle
```

Use this only when the source has not changed since freezing. Every completed package receives a `.sha256` file in `dist/`.

## Release checks

Validate desktop metadata, inspect package contents, run `--version` and `--diagnose`, launch the GUI on a graphical desktop, and perform the manual hotspot matrix on the target distribution. Preserve bundled third-party license files and publish corresponding source/rebuild instructions.
