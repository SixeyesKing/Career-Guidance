import json
import re
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from app.settings import DATABASE_PATH

_session_path = ContextVar("career_session_database", default=None)


@contextmanager
def session_database(session_id):
    """Select storage for one request, including its worker-thread service calls."""
    path = DATABASE_PATH.parent / "sessions" / (session_id + ".db")
    token = _session_path.set(path)
    try:
        yield
    finally:
        _session_path.reset(token)


def list_saved_visits(limit=50):
    """Summarize local visits with saved content without changing their databases."""
    directory = DATABASE_PATH.parent / "sessions"
    if not directory.exists():
        return []
    visits = []
    for path in directory.glob("*.db"):
        if not re.fullmatch(r"[0-9a-f]{32}", path.stem):
            continue
        try:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2) as connection:
                connection.row_factory = sqlite3.Row
                profile = connection.execute(
                    "SELECT grade, major, skills_json, experience_text, interest_json, target_city "
                    "FROM profiles WHERE id=1"
                ).fetchone()
                if profile is None:
                    continue
                counts = {
                    table: connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                    for table in ("analyses", "plans", "conversations", "experience_feedback")
                }
                has_profile = any(profile[field] for field in ("grade", "major", "experience_text", "target_city"))
                has_profile = has_profile or bool(json_load(profile["skills_json"], []) or json_load(profile["interest_json"], []))
                if not has_profile and not any(counts.values()):
                    continue
                latest = connection.execute(
                    "SELECT job_category FROM ("
                    "SELECT job_category, created_at FROM plans UNION ALL "
                    "SELECT job_category, created_at FROM analyses UNION ALL "
                    "SELECT job_category, created_at FROM conversations UNION ALL "
                    "SELECT job_category, created_at FROM experience_feedback"
                    ") ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
            visits.append({
                "visit_id": path.stem,
                "grade": profile["grade"],
                "major": profile["major"],
                "job_category": latest["job_category"] if latest else "",
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).astimezone().isoformat(timespec="seconds"),
                "analysis_count": counts["analyses"],
                "plan_count": counts["plans"],
                "conversation_count": counts["conversations"],
            })
        except (OSError, sqlite3.DatabaseError):
            continue
    visits.sort(key=lambda visit: visit["updated_at"], reverse=True)
    return visits[:limit]


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@contextmanager
def connect():
    path = _session_path.get() or DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db():
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                grade TEXT NOT NULL DEFAULT '',
                major TEXT NOT NULL DEFAULT '',
                skills_json TEXT NOT NULL DEFAULT '[]',
                experience_text TEXT NOT NULL DEFAULT '',
                interest_json TEXT NOT NULL DEFAULT '[]',
                target_city TEXT NOT NULL DEFAULT '',
                weekly_hours INTEGER NOT NULL DEFAULT 5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL DEFAULT 1,
                job_category TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '职业咨询',
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS experience_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL DEFAULT 1,
                job_category TEXT NOT NULL,
                choice TEXT NOT NULL CHECK(choice IN ('started', 'skipped')),
                interest INTEGER,
                difficulty INTEGER,
                continue_interest INTEGER,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL DEFAULT 1,
                job_category TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL DEFAULT 1,
                job_category TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
            """
        )
        feedback_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(experience_feedback)")
        }
        if "task_status" not in feedback_columns:
            db.execute(
                """ALTER TABLE experience_feedback ADD COLUMN task_status TEXT NOT NULL
                   DEFAULT 'started' CHECK(task_status IN ('started', 'completed', 'skipped'))"""
            )
        stamp = now_iso()
        db.execute(
            "INSERT OR IGNORE INTO profiles(id, created_at, updated_at) VALUES(1, ?, ?)",
            (stamp, stamp),
        )


def json_load(value, fallback):
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def get_profile():
    with connect() as db:
        row = db.execute("SELECT * FROM profiles WHERE id = 1").fetchone()
    result = dict(row)
    result["skills"] = json_load(result.pop("skills_json"), [])
    result["interests"] = json_load(result.pop("interest_json"), [])
    return result


def save_profile(data):
    stamp = now_iso()
    with connect() as db:
        db.execute(
            """UPDATE profiles SET grade=?, major=?, skills_json=?, experience_text=?,
               interest_json=?, target_city=?, weekly_hours=?, updated_at=? WHERE id=1""",
            (
                data.get("grade", ""), data.get("major", ""),
                json.dumps(data.get("skills", []), ensure_ascii=False),
                data.get("experience_text", ""),
                json.dumps(data.get("interests", []), ensure_ascii=False),
                data.get("target_city", ""), data.get("weekly_hours", 5), stamp,
            ),
        )
    return get_profile()


def create_conversation(job_category):
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO conversations(profile_id, job_category, created_at) VALUES(1, ?, ?)",
            (job_category, now_iso()),
        )
        return cursor.lastrowid


def add_message(conversation_id, role, content, sources=None):
    with connect() as db:
        cursor = db.execute(
            """INSERT INTO messages(conversation_id, role, content, sources_json, created_at)
               VALUES(?, ?, ?, ?, ?)""",
            (conversation_id, role, content, json.dumps(sources or [], ensure_ascii=False), now_iso()),
        )
        return cursor.lastrowid


def get_messages(conversation_id, limit=30):
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    messages = [dict(row) for row in reversed(rows)]
    for message in messages:
        message["sources"] = json_load(message.pop("sources_json"), [])
    return messages


def list_conversations():
    with connect() as db:
        rows = db.execute(
            """SELECT c.*, (SELECT content FROM messages m WHERE m.conversation_id=c.id
               ORDER BY m.id DESC LIMIT 1) AS last_message
               FROM conversations c ORDER BY c.id DESC LIMIT 20"""
        ).fetchall()
    return [dict(row) for row in rows]


def save_feedback(
    job_category,
    choice,
    interest=None,
    difficulty=None,
    continue_interest=None,
    note="",
    task_status=None,
):
    if task_status is None:
        task_status = "skipped" if choice == "skipped" else "started"
    with connect() as db:
        db.execute(
            """INSERT INTO experience_feedback(profile_id, job_category, choice, interest,
               difficulty, continue_interest, note, task_status, created_at)
               VALUES(1, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_category, choice, interest, difficulty, continue_interest, note, task_status, now_iso()),
        )


