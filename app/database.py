import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from .schemas import CATEGORIES, ExampleInput, ExampleRecord
from .settings import DATABASE_FILES

EXAMPLE_SELECT = """
SELECT m.message_id, m.text, m.category_code, m.dataset_split,
       EXISTS (
           SELECT 1 FROM predictions AS p WHERE p.message_id = m.message_id
       ) AS locked
FROM labeled_messages AS m
"""


class DatasetConflict(ValueError):
    pass


@contextmanager
def connect(
    path: Path, *, immediate: bool = False
) -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(path, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        if immediate:
            db.execute("BEGIN IMMEDIATE")
        with db:
            yield db


def initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        if db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'categories'"
        ).fetchone() is None:
            db.executescript(
                (DATABASE_FILES / "schema.sql").read_text(encoding="utf-8")
            )
        db.executescript(
            (DATABASE_FILES / "auth_schema.sql").read_text(encoding="utf-8")
        )
        db.executemany(
            "INSERT INTO categories (category_code, category_name) "
            "VALUES (?, ?) ON CONFLICT (category_code) DO NOTHING",
            CATEGORIES.items(),
        )


def list_examples(path: Path) -> list[ExampleRecord]:
    with connect(path) as db:
        rows = db.execute(EXAMPLE_SELECT + " ORDER BY m.message_id DESC")
        return [ExampleRecord.model_validate(dict(row)) for row in rows]


def _find_example(
    db: sqlite3.Connection, message_id: int
) -> ExampleRecord | None:
    row = db.execute(
        EXAMPLE_SELECT + " WHERE m.message_id = ?", (message_id,)
    ).fetchone()
    return ExampleRecord.model_validate(dict(row)) if row else None


def get_example(path: Path, message_id: int) -> ExampleRecord | None:
    with connect(path) as db:
        return _find_example(db, message_id)


def add_example(path: Path, example: ExampleInput) -> ExampleRecord:
    with connect(path) as db:
        cursor = db.execute(
            "INSERT INTO labeled_messages (text, category_code, dataset_split) "
            "VALUES (?, ?, ?)",
            (example.text, example.category_code, example.dataset_split),
        )
        return ExampleRecord(
            **example.model_dump(), message_id=cursor.lastrowid, locked=False
        )


def _editable_example(
    db: sqlite3.Connection, message_id: int
) -> ExampleRecord | None:
    record = _find_example(db, message_id)
    if record and record.locked:
        raise DatasetConflict("Приклад уже використано для оцінювання.")
    return record


def update_example(
    path: Path, message_id: int, example: ExampleInput
) -> ExampleRecord | None:
    with connect(path, immediate=True) as db:
        if _editable_example(db, message_id) is None:
            return None
        db.execute(
            "UPDATE labeled_messages "
            "SET text = ?, category_code = ?, dataset_split = ? "
            "WHERE message_id = ?",
            (example.text, example.category_code, example.dataset_split, message_id),
        )
        return ExampleRecord(
            **example.model_dump(), message_id=message_id, locked=False
        )


def delete_example(path: Path, message_id: int) -> bool:
    with connect(path, immediate=True) as db:
        if _editable_example(db, message_id) is None:
            return False
        db.execute(
            "DELETE FROM labeled_messages WHERE message_id = ?", (message_id,)
        )
        return True
