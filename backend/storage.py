"""Small SQLite store for analysis summaries and query experiments."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DATABASE_PATH = Path(__file__).parent / "data" / "repolens.db"


def connection():
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    database = sqlite3.connect(DATABASE_PATH)
    database.row_factory = sqlite3.Row
    return database


def setup_database():
    with connection() as database:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                repo TEXT PRIMARY KEY,
                stats TEXT NOT NULL,
                analyzed_at TEXT NOT NULL
            )
            """
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS query_runs (
                id TEXT PRIMARY KEY,
                repo TEXT NOT NULL,
                query TEXT NOT NULL,
                intent TEXT NOT NULL,
                answer TEXT NOT NULL,
                trace TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_analysis(repo, stats):
    timestamp = datetime.now(timezone.utc).isoformat()
    with connection() as database:
        database.execute(
            """
            INSERT INTO analyses (repo, stats, analyzed_at) VALUES (?, ?, ?)
            ON CONFLICT(repo) DO UPDATE SET stats = excluded.stats, analyzed_at = excluded.analyzed_at
            """,
            (repo, json.dumps(stats), timestamp),
        )


def save_query_run(repo, query, answer, trace, latency_ms):
    run_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    with connection() as database:
        database.execute(
            """
            INSERT INTO query_runs (id, repo, query, intent, answer, trace, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                repo,
                query,
                trace.get("intent", "semantic"),
                answer,
                json.dumps(trace),
                latency_ms,
                timestamp,
            ),
        )
    return run_id


def recent_runs(repo=None, limit=20):
    query = "SELECT * FROM query_runs"
    values = []
    if repo:
        query += " WHERE repo = ?"
        values.append(repo)
    query += " ORDER BY created_at DESC LIMIT ?"
    values.append(limit)

    with connection() as database:
        rows = database.execute(query, values).fetchall()

    return [
        {
            "id": row["id"],
            "repo": row["repo"],
            "query": row["query"],
            "intent": row["intent"],
            "answer": row["answer"],
            "trace": json.loads(row["trace"]),
            "latency_ms": row["latency_ms"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def recent_analyses(limit=8):
    with connection() as database:
        rows = database.execute(
            "SELECT * FROM analyses ORDER BY analyzed_at DESC LIMIT ?", (limit,)
        ).fetchall()

    return [
        {
            "repo": row["repo"],
            "stats": json.loads(row["stats"]),
            "analyzed_at": row["analyzed_at"],
        }
        for row in rows
    ]
