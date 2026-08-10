"""One-off migration: read the old thesis_tracker.db (Thesis/ThesisCheck
tables, pre-vault) and write each thesis and its checks into the vault as
markdown notes. Re-runnable - the old database is read-only input and is
never modified, so running this twice just creates duplicate nodes (safe,
if wasteful; delete the duplicates by hand if that happens).
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.deps import Vault  # noqa: E402
from app.schemas import Source, Verdict  # noqa: E402
from app.services.agent import CheckResult  # noqa: E402
from app.services.notes import create_node, write_check_note  # noqa: E402

OLD_DB_PATH = Path(__file__).resolve().parent.parent / "thesis_tracker.db"


def main() -> None:
    if not OLD_DB_PATH.exists():
        print(f"No old database found at {OLD_DB_PATH}, nothing to migrate.")
        return

    Base.metadata.create_all(bind=engine)

    old_conn = sqlite3.connect(OLD_DB_PATH)
    old_conn.row_factory = sqlite3.Row

    vault = Vault(root=settings.vault_path)
    db = SessionLocal()

    theses = old_conn.execute(
        "SELECT id, ticker, thesis_text FROM theses ORDER BY created_at"
    ).fetchall()
    print(f"Found {len(theses)} theses to migrate.")

    for thesis in theses:
        node = create_node(
            db,
            vault,
            title=f"{thesis['ticker']} Thesis",
            body=thesis["thesis_text"],
            ticker=thesis["ticker"],
            tags=[],
        )
        print(f"  created node {node.id} for {thesis['ticker']}")

        checks = old_conn.execute(
            "SELECT verdict, reasoning, sources FROM thesis_checks "
            "WHERE thesis_id = ? ORDER BY created_at",
            (thesis["id"],),
        ).fetchall()
        for check in checks:
            sources_data = json.loads(check["sources"]) if check["sources"] else []
            result = CheckResult(
                verdict=cast(Verdict, check["verdict"]),
                reasoning=check["reasoning"],
                sources=[Source(**s) for s in sources_data],
            )
            write_check_note(db, vault, node, result)
        if checks:
            print(f"    migrated {len(checks)} check(s)")

    db.close()
    old_conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()
