import src.auth.router as auth_router


class DummyResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def test_get_token_success(client, monkeypatch):
    monkeypatch.setattr(
        auth_router.auth_service,
        "request_auth0_token",
        lambda _u, _p: {
            "status_code": 200,
            "body": DummyResponse(
                200,
                {
                    "access_token": "abc123",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "openid profile email",
                },
            ),
        },
    )

    response = client.post(
        "/auth/token",
        json={"username": "user-admin@acme.test", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "abc123"


def test_get_token_unauthorized(client, monkeypatch):
    monkeypatch.setattr(
        auth_router.auth_service,
        "request_auth0_token",
        lambda _u, _p: {
            "status_code": 401,
            "body": DummyResponse(
                401,
                {"error_description": "Wrong email or password"},
                text="Unauthorized",
            ),
        },
    )

    response = client.post(
        "/auth/token",
        json={"username": "user-admin@acme.test", "password": "bad"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"


def test_get_token_validation_error(client):
    response = client.post(
        "/auth/token",
        json={"username": "user-admin@acme.test"},
    )

    assert response.status_code == 422
