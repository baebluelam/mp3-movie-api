from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from src.storage import MovieStorage


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client using a temporary SQLite database."""
    test_storage = MovieStorage(tmp_path / "movies.db")
    monkeypatch.setattr(main, "storage", test_storage)

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def sample_csv_bytes():
    """Read the sample movie CSV as bytes."""
    return Path("fixtures/sample_movies.csv").read_bytes()


@pytest.fixture
def uploaded_movies(client, sample_csv_bytes):
    """Upload the sample movies before a test."""
    response = client.post(
        "/upload",
        files={
            "file": (
                "sample_movies.csv",
                sample_csv_bytes,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    return response.json()