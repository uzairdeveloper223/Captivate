#!/usr/bin/env python3
"""Serve a browser preview without administrator privileges or network changes."""

import argparse
import signal
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from captivate.config import SessionConfig  # noqa: E402
from captivate.portal import PortalServer  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", choices=("welcome", "terms", "voucher", "custom"), default="welcome")
    parser.add_argument("--directory", default="")
    parser.add_argument("--voucher", default="")
    arguments = parser.parse_args()
    server = PortalServer(SessionConfig(template=arguments.template,
                                        custom_directory=arguments.directory,
                                        vouchers=arguments.voucher), preview=True)
    done = threading.Event()
    signal.signal(signal.SIGINT, lambda *_args: done.set())
    signal.signal(signal.SIGTERM, lambda *_args: done.set())
    server.start()
    print(server.url, flush=True)
    done.wait()
    server.stop()


if __name__ == "__main__":
    main()
