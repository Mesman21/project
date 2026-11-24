import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

DATABASE_DIR = Path(__file__).resolve().parents[1] / "database"
TOTALS_QUERY = (
    "SELECT total, correct, accuracy FROM evaluation_totals "
    "WHERE evaluation_id = 1"
)


@pytest.fixture
def db() -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(":memory:")) as connection:
        for name in ("schema.sql", "demo_data.sql"):
            sql = (DATABASE_DIR / name).read_text(encoding="utf-8")
            connection.executescript(sql)
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
        yield connection


def test_sample_partitions(db: sqlite3.Connection) -> None:
    rows = db.execute(
        "SELECT dataset_split, COUNT(*) FROM labeled_messages "
        "GROUP BY dataset_split ORDER BY dataset_split"
    ).fetchall()

    assert rows == [("test", 4), ("train", 6)]


def test_distribution_includes_zero_counts(db: sqlite3.Connection) -> None:
    rows = db.execute(
        "SELECT category_code, count, share FROM evaluation_distribution "
        "WHERE evaluation_id = 1 ORDER BY category_code"
    ).fetchall()

    assert rows == [
        ("incident_report", 2, 0.5),
        ("information_request", 2, 0.5),
        ("suggestion", 0, 0.0),
    ]


def test_accuracy_uses_reference_labels(db: sqlite3.Connection) -> None:
    assert db.execute(TOTALS_QUERY).fetchone() == (4, 3, 0.75)


@pytest.mark.parametrize(
    "text",
    ["", "\t\u2003\u00a0", "з" * 2001, "текст\x00", " текст"],
    ids=["empty", "whitespace", "too-long", "null-character", "untrimmed"],
)
def test_rejects_invalid_text(db: sqlite3.Connection, text: str) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint"):
        db.execute(
            "INSERT INTO labeled_messages "
            "(text, category_code, dataset_split) "
            "VALUES (?, 'suggestion', 'train')",
            (text,),
        )


def test_rejects_duplicate_text_across_splits(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint"):
        db.execute(
            "INSERT INTO labeled_messages "
            "(text, category_code, dataset_split) "
            "SELECT text, category_code, 'test' FROM labeled_messages "
            "WHERE message_id = 1"
        )


def test_rejects_unknown_split(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint"):
        db.execute(
            "INSERT INTO labeled_messages "
            "(text, category_code, dataset_split) "
            "VALUES ('Зразок нового тексту', 'suggestion', 'unknown')"
        )


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO labeled_messages (text, category_code, dataset_split) "
        "VALUES ('Зразок нового тексту', 'unknown', 'test')",
        "UPDATE predictions SET predicted_category_code = 'unknown' "
        "WHERE evaluation_id = 1 AND message_id = 7",
    ],
    ids=["reference-label", "predicted-label"],
)
def test_rejects_unknown_label(db: sqlite3.Connection, statement: str) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint"):
        db.execute(statement)


def test_rejects_duplicate_prediction(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint"):
        db.execute(
            "INSERT INTO predictions VALUES (1, 7, 'information_request')"
        )


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO predictions VALUES (1, 1, 'information_request')",
        "UPDATE predictions SET message_id = 1 "
        "WHERE evaluation_id = 1 AND message_id = 7",
    ],
    ids=["insert", "update"],
)
def test_rejects_prediction_for_training_message(
    db: sqlite3.Connection, statement: str
) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="Прогноз має посилатися"):
        db.execute(statement)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE labeled_messages SET category_code = 'suggestion' "
        "WHERE message_id = 7",
        "UPDATE labeled_messages SET dataset_split = 'train' "
        "WHERE message_id = 7",
        "UPDATE labeled_messages SET text = 'Де отримати довідку?' "
        "WHERE message_id = 7",
    ],
    ids=["label", "split", "text"],
)
def test_protects_evaluated_message(
    db: sqlite3.Connection, statement: str
) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="уже використано"):
        db.execute(statement)


def test_evaluation_runs_are_independent(db: sqlite3.Connection) -> None:
    db.execute(
        "INSERT INTO evaluation_runs (evaluation_id, model_version) "
        "VALUES (2, 'demo-v2')"
    )
    db.execute("INSERT INTO predictions VALUES (2, 7, 'incident_report')")

    rows = db.execute(
        "SELECT evaluation_id, total, correct FROM evaluation_totals "
        "ORDER BY evaluation_id"
    ).fetchall()

    assert rows == [(1, 4, 3), (2, 1, 0)]


def test_empty_run_has_no_summary(db: sqlite3.Connection) -> None:
    db.execute(
        "INSERT INTO evaluation_runs (evaluation_id, model_version) "
        "VALUES (2, 'empty')"
    )
    row = db.execute(
        "SELECT total FROM evaluation_totals WHERE evaluation_id = 2"
    ).fetchone()

    assert row is None


def test_evaluation_deletion_keeps_examples(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM evaluation_runs WHERE evaluation_id = 1")
    predictions = db.execute("SELECT COUNT(*) FROM predictions").fetchone()
    examples = db.execute("SELECT COUNT(*) FROM labeled_messages").fetchone()

    assert predictions == (0,)
    assert examples == (10,)


def test_delivered_demo_database_is_consistent() -> None:
    path = DATABASE_DIR / "classification_demo.sqlite3"
    uri = f"{path.as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        assert integrity == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(TOTALS_QUERY).fetchone() == (4, 3, 0.75)

