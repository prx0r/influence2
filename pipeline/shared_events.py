"""Shared events — monotonic log human + agent actions can both read.

Port of agent-theater studio.ts record/eventsSince/waitForEvents.
One SQLite table, integer seq, human|agent attribution. Every MCP reply
carries human-events-since-last-call (no polling, no drift).

Usage:
  seq = record(conn, kind, summary, by="agent", detail={...})
  news = events_since(conn, last_seen_seq)  # what happened since?
"""
from __future__ import annotations

import json
import sqlite3
import time


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS shared_events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        at REAL NOT NULL,
        kind TEXT NOT NULL,
        summary TEXT NOT NULL,
        by TEXT NOT NULL DEFAULT 'human',
        detail TEXT DEFAULT '{}')""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_events_seq "
                 "ON shared_events(seq)")
    conn.commit()


def record(conn: sqlite3.Connection, kind: str, summary: str,
           by: str = "human", detail: dict | None = None) -> int:
    """Append event, return seq. by: human|agent."""
    ensure_table(conn)
    cur = conn.execute(
        "INSERT INTO shared_events (at, kind, summary, by, detail)"
        " VALUES (?,?,?,?,?)",
        (time.time(), kind, summary[:500], by,
         json.dumps(detail or {})[:2000]))
    conn.commit()
    return cur.lastrowid


def events_since(conn: sqlite3.Connection, seq: int,
                 limit: int = 50) -> list[dict]:
    """All events after seq (for MCP 'meanwhile human did X' lines)."""
    ensure_table(conn)
    prev_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT seq, at, kind, summary, by, detail FROM shared_events"
            " WHERE seq > ? ORDER BY seq ASC LIMIT ?",
            (seq, limit)).fetchall()
    finally:
        conn.row_factory = prev_factory
    out = []
    for r in rows:
        try:
            detail = json.loads(r["detail"] or "{}")
        except (json.JSONDecodeError, TypeError):
            detail = {}
        out.append({"seq": r["seq"], "at": r["at"], "kind": r["kind"],
                    "summary": r["summary"], "by": r["by"],
                    "detail": detail})
    return out


def latest_seq(conn: sqlite3.Connection) -> int:
    ensure_table(conn)
    r = conn.execute("SELECT MAX(seq) FROM shared_events").fetchone()
    return r[0] or 0 if r else 0


def human_news_line(conn: sqlite3.Connection, since_seq: int) -> str:
    """One-line summary for MCP replies: what did the human do since?"""
    evs = [e for e in events_since(conn, since_seq) if e["by"] == "human"]
    if not evs:
        return ""
    bits = [f"{e['kind']}: {e['summary']}" for e in evs[-3:]]
    return "Meanwhile, the human was working: " + "; ".join(bits)
