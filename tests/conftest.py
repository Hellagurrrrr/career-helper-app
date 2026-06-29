from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import reset_all


@pytest.fixture()
def client():
    # `with` triggers the lifespan (seeds public catalogs).
    with TestClient(app) as c:
        yield c
    reset_all()


def register(client: TestClient, email="alex@example.com", name="Alex Chen", password="secret123"):
    resp = client.post(
        "/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    return resp


def auth_headers(client: TestClient, **kwargs) -> dict[str, str]:
    resp = register(client, **kwargs)
    assert resp.status_code == 201, resp.text
    token = resp.json()["tokens"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}