def list_feedback():
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM experience_feedback WHERE profile_id=1 ORDER BY id DESC"
        ).fetchall()
    feedback = [dict(row) for row in rows]
    for item in feedback:
        if item.get("choice") == "skipped":
            item["task_status"] = "skipped"
    return feedback


def save_analysis(job_category, result):
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO analyses(profile_id, job_category, result_json, created_at) VALUES(1, ?, ?, ?)",
            (job_category, json.dumps(result, ensure_ascii=False), now_iso()),
        )
        return cursor.lastrowid


def save_plan(job_category, plan):
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO plans(profile_id, job_category, plan_json, created_at) VALUES(1, ?, ?, ?)",
            (job_category, json.dumps(plan, ensure_ascii=False), now_iso()),
        )
        return cursor.lastrowid


def get_plan(plan_id):
    with connect() as db:
        row = db.execute("SELECT * FROM plans WHERE id=? AND profile_id=1", (plan_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["plan"] = json_load(result.pop("plan_json"), {})
    return result


def list_plans():
    with connect() as db:
        rows = db.execute("SELECT * FROM plans WHERE profile_id=1 ORDER BY id DESC LIMIT 20").fetchall()
    plans = [dict(row) for row in rows]
    for plan in plans:
        plan["plan"] = json_load(plan.pop("plan_json"), {})
    return plans


def list_analyses(limit=20):
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM analyses WHERE profile_id=1 ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    analyses = [dict(row) for row in rows]
    for analysis in analyses:
        analysis["result"] = json_load(analysis.pop("result_json"), {})
    return analyses


def latest_analysis(job_category):
    with connect() as db:
        row = db.execute(
            "SELECT result_json FROM analyses WHERE profile_id=1 AND job_category=? ORDER BY id DESC LIMIT 1",
            (job_category,),
        ).fetchone()
    return json_load(row["result_json"], {}) if row else None
