"""Local persistent memory (SQLite): conversations, approved memories, tasks and action log.

Temporary context = the in-flight message list of a conversation (agent engine).
Persistent memory = rows in `memories`, created only with user approval.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from jarvis.security.redact import looks_sensitive, redact, redact_obj

CATEGORIES = ("preference", "project", "fact", "workflow", "task")

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT, role TEXT, content TEXT, created REAL);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, content TEXT, source TEXT, created REAL, updated REAL);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, category, content='memories', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, content, category) VALUES (new.id, new.content, new.category); END;
CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, content, category) VALUES ('delete', old.id, old.content, old.category); END;
CREATE TRIGGER IF NOT EXISTS mem_au AFTER UPDATE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, content, category) VALUES ('delete', old.id, old.content, old.category);
  INSERT INTO memories_fts(rowid, content, category) VALUES (new.id, new.content, new.category); END;
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, conversation_id TEXT, request TEXT, state TEXT, plan TEXT, result TEXT,
  error TEXT, created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, tool TEXT, args TEXT, risk TEXT, decision TEXT,
  status TEXT, output TEXT, verified INTEGER, created REAL, duration_ms INTEGER);
CREATE INDEX IF NOT EXISTS idx_act_task ON actions(task_id);
"""


class SensitiveContentError(ValueError):
    pass


class MemoryStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)

    def _x(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._db.execute(sql, params)
            self._db.commit()
            return cur

    def _q(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._db.execute(sql, params).fetchall()]

    # ---- conversations -------------------------------------------------
    def new_conversation(self, title: str = "") -> str:
        cid = uuid.uuid4().hex[:12]
        now = time.time()
        self._x("INSERT INTO conversations VALUES (?,?,?,?)", (cid, title[:80], now, now))
        return cid

    def ensure_conversation(self, cid: str | None, title: str = "") -> str:
        if cid and self._q("SELECT 1 FROM conversations WHERE id=?", (cid,)):
            return cid
        return self.new_conversation(title)

    def add_message(self, cid: str, role: str, content: str) -> None:
        now = time.time()
        self._x("INSERT INTO messages(conversation_id, role, content, created) VALUES (?,?,?,?)",
                (cid, role, redact(content), now))
        self._x("UPDATE conversations SET updated=? WHERE id=?", (now, cid))

    def messages(self, cid: str, limit: int = 200) -> list[dict]:
        return self._q("SELECT role, content, created FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                       (cid, limit))[::-1]

    def conversations(self, limit: int = 50) -> list[dict]:
        return self._q("SELECT * FROM conversations ORDER BY updated DESC LIMIT ?", (limit,))

    def delete_conversation(self, cid: str) -> None:
        self._x("DELETE FROM messages WHERE conversation_id=?", (cid,))
        self._x("DELETE FROM conversations WHERE id=?", (cid,))

    # ---- memories ---------------------------------------------------------
    def add_memory(self, category: str, content: str, source: str = "user") -> int:
        if category not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        content = content.strip()
        if not content:
            raise ValueError("empty memory")
        if looks_sensitive(content):
            raise SensitiveContentError("Refusing to store credentials or financial/identity data in memory.")
        now = time.time()
        return self._x("INSERT INTO memories(category, content, source, created, updated) VALUES (?,?,?,?,?)",
                       (category, content[:2000], source, now, now)).lastrowid

    def update_memory(self, mid: int, content: str, category: str | None = None) -> None:
        if looks_sensitive(content):
            raise SensitiveContentError("Refusing to store credentials or financial/identity data in memory.")
        row = self._q("SELECT category FROM memories WHERE id=?", (mid,))
        if not row:
            raise KeyError(mid)
        self._x("UPDATE memories SET content=?, category=?, updated=? WHERE id=?",
                (content.strip()[:2000], category or row[0]["category"], time.time(), mid))

    def delete_memory(self, mid: int) -> None:
        self._x("DELETE FROM memories WHERE id=?", (mid,))

    def list_memories(self, category: str | None = None) -> list[dict]:
        if category:
            return self._q("SELECT * FROM memories WHERE category=? ORDER BY updated DESC", (category,))
        return self._q("SELECT * FROM memories ORDER BY updated DESC")

    def search_memories(self, query: str, limit: int = 8) -> list[dict]:
        terms = [t for t in "".join(c if c.isalnum() else " " for c in query).split() if len(t) > 1]
        if not terms:
            return []
        fts = " OR ".join(f'"{t}"' for t in terms[:12])
        try:
            return self._q("SELECT m.* FROM memories_fts f JOIN memories m ON m.id=f.rowid "
                           "WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?", (fts, limit))
        except sqlite3.OperationalError:
            like = f"%{query}%"
            return self._q("SELECT * FROM memories WHERE content LIKE ? LIMIT ?", (like, limit))

    def clear_memories(self) -> None:
        self._x("DELETE FROM memories")

    # ---- tasks & actions -----------------------------------------------------
    def save_task(self, t: dict[str, Any]) -> None:
        now = time.time()
        self._x("""INSERT INTO tasks(id, conversation_id, request, state, plan, result, error, created, updated)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET state=excluded.state, plan=excluded.plan, result=excluded.result,
                   error=excluded.error, updated=excluded.updated""",
                (t["id"], t.get("conversation_id"), redact(t.get("request", "")), t["state"],
                 json.dumps(redact_obj(t.get("plan", [])), ensure_ascii=False), redact(t.get("result") or ""),
                 redact(t.get("error") or ""), t.get("created", now), now))

    def log_action(self, task_id: str, tool: str, args: dict, risk: str, decision: str, status: str,
                   output: str = "", verified: bool | None = None, duration_ms: int = 0) -> int:
        return self._x("""INSERT INTO actions(task_id, tool, args, risk, decision, status, output, verified, created, duration_ms)
                          VALUES (?,?,?,?,?,?,?,?,?,?)""",
                       (task_id, tool, json.dumps(redact_obj(args), ensure_ascii=False), risk, decision, status,
                        redact(output)[:4000], None if verified is None else int(verified), time.time(), duration_ms)).lastrowid

    def tasks(self, limit: int = 50) -> list[dict]:
        rows = self._q("SELECT * FROM tasks ORDER BY created DESC LIMIT ?", (limit,))
        for r in rows:
            r["plan"] = json.loads(r["plan"] or "[]")
            r["actions"] = self.actions(r["id"])
        return rows

    def actions(self, task_id: str) -> list[dict]:
        rows = self._q("SELECT * FROM actions WHERE task_id=? ORDER BY id", (task_id,))
        for r in rows:
            r["args"] = json.loads(r["args"] or "{}")
        return rows

    def recent_actions(self, limit: int = 100) -> list[dict]:
        rows = self._q("SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,))
        for r in rows:
            r["args"] = json.loads(r["args"] or "{}")
        return rows

    def close(self):
        with self._lock:
            self._db.close()
