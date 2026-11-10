from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trivia_arena.app import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    # High ceilings so suite traffic does not trip join/lookup limiters.
    app = create_app(
        db_path=tmp_path / "test.db",
        create_rate=(10_000, 60.0),
        join_rate=(10_000, 60.0),
        lookup_rate=(10_000, 60.0),
    )
    with TestClient(app) as test_client:
        csrf = test_client.get("/api/auth/csrf").json()["csrf_token"]
        test_client.headers["X-CSRF-Token"] = csrf
        yield test_client
