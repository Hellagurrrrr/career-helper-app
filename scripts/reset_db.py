#!/usr/bin/env python3
"""Reset the local SQLite database to the shipped initial snapshot.

    python scripts/reset_db.py            # overwrite the local DB with the initial one
    python scripts/reset_db.py --backup   # copy the current DB aside first

Cross-platform (Windows, macOS, Linux). The target path is read from settings
(``CAREER_LOCAL_DATABASE_PATH``), so it stays in sync with the running app.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INITIAL = ROOT / "app" / "data" / "career_helper_initial.sqlite3"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset the local database to the initial snapshot."
    )
    parser.add_argument(
        "--backup", action="store_true", help="Back up the current database before overwriting."
    )
    args = parser.parse_args()

    from app.core.config import settings

    target = (ROOT / settings.local_database_path).resolve()

    if not INITIAL.exists():
        sys.exit(f"Initial database not found: {INITIAL}")

    target.parent.mkdir(parents=True, exist_ok=True)

    if args.backup and target.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = target.with_name(f"{target.name}.bak-{stamp}")
        shutil.copyfile(target, backup)
        print(f"Backup created: {backup}")

    shutil.copyfile(INITIAL, target)
    print(f"Database reset from: {INITIAL}")
    print(f"Database written to: {target}")


if __name__ == "__main__":
    main()
