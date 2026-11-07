#!/usr/bin/env python3
"""Build self-contained Debian and AppImage releases without changing host networking."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from captivate import __version__  # noqa: E402


def command(arguments, **kwargs):
    print("Running: " + " ".join(str(item) for item in arguments), flush=True)
    subprocess.run([str(item) for item in arguments], check=True, cwd=ROOT, **kwargs)


def freeze() -> Path:
    output = ROOT / "build" / "frozen"
    command([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
             "--name", "captivate", "--distpath", output, "--workpath", ROOT / "build" / "pyinstaller-gui",
             "--specpath", ROOT / "build", "--paths", ROOT,
             "--add-data", f"{ROOT / 'captivate' / 'assets'}:captivate/assets",
             ROOT / "packaging" / "desktop_entry.py"])
    command([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
             "--name", "captivate-helper", "--distpath", output,
             "--workpath", ROOT / "build" / "pyinstaller-helper", "--specpath", ROOT / "build",
             "--paths", ROOT, ROOT / "packaging" / "helper_entry.py"])
    bundle = output / "captivate"
    shutil.copytree(output / "captivate-helper", bundle / "helper", dirs_exist_ok=True)
    return bundle


def copy_metadata(base: Path):
    applications = base / "usr" / "share" / "applications"
    icons = base / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps"
    metainfo = base / "usr" / "share" / "metainfo"
    for directory in (applications, icons, metainfo):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "packaging" / "dev.uzair.Captivate.desktop", applications)
    shutil.copy2(ROOT / "captivate" / "assets" / "captivate.svg", icons / "dev.uzair.Captivate.svg")
    shutil.copy2(ROOT / "packaging" / "dev.uzair.Captivate.metainfo.xml", metainfo)
    licenses = base / "usr" / "share" / "doc" / "captivate"
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", licenses / "copyright")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", licenses)
    # Qt for Python wheels include Qt/PySide/Shiboken license texts; preserve all of them.
    for package in ("PySide6", "shiboken6"):
        module = __import__(package)
        source = Path(module.__file__).parent
        for filename in source.rglob("*LICENSE*"):
            if filename.is_file():
                target = licenses / "bundled" / package / filename.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(filename, target)
    versions = {"Python": platform.python_version()}
    for name in ("PySide6-Essentials", "shiboken6", "PyInstaller"):
        installed = distribution(name)
        versions[name] = installed.version
        destination = licenses / "bundled" / name
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "METADATA").write_text(installed.read_text("METADATA") or "")
        for relative in installed.files or ():
            if "licenses" in relative.parts or relative.name.upper().startswith(("COPYING", "LICENSE")):
                source = Path(installed.locate_file(relative))
                if source.is_file():
                    shutil.copy2(source, destination / source.name)
    common = licenses / "bundled" / "license-texts"
    common.mkdir(parents=True, exist_ok=True)
    for name in ("LGPL-3", "GPL-3", "GPL-2"):
        source = Path("/usr/share/common-licenses") / name
        if not source.exists():
            raise RuntimeError(f"Missing {source}. Install the distribution's common license texts before building.")
        shutil.copy2(source, common)
    python_notice = Path(f"/usr/share/doc/python{sys.version_info.major}.{sys.version_info.minor}/copyright")
    if python_notice.exists():
        shutil.copy2(python_notice, common / "Python-copyright")
    (licenses / "build-versions.json").write_text(json.dumps(versions, indent=2) + "\n")


def deb(bundle: Path, architecture: str) -> Path:
    stage = ROOT / "build" / "deb"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(bundle, stage / "opt" / "captivate", symlinks=True)
    copy_metadata(stage)
    binary = stage / "usr" / "bin"
    binary.mkdir(parents=True)
    (binary / "captivate").symlink_to("/opt/captivate/captivate")
    control = stage / "DEBIAN"
    control.mkdir()
    size = sum(file.stat().st_size for file in stage.rglob("*") if file.is_file()) // 1024
    (control / "control").write_text(f'''Package: captivate
Version: {__version__}
Section: net
Priority: optional
Architecture: {architecture}
Maintainer: Uzair <uzairdeveloper223@users.noreply.github.com>
Homepage: https://uzair.is-a.dev
Installed-Size: {size}
Depends: network-manager, dnsmasq-base, nftables, pkexec, iproute2, libxcb-cursor0, libxkbcommon-x11-0, libegl1, libgl1, libc6 (>= {platform.libc_ver()[1]})
Recommends: iw
Description: Customizable Wi-Fi captive portals for Linux
 A Python and Qt desktop utility for hosting offline portals and optional
 gated internet sharing through a separate network uplink.
''')
    output = ROOT / "dist" / f"captivate_{__version__}_{architecture}.deb"
    temporary = output.with_name(output.name + ".partial")
    command(["dpkg-deb", "--root-owner-group", "--build", stage, temporary])
    temporary.replace(output)
    return output


def appimage(bundle: Path, tool: Path, architecture: str) -> Path:
    stage = ROOT / "build" / "Captivate.AppDir"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(bundle, stage / "usr" / "lib" / "captivate", symlinks=True)
    copy_metadata(stage)
    shutil.copy2(ROOT / "packaging" / "dev.uzair.Captivate.desktop", stage)
    shutil.copy2(ROOT / "captivate" / "assets" / "captivate.svg", stage / "dev.uzair.Captivate.svg")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(str(ROOT / "captivate" / "assets" / "captivate.svg"))
    if not renderer.isValid():
        raise RuntimeError("The Captivate icon is invalid.")
    image = QImage(256, 256, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    image.setText("impeccable:prompt", "Origin: captivate/assets/captivate.svg, original Captivate vector icon "
                  "authored by Uzair, MIT license. Rendered to a transparent 256x256 PNG with QSvgRenderer.")
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    icon = stage / "dev.uzair.Captivate.png"
    if not image.save(str(icon)):
        raise RuntimeError("Unable to render the AppImage thumbnail icon.")
    (stage / ".DirIcon").symlink_to(icon.name)
    apprun = stage / "AppRun"
    apprun.write_text('''#!/bin/sh
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "$HERE/usr/lib/captivate/captivate" "$@"
''')
    apprun.chmod(0o755)
    output = ROOT / "dist" / f"Captivate-{__version__}-{architecture}.AppImage"
    temporary = output.with_name(output.stem + ".partial.AppImage")
    temporary.unlink(missing_ok=True)
    environment = dict(os.environ, ARCH=architecture, APPIMAGE_EXTRACT_AND_RUN="1")
    command([tool.resolve(), "--no-appstream", stage, temporary], env=environment)
    temporary.chmod(0o755)
    temporary.replace(output)
    return output


def record_artifact(output: Path):
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest}  {output.name}\n")
    print(f"Built {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("deb", "appimage", "all"), default="all")
    parser.add_argument("--appimagetool", type=Path, default=shutil.which("appimagetool"))
    parser.add_argument("--reuse-bundle", action="store_true", help="Reuse build/frozen/captivate")
    args = parser.parse_args()
    machine = platform.machine()
    if machine not in ("x86_64", "aarch64"):
        parser.error("Builds currently support x86_64 and aarch64 hosts.")
    if args.format in ("all", "appimage") and not args.appimagetool:
        parser.error("Provide --appimagetool /path/to/appimagetool.AppImage. See docs/packaging.md.")
    (ROOT / "dist").mkdir(exist_ok=True)
    bundle = ROOT / "build" / "frozen" / "captivate" if args.reuse_bundle else freeze()
    if not (bundle / "captivate").exists():
        parser.error("The frozen bundle is missing. Run without --reuse-bundle.")
    if args.format in ("all", "deb"):
        record_artifact(deb(bundle, "amd64" if machine == "x86_64" else "arm64"))
    if args.format in ("all", "appimage"):
        record_artifact(appimage(bundle, Path(args.appimagetool), machine))


if __name__ == "__main__":
    main()
