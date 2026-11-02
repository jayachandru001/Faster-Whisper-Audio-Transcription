"""SQLite database operations."""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from config import DB_PATH, UPLOAD_DIR
import os
import tempfile


def get_db() -> sqlite3.Connection:
    """Return a thread-safe, optimized connection to SQLite with automatic /tmp fallback."""
    global DB_PATH
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    except Exception:
        # Fall back to temp dir if current directory is read-only (e.g. Vercel, AWS Lambda)
        fallback_dir = os.path.join(tempfile.gettempdir(), "storage")
        os.makedirs(fallback_dir, exist_ok=True)
        DB_PATH = os.path.join(fallback_dir, "whisper.db")
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def init_db() -> None:
    """Create upload directory and jobs table schema with WAL mode and indexes."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except OSError:
        pass

    conn = get_db()
    with conn:
        # High-concurrency WAL mode & fast synchronous writes (falls back to DELETE if WAL unsupported)
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        except Exception:
            conn.execute("PRAGMA journal_mode = DELETE;")
        conn.execute("PRAGMA busy_timeout = 5000;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                device TEXT DEFAULT 'cpu',
                language TEXT,
                duration REAL,
                text TEXT,
                segments_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        # Automatic migration for existing DB
        cols = [col[1] for col in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        if "progress" not in cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN progress INTEGER DEFAULT 0")
        if "device" not in cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN device TEXT DEFAULT 'cpu'")

        # Covering indexes for fast sorted querying
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
    conn.close()


def db_create_job(job_id: str, filename: str, file_path: str, device: str = "cpu") -> None:
    """Insert a new queued job."""
    created_at = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    with conn:
        conn.execute(
            "INSERT INTO jobs (id, filename, file_path, status, progress, device, created_at) VALUES (?, ?, ?, 'queued', 0, ?, ?)",
            (job_id, filename, file_path, device, created_at),
        )
    conn.close()


def db_get_job(job_id: str) -> Optional[sqlite3.Row]:
    """Retrieve job by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return row


def db_update_status(job_id: str, status_text: str, error: Optional[str] = None) -> None:
    """Update job status and optional error message."""
    conn = get_db()
    with conn:
        conn.execute(
            "UPDATE jobs SET status = ?, error = ? WHERE id = ?",
            (status_text, error, job_id),
        )
    conn.close()


def db_update_progress(job_id: str, progress: int) -> None:
    """Update job percentage progress (0-100)."""
    conn = get_db()
    with conn:
        conn.execute(
            "UPDATE jobs SET progress = ? WHERE id = ?",
            (progress, job_id),
        )
    conn.close()


def db_list_recent_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve list of recent transcription jobs."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, filename, status, progress, device, language, duration, created_at, completed_at, error
        FROM jobs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def db_complete_job(
    job_id: str, language: str, duration: float, text: str, segments: List[Dict[str, Any]]
) -> None:
    """Mark job as completed with transcript text and segment timestamps."""
    completed_at = datetime.now(timezone.utc).isoformat()
    segments_json = json.dumps(segments, ensure_ascii=False)
    conn = get_db()
    with conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'completed',
                progress = 100,
                language = ?,
                duration = ?,
                text = ?,
                segments_json = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (language, round(duration, 2), text, segments_json, completed_at, job_id),
        )
    conn.close()


def db_delete_job(job_id: str) -> Optional[str]:
    """Delete job record from SQLite and return file path for cleanup."""
    conn = get_db()
    row = conn.execute("SELECT file_path FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        conn.close()
        return None
    file_path = row["file_path"]
    with conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.close()
    return file_path
