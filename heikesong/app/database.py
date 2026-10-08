"""SQLite 连接、建表与题库种子导入（使用标准库 sqlite3，无 ORM）。"""
import json
import sqlite3
from pathlib import Path

from .config import settings

DB_PATH = Path(settings.database_path)


def get_conn() -> sqlite3.Connection:
    """获取一个 SQLite 连接（自动创建数据目录，返回 Row 式结果）。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position TEXT NOT NULL,
    years_range TEXT NOT NULL DEFAULT 'all',
    salary_tier TEXT NOT NULL DEFAULT 'all',
    difficulty INTEGER NOT NULL DEFAULT 2,
    question TEXT NOT NULL,
    analysis TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS practice_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    position TEXT NOT NULL,
    years_range TEXT NOT NULL,
    salary_tier TEXT NOT NULL,
    source TEXT NOT NULL,
    qa_json TEXT NOT NULL,
    score_json TEXT NOT NULL,
    total_score INTEGER,
    hire_probability INTEGER,
    weak_dimension TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'free',
    plan TEXT NOT NULL DEFAULT 'free',
    started_at TEXT,
    expires_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS daily_usage (
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_bank_position ON question_bank(position);
CREATE INDEX IF NOT EXISTS idx_records_user ON practice_records(user_id, created_at);
"""


def init_db() -> None:
    """建表（幂等）。"""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_question_bank(seed_path: Path) -> int:
    """导入预设题库种子（幂等：同岗位 + 同题目则跳过）。返回新增条数。"""
    if not seed_path.exists():
        return 0
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    questions = data.get("questions", [])
    conn = get_conn()
    inserted = 0
    try:
        for q in questions:
            exists = conn.execute(
                "SELECT 1 FROM question_bank WHERE position=? AND question=?",
                (q["position"], q["question"]),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO question_bank "
                "(position, years_range, salary_tier, difficulty, question, analysis) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    q["position"],
                    q.get("years_range", "all"),
                    q.get("salary_tier", "all"),
                    q.get("difficulty", 2),
                    q["question"],
                    q["analysis"],
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted
