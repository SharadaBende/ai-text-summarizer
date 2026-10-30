"""Tiny SQLite store for summary history."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager

from .config import DB_PATH


@contextmanager
def _conn():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL NOT NULL, title TEXT, method TEXT,
                text TEXT NOT NULL, summary TEXT NOT NULL, metrics TEXT)"""
        )


def add(title: str, method: str, text: str, summary: str, metrics: dict) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO history (created, title, method, text, summary, metrics) VALUES (?,?,?,?,?,?)",
            (time.time(), title or "Untitled", method, text, summary, json.dumps(metrics)),
        )
        return int(cur.lastrowid)


def list_items(limit: int = 100) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, created, title, method, summary, metrics FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{**dict(r), "metrics": json.loads(r["metrics"] or "{}")} for r in rows]


def get(item_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM history WHERE id = ?", (item_id,)).fetchone()
    return {**dict(r), "metrics": json.loads(r["metrics"] or "{}")} if r else None


def delete(item_id: int) -> bool:
    with _conn() as c:
        return c.execute("DELETE FROM history WHERE id = ?", (item_id,)).rowcount > 0


def clear() -> None:
    with _conn() as c:
        c.execute("DELETE FROM history")
