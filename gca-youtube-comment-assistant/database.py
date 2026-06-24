import sqlite3
from pathlib import Path

DB_PATH = Path("comments.db")


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            thread_id TEXT,
            video_id TEXT,
            video_title TEXT,
            author TEXT,
            text TEXT,
            published_at TEXT,
            status TEXT DEFAULT 'new'
        )
    """)
    conn.commit()
    conn.close()


def save_comment(comment):
    """
    Save a new comment only once.

    Existing comments keep their current status, so comments marked posted,
    skipped, or important will not be reset back to new.
    """
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO comments (
            comment_id, thread_id, video_id, video_title, author, text, published_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
    """, (
        comment["comment_id"],
        comment["thread_id"],
        comment["video_id"],
        comment.get("video_title", ""),
        comment.get("author", ""),
        comment.get("text", ""),
        comment.get("published_at", "")
    ))
    conn.commit()
    conn.close()


def get_unhandled_comments():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM comments
        WHERE status IN ('new', 'important')
        ORDER BY published_at DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_comment_status(comment_id, status):
    conn = get_conn()
    conn.execute(
        "UPDATE comments SET status = ? WHERE comment_id = ?",
        (status, comment_id)
    )
    conn.commit()
    conn.close()


def clear_new_comments():
    """
    Optional cleanup helper.
    Removes only unhandled comments so you can refresh the inbox after filters change.
    It does not remove posted, skipped, or important history.
    """
    conn = get_conn()
    conn.execute("DELETE FROM comments WHERE status = 'new'")
    conn.commit()
    conn.close()
