"""Kalıcı session memory; LangGraph checkpoint'inden bağımsız uzun dönem kayıt."""

from __future__ import annotations

import sqlite3
from pathlib import Path


MEMORY_DB = Path(__file__).resolve().parent / "conversation_memory.db"


class ConversationMemory:
    def __init__(self, path: str | Path = MEMORY_DB):
        self.path = Path(path)
        with sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS conversations (session_id TEXT, role TEXT, content TEXT, project TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id, created_at)")

    def append(self, session_id: str, role: str, content: str, project: str | None = None) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO conversations(session_id,role,content,project) VALUES (?,?,?,?)", (session_id, role, content, project))

    def recent(self, session_id: str, limit: int = 12) -> list[dict]:
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT role,content,project,created_at FROM conversations WHERE session_id=? ORDER BY created_at DESC LIMIT ?", (session_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def last_project(self, session_id: str) -> str | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT project FROM conversations WHERE session_id=? AND project IS NOT NULL ORDER BY created_at DESC LIMIT 1", (session_id,)).fetchone()
        return row[0] if row else None
