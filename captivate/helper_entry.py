"""Source-install helper entry, invoked with the system interpreter's isolated mode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from captivate.helper import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
