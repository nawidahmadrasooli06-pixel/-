import sqlite3
import threading
from datetime import datetime, timezone

import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS names(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS winners(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    won_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings(
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            self.conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('auto_remove', '0')")
            self.conn.commit()

    # ---- names ----
    def list_names(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT id, name FROM names ORDER BY id").fetchall()
        return [{"id": r["id"], "name": r["name"]} for r in rows]

    def count_names(self) -> int:
        with self.lock:
            return self.conn.execute("SELECT COUNT(*) FROM names").fetchone()[0]

    def add_names(self, names: list[str]) -> tuple[int, int]:
        """Returns (added, skipped_because_full)."""
        with self.lock, self.conn:
            count = self.conn.execute("SELECT COUNT(*) FROM names").fetchone()[0]
            room = max(0, config.MAX_NAMES - count)
            accepted = names[:room]
            now = _now()
            self.conn.executemany(
                "INSERT INTO names(name, created_at) VALUES(?, ?)", [(n, now) for n in accepted]
            )
        return len(accepted), len(names) - len(accepted)

    def get_name(self, name_id: int):
        with self.lock:
            row = self.conn.execute("SELECT id, name FROM names WHERE id=?", (name_id,)).fetchone()
        return {"id": row["id"], "name": row["name"]} if row else None

    def remove_name(self, name_id: int) -> bool:
        with self.lock, self.conn:
            cur = self.conn.execute("DELETE FROM names WHERE id=?", (name_id,))
            return cur.rowcount > 0

    def rename(self, name_id: int, new_name: str) -> bool:
        with self.lock, self.conn:
            cur = self.conn.execute("UPDATE names SET name=? WHERE id=?", (new_name, name_id))
            return cur.rowcount > 0

    def clear_names(self) -> None:
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM names")

    # ---- winners ----
    def add_winner(self, name: str) -> None:
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO winners(name, won_at) VALUES(?, ?)", (name, _now()))

    def list_winners(self, limit: int = 100) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT id, name, won_at FROM winners ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"id": r["id"], "name": r["name"], "won_at": r["won_at"]} for r in rows]

    def clear_winners(self) -> None:
        with self.lock, self.conn:
            self.conn.execute("DELETE FROM winners")

    # ---- settings ----
    def auto_remove(self) -> bool:
        with self.lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key='auto_remove'").fetchone()
        return bool(row and row["value"] == "1")

    def set_auto_remove(self, value: bool) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO settings(key, value) VALUES('auto_remove', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("1" if value else "0",),
            )

    def get_setting(self, key: str, default=None):
        with self.lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    # ---- backup ----
    def snapshot_to(self, dest_path: str) -> None:
        dest = sqlite3.connect(dest_path)
        try:
            with self.lock:
                self.conn.backup(dest)
        finally:
            dest.close()
