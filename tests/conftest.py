from collections.abc import Iterator
from pathlib import Path
from shutil import copy2, copytree

import pytest
from fastapi.testclient import TestClient

from app.auth import create_account
from app.database import initialize_database
from app.main import create_app
from app.settings import DATABASE_FILES, Settings
from app.setup import seed_examples
from app.training import train_and_publish

TEST_PASSWORD = "classifier test phrase"


@pytest.fixture(scope="session")
def trained_settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    settings = Settings(tmp_path_factory.mktemp("model"))
    initialize_database(settings.database)
    seed_examples(settings.database, DATABASE_FILES / "training_examples.csv")
    train_and_publish(settings)
    for role in ("operator", "coordinator", "maintainer"):
        create_account(settings.database, role, TEST_PASSWORD, role)
    return settings


@pytest.fixture
def app_settings(tmp_path: Path, trained_settings: Settings) -> Settings:
    settings = Settings(tmp_path)
    copy2(trained_settings.database, settings.database)
    copytree(trained_settings.artifacts, settings.artifacts)
    return settings


@pytest.fixture
def client(app_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(app_settings), base_url="http://127.0.0.1") as test_client:
        yield test_client
