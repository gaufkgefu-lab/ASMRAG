"""Initialize the SQLite database schema."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import DEFAULT_DB_PATH, init_db


def main() -> None:
    init_db()
    print(f"Initialized database at: {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    main()
