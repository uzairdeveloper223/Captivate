# Contributing to Captivate

Contributions are welcome through issues and pull requests at [uzairdeveloper223/Captivate](https://github.com/uzairdeveloper223/Captivate).

## Development

Create a Python virtual environment and install `.[dev]`. Run the desktop with `.venv/bin/python -m captivate`. Keep changes consistent with the existing Qt Widgets interface and small Python modules.

Before submitting:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

Network changes require meaningful tests for validation, rollback, and access policy. Automated tests must not mutate the developer's Wi-Fi connection or system firewall. Record hardware-dependent results using `docs/testing.md`.

The GitHub checks workflow is manually triggered while hosted Actions billing is unavailable. Release binaries are compiled and checked locally using `scripts/build_linux.py`.

## Repository layout

```text
captivate/       Application modules and bundled portal assets
docs/           Architecture, usage, testing, and release notes
examples/       Example custom portal
packaging/      Desktop metadata and frozen application entry points
scripts/        Local packaging and preview tools
tests/          Unit and isolated-network integration checks
.github/        Repository automation configuration
```

Keep generated bundles in `build/` and release artifacts in `dist/`. These directories, virtual environments, caches, logs, and local design-tool state are ignored by Git. Publish compiled packages and checksums as release assets.

## Issue reports

Include the distribution/version, Captivate version, adapter/driver, portal template, uplink type, visitor OS/version, reproduction steps, and relevant exported session log. Remove credentials and private visitor information before publishing a log.

## Documentation and assets

Use formal project voice, accurate capability descriptions, and maintainer attribution. Keep page assets local for offline support. Use consistent SVG icons rather than emoji or decorative Unicode glyphs. Preserve third-party license notices in release artifacts.
