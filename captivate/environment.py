"""Environment for system programs launched from a frozen application."""

import os
from contextlib import contextmanager


def system_environment() -> dict[str, str]:
    environment = dict(os.environ)
    original = environment.pop("LD_LIBRARY_PATH_ORIG", None)
    environment.pop("LD_LIBRARY_PATH", None)
    if original is not None:
        environment["LD_LIBRARY_PATH"] = original
    return environment


@contextmanager
def system_library_path():
    """Qt's desktop URL launcher inherits process environment rather than accepting one."""
    previous = os.environ.get("LD_LIBRARY_PATH")
    original = system_environment().get("LD_LIBRARY_PATH")
    if original is None:
        os.environ.pop("LD_LIBRARY_PATH", None)
    else:
        os.environ["LD_LIBRARY_PATH"] = original
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = previous
