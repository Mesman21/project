from fastapi.testclient import TestClient

from app.auth import SESSION_COOKIE

PASSWORD = "classifier test phrase"
EXAMPLE = {
    "text": "Підкажіть точний час захисту практики.",
    "category_code": "information_request",
    "dataset_split": "train",
}


def sign_in(client: TestClient, role: str) -> None:
    response = client.post(
        "/api/auth/login", json={"username": role, "password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["role"] == role


def test_sign_in_sets_protected_cookie(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401
    response = client.post(
        "/api/auth/login", json={"username": "operator", "password": PASSWORD}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/api/auth/me").json()["role"] == "operator"


def test_wrong_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"username": "operator", "password": "wrong"}
    )
    assert response.status_code == 401
    assert SESSION_COOKIE not in client.cookies


def test_sign_out_revokes_session(client: TestClient) -> None:
    sign_in(client, "maintainer")
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_role_restricts_example_changes(client: TestClient) -> None:
    sign_in(client, "operator")
    assert client.post("/api/examples", json=EXAMPLE).status_code == 403
    assert client.get("/api/statistics").status_code == 403


def test_coordinator_receives_real_evaluation(client: TestClient) -> None:
    sign_in(client, "coordinator")
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 18
    assert sum(row["count"] for row in data["categories"]) == 18
    assert len(data["categories"]) == 3
    assert client.post("/api/classify", json={"text": "Яка дата?"}).status_code == 403


def test_classify_uses_trained_pipeline(client: TestClient) -> None:
    sign_in(client, "operator")
    response = client.post(
        "/api/classify", json={"text": "  Де можна переглянути розклад занять?  "}
    )
    assert response.status_code == 200
    assert response.json() == {
        "category_code": "information_request",
        "category_name": "Інформаційний запит",
    }


def test_invalid_text_returns_localized_error(client: TestClient) -> None:
    sign_in(client, "operator")
    result = client.post("/api/classify", json={"text": " \t "})
    assert result.status_code == 422
    assert result.json() == {"detail": "Введіть текст повідомлення."}


def test_example_crud(client: TestClient) -> None:
    sign_in(client, "maintainer")
    created = client.post("/api/examples", json=EXAMPLE)
    assert created.status_code == 201
    url = "/api/examples/" + str(created.json()["message_id"])
    assert client.get(url).json()["text"] == EXAMPLE["text"]
    updated = client.put(url, json=dict(EXAMPLE, text="Яка дата захисту?"))
    assert updated.status_code == 200
    assert updated.json()["text"] == "Яка дата захисту?"
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_duplicate_example_conflicts(client: TestClient) -> None:
    sign_in(client, "maintainer")
    assert client.post("/api/examples", json=EXAMPLE).status_code == 201
    assert client.post("/api/examples", json=EXAMPLE).status_code == 409


def test_evaluated_example_cannot_be_changed(client: TestClient) -> None:
    sign_in(client, "maintainer")
    locked = next(item for item in client.get("/api/examples").json() if item["locked"])
    url = "/api/examples/" + str(locked["message_id"])
    assert client.put(url, json=EXAMPLE).status_code == 409
    assert client.delete(url).status_code == 409
