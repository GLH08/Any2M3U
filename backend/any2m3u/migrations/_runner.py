from __future__ import annotations
import sqlite3
from pathlib import Path


def apply(data_dir: Path) -> None:
    """Apply any *.sql migration in this directory not yet recorded in schema_migrations."""
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "app.db"
    migrations_dir = Path(__file__).parent
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        # bootstrap the migrations table
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        conn.commit()
        applied = {
            row[0]
            for row in conn.execute("SELECT name FROM schema_migrations").fetchall()
        }
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            if sql_file.name in applied:
                continue
            sql = sql_file.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(name, applied_at) VALUES (?, datetime('now'))",
                (sql_file.name,),
            )
            conn.commit()
