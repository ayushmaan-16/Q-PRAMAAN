"""SQLite receipts and atomic exactly-once simulated execution."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, report TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS executions(session TEXT PRIMARY KEY, context TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def save(self, report):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO reports VALUES (?, ?)", (report["id"], json.dumps(report)))

    def get(self, report_id):
        with self.connect() as db:
            row = db.execute("SELECT report FROM reports WHERE id=?", (report_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def execute_once(self, session, context):
        with self.connect() as db:
            try:
                db.execute("INSERT INTO executions VALUES (?, ?)", (session, context))
                return True
            except sqlite3.IntegrityError:
                return False
