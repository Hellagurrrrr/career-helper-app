from __future__ import annotations

from tests.conftest import register


def _register_with_tokens(client, email="alex@example.com", password="secret123"):
    resp = register(client, email=email, password=password)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body, {"Authorization": f"Bearer {body['tokens']['accessToken']}"}


def test_settings_view_and_notification_preferences(client):
    body, headers = _register_with_tokens(client)

    settings = client.get("/v1/settings", headers=headers)
    assert settings.status_code == 200
    assert settings.json()["account"]["email"] == body["user"]["email"]
    assert settings.json()["notifications"]["enabled"] is True

    updated = client.put("/v1/settings/notifications", json={"enabled": False}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert updated.json()["updatedAt"] > 0

    persisted = client.get("/v1/settings", headers=headers)
    assert persisted.json()["notifications"]["enabled"] is False


def test_settings_change_password_validation_and_login(client):
    body, headers = _register_with_tokens(client)

    short = client.post(
        "/v1/settings/password",
        json={"currentPassword": "secret123", "newPassword": "short"},
        headers=headers,
    )
    assert short.status_code == 400
    assert short.json()["error"]["message"] == "New password must be at least 6 characters."
    assert short.json()["error"]["details"]["field"] == "newPassword"

    wrong = client.post(
        "/v1/settings/password",
        json={"currentPassword": "bad-password", "newPassword": "newsecret123"},
        headers=headers,
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["message"] == "Current password is incorrect."

    changed = client.post(
        "/v1/settings/password",
        json={"currentPassword": "secret123", "newPassword": "newsecret123"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "updated"

    old_login = client.post(
        "/v1/auth/login", json={"email": body["user"]["email"], "password": "secret123"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/v1/auth/login", json={"email": body["user"]["email"], "password": "newsecret123"}
    )
    assert new_login.status_code == 200

    refresh = client.post("/v1/auth/refresh", json={"refreshToken": body["tokens"]["refreshToken"]})
    assert refresh.status_code == 401


def test_settings_reset_demo_data_preserves_account_and_preferences(client):
    _body, headers = _register_with_tokens(client)
    client.put("/v1/settings/notifications", json={"enabled": False}, headers=headers)
    client.put("/v1/profile", json={"name": "Alex", "skills": ["React"]}, headers=headers)
    created_goal = client.post("/v1/goals", json={"catalogId": "1"}, headers=headers)
    assert created_goal.status_code == 201

    reset = client.post("/v1/settings/reset-demo-data", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["status"] == "reset"

    assert client.get("/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/v1/profile", headers=headers).status_code == 404
    assert client.get("/v1/goals", headers=headers).json() == []
    assert client.get("/v1/settings", headers=headers).json()["notifications"]["enabled"] is False


def test_settings_repository_default_and_isolation(client):
    # Regression guard for the user_settings repository slice: a user with no
    # stored row gets the default, preferences are per-user, and a second user
    # registering must not cascade-wipe the first user's preference.
    _b1, alice = _register_with_tokens(client, email="alice@example.com")
    assert client.get("/v1/settings", headers=alice).json()["notifications"]["enabled"] is True

    client.put("/v1/settings/notifications", json={"enabled": False}, headers=alice)

    _b2, bob = _register_with_tokens(client, email="bob@example.com")
    assert client.get("/v1/settings", headers=alice).json()["notifications"]["enabled"] is False
    assert client.get("/v1/settings", headers=bob).json()["notifications"]["enabled"] is True


def test_settings_delete_account_removes_auth_and_data(client):
    body, headers = _register_with_tokens(client)
    client.put("/v1/profile", json={"name": "Alex"}, headers=headers)

    deleted = client.delete("/v1/settings/account", headers=headers)
    assert deleted.status_code == 204

    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 401

    login = client.post(
        "/v1/auth/login", json={"email": body["user"]["email"], "password": "secret123"}
    )
    assert login.status_code == 404
    assert login.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"
