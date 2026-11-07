"""Desktop and read-only command-line entry points."""

import argparse
import json
import sys

from captivate import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="Captivate — customizable Linux captive portals")
    parser.add_argument("--version", action="version", version=f"Captivate {__version__}")
    parser.add_argument("--diagnose", action="store_true", help="Print read-only networking diagnostics")
    arguments = parser.parse_args()
    if arguments.diagnose:
        from captivate.diagnostics import report
        print(json.dumps(report(), indent=2))
        return 0
    if sys.platform != "linux":
        parser.error("The hotspot backend currently supports Linux only.")
    from captivate.ui import MainWindow, create_application
    application = create_application()
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
