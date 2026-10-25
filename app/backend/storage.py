"""Local storage: SQLite for the history list, plain files for audio and reports.
Everything for one analysis lives under data/ and is removed by delete(), including its transcript cache."""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

ID_RE = re.compile(r"^[a-f0-9]{12}$")
FIELDS = ("id", "filename", "created", "language", "status", "step", "error", "level", "auth_label",
          "est_rupees", "consent_at", "audio_ext", "audio_seconds")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir)
        self.uploads, self.reports, self.cache = (self.root / n for n in ("uploads", "reports", "cache"))
        for d in (self.uploads, self.reports, self.cache):
            d.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "call-shield.db"
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY, filename TEXT, created TEXT, language TEXT, status TEXT, step TEXT, error TEXT,
                level TEXT, auth_label TEXT, est_rupees REAL, consent_at TEXT, audio_ext TEXT, audio_seconds REAL)""")

    def _conn(self):
        c = sqlite3.connect(self.db, timeout=10, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def recover_interrupted(self) -> None:
        """A server restart kills background jobs; mark them so the UI does not wait forever."""
        with self._lock, self._conn() as c:
            c.execute("UPDATE analyses SET status='error', step=NULL, error='Interrupted by a server restart. Upload again.' "
                      "WHERE status IN ('queued','running')")

    # ---- records ---------------------------------------------------------------------------
    def create(self, id: str, filename: str, language: str, audio_ext: str) -> None:
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO analyses (id, filename, created, language, status, consent_at, audio_ext) "
                      "VALUES (?,?,?,?,?,?,?)", (id, filename, now(), language, "queued", now(), audio_ext))

    def update(self, id: str, **fields) -> None:
        assert set(fields) <= set(FIELDS), fields
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields)
        with self._lock, self._conn() as c:
            c.execute(f"UPDATE analyses SET {sets} WHERE id=?", (*fields.values(), id))

    def get(self, id: str) -> dict | None:
        if not ID_RE.match(id):
            return None
        with self._lock, self._conn() as c:
            row = c.execute("SELECT * FROM analyses WHERE id=?", (id,)).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict]:
        with self._lock, self._conn() as c:
            rows = c.execute("SELECT id, filename, created, language, status, step, error, level, auth_label, est_rupees "
                             "FROM analyses ORDER BY created DESC, rowid DESC").fetchall()
        return [dict(r) for r in rows]

    def ids(self) -> list[str]:
        return [r["id"] for r in self.list()]

    # ---- files -------------------------------------------------------------------------------
    def audio_path(self, id: str, ext: str) -> Path:
        return self.uploads / f"{id}{ext}"

    def cache_dir(self, id: str) -> Path:
        return self.cache / id

    def save_report(self, id: str, report: dict, html: str) -> None:
        (self.reports / f"{id}.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        (self.reports / f"{id}.html").write_text(html, encoding="utf-8")

    def load_report(self, id: str) -> dict | None:
        f = self.reports / f"{id}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def report_html(self, id: str) -> str | None:
        f = self.reports / f"{id}.html"
        return f.read_text(encoding="utf-8") if f.exists() else None

    # ---- the timestamped call record and the AI-written summaries (both removed by delete()) ----------
    def save_session(self, id: str, record: dict) -> None:
        (self.reports / f"{id}.session.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    def load_session(self, id: str) -> dict | None:
        f = self.reports / f"{id}.session.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def load_ai(self, id: str) -> dict:
        f = self.reports / f"{id}.ai.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    def save_ai(self, id: str, lang: str, result: dict) -> None:
        data = self.load_ai(id)
        data[lang] = result
        (self.reports / f"{id}.ai.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def delete(self, id: str) -> bool:
        rec = self.get(id)
        if not rec:
            return False
        for f in list(self.uploads.glob(f"{id}.*")) + list(self.reports.glob(f"{id}.*")):
            f.unlink(missing_ok=True)
        shutil.rmtree(self.cache_dir(id), ignore_errors=True)
        with self._lock, self._conn() as c:
            c.execute("DELETE FROM analyses WHERE id=?", (id,))
        return True
