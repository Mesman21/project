from fastapi.testclient import TestClient

from app.database import connect
from app.settings import Settings

PASSWORD = "classifier test phrase"
EXAMPLE = {
    "text": "Пропоную додати розклад практичних занять на головну.",
    "category_code": "suggestion",
    "dataset_split": "train",
}


def log_in(client: TestClient, role: str) -> None:
    response = client.post(
        "/api/auth/login", json={"username": role, "password": PASSWORD}
    )
    assert response.status_code == 200


def test_api_insert_is_visible_in_sqlite(
    client: TestClient, app_settings: Settings
) -> None:
    log_in(client, "maintainer")
    response = client.post("/api/examples", json=EXAMPLE)
    assert response.status_code == 201
    message_id = response.json()["message_id"]

    with connect(app_settings.database) as db:
        row = db.execute(
            "SELECT text, category_code, dataset_split "
            "FROM labeled_messages WHERE message_id = ?",
            (message_id,),
        ).fetchone()
    assert dict(row) == EXAMPLE


def test_sqlite_references_protect_evaluated_example(
    client: TestClient, app_settings: Settings
) -> None:
    log_in(client, "maintainer")
    before = next(row for row in client.get("/api/examples").json() if row["locked"])
    message_id = before["message_id"]
    url = f"/api/examples/{message_id}"

    assert client.put(url, json=EXAMPLE).status_code == 409
    assert client.delete(url).status_code == 409
    assert client.get(url).json() == before
    with connect(app_settings.database) as db:
        assert db.execute(
            "SELECT COUNT(*) FROM predictions WHERE message_id = ?", (message_id,)
        ).fetchone()[0] == 1


def test_api_statistics_agree_with_sqlite(
    client: TestClient, app_settings: Settings
) -> None:
    log_in(client, "coordinator")
    response = client.get("/api/statistics")
    assert response.status_code == 200

    with connect(app_settings.database) as db:
        predicted = db.execute(
            "SELECT category_code, category_name, count, share "
            "FROM evaluation_distribution WHERE evaluation_id = 1 "
            "ORDER BY category_code"
        ).fetchall()
        total = db.execute(
            "SELECT total FROM evaluation_totals WHERE evaluation_id = 1"
        ).fetchone()["total"]

    assert response.json() == {
        "total": total, "categories": [dict(row) for row in predicted]
    }
