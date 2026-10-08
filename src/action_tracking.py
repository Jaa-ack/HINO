"""Local pilot actions, separated by demonstration scope and stable problem identity."""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from src.utils import ROOT, json_safe

ACTION_STATUSES = ("待核對", "已採納", "執行中", "待驗證")
VERIFICATION_PENDING = "待後續可比較行程驗證"


def action_key(action):
    """An owner or evidence update must not create a new trip problem."""
    identity = [str(action["trip_id"]), str(action["problem"])]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()


class ActionStore:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("ECOPILOT_ACTION_DB") or ROOT / "data/pilot/action_tracking.sqlite3")

    def load(self, action, *, demonstration):
        if not self.path.exists():
            return None
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT payload FROM actions WHERE scope = ? AND action_key = ?",
                               (self._scope(demonstration), action_key(action))).fetchone()
        return json.loads(row[0]) if row else None

    def records(self, *, demonstration):
        if not self.path.exists():
            return []
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT payload FROM actions WHERE scope = ? ORDER BY updated_at DESC, action_key",
                                (self._scope(demonstration),)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save(self, action, *, measures, status, follow_up_date, demonstration):
        measures = measures.strip()
        if not measures:
            raise ValueError("請填寫執行措施，再保存追蹤紀錄。")
        if status not in ACTION_STATUSES:
            raise ValueError("請選擇有效的追蹤狀態。")
        follow_up = date.fromisoformat(str(follow_up_date)).isoformat()
        record = {
            "action_key": action_key(action), "trip_id": str(action["trip_id"]),
            "problem": str(action["problem"]), "primary_owner": str(action["primary_owner"]),
            "supporting_roles": json_safe(action.get("supporting_roles", [])),
            "evidence": str(action["evidence"]), "measures": measures,
            "status": status, "follow_up_date": follow_up, "scope": self._scope(demonstration),
            "verification": VERIFICATION_PENDING,
            "updated_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS actions (
                scope TEXT NOT NULL, action_key TEXT NOT NULL, payload TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY (scope, action_key))""")
            conn.execute("""INSERT INTO actions (scope, action_key, payload, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(scope, action_key) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at""",
                (record["scope"], record["action_key"], json.dumps(record, ensure_ascii=False), record["updated_at"]))
        return record

    @staticmethod
    def _scope(demonstration):
        return "demonstration" if demonstration else "pilot"
