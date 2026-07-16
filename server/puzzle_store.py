"""Persistent puzzle storage for fast game startup."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "puzzles.db"
TARGET_PUZZLE_COUNT = 150


class PuzzleStoreError(RuntimeError):
    """Raised when the puzzle database is missing or unusable."""


@dataclass(frozen=True)
class StoredPuzzle:
    start_title: str
    target_title: str
    path: list[str]
    shortest_steps: int


def initialize(db_path: Path = DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS puzzles (
                    id INTEGER PRIMARY KEY,
                    start_title TEXT NOT NULL,
                    target_title TEXT NOT NULL,
                    path_json TEXT NOT NULL,
                    shortest_steps INTEGER NOT NULL CHECK (shortest_steps > 0),
                    source TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    play_count INTEGER NOT NULL DEFAULT 0,
                    last_played_at TEXT,
                    UNIQUE (start_title, target_title)
                );

                CREATE INDEX IF NOT EXISTS puzzles_depth_usage
                    ON puzzles (shortest_steps, play_count);
                """
            )


def add_puzzle(
    path: list[str],
    *,
    source: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    if len(path) < 2 or len(set(path)) != len(path):
        raise ValueError("A puzzle path must contain at least two unique articles")

    initialize(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO puzzles (
                    start_title,
                    target_title,
                    path_json,
                    shortest_steps,
                    source,
                    verified_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    path[0],
                    path[-1],
                    json.dumps(path, ensure_ascii=False),
                    len(path) - 1,
                    source,
                    datetime.now(UTC).isoformat(),
                ),
            )
            return cursor.rowcount == 1


def count_puzzles(
    *,
    shortest_steps: int | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    if not db_path.exists():
        return 0

    with closing(sqlite3.connect(db_path)) as connection:
        if shortest_steps is None:
            row = connection.execute("SELECT COUNT(*) FROM puzzles").fetchone()
        else:
            row = connection.execute(
                "SELECT COUNT(*) FROM puzzles WHERE shortest_steps = ?",
                (shortest_steps,),
            ).fetchone()
    return int(row[0]) if row else 0


def get_random_puzzle(
    *,
    shortest_steps: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> StoredPuzzle:
    """Return a random least-played puzzle and record its use.

    Selecting from the lowest play count keeps all 150 puzzles in rotation
    while preserving randomness within each rotation.
    """
    if not db_path.exists():
        raise PuzzleStoreError(f"Puzzle database does not exist: {db_path}")

    with closing(sqlite3.connect(db_path, timeout=5)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT id, start_title, target_title, path_json, shortest_steps
                FROM puzzles
                WHERE shortest_steps = ?
                  AND play_count = (
                      SELECT MIN(play_count)
                      FROM puzzles
                      WHERE shortest_steps = ?
                  )
                ORDER BY RANDOM()
                LIMIT 1
                """,
                (shortest_steps, shortest_steps),
            ).fetchone()

            if row is None:
                raise PuzzleStoreError(
                    f"No puzzle with a shortest path of {shortest_steps} steps"
                )

            connection.execute(
                """
                UPDATE puzzles
                SET play_count = play_count + 1,
                    last_played_at = ?
                WHERE id = ?
                """,
                (datetime.now(UTC).isoformat(), row[0]),
            )

    try:
        path = json.loads(row[3])
    except (json.JSONDecodeError, TypeError) as exc:
        raise PuzzleStoreError(f"Puzzle {row[0]} has an invalid path") from exc

    if not isinstance(path, list) or not all(isinstance(item, str) for item in path):
        raise PuzzleStoreError(f"Puzzle {row[0]} has an invalid path")

    return StoredPuzzle(
        start_title=row[1],
        target_title=row[2],
        path=path,
        shortest_steps=row[4],
    )
