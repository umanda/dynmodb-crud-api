import src.auth.service as auth_service
import src.channels.router as channels_router
from src.auth.constants import PERMISSION_READ_CHANNEL


def _channel_payload(channel_code: str = "UST59FOXWEATHER") -> dict:
    return {
        "_table": "test-table",
        "ChannelCode": channel_code,
        "TVorRadio": "true",
        "Label": "nattvnormal",
        "Service": "TESTService-A",
        "URLs": ["http://example.com/live.m3u8"],
    }


def test_list_channels(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        channels_router.channel_service,
        "list_channels",
        lambda table, limit, last_evaluated_key: {
            "items": [{"ChannelCode": "A1", "_table": "test-table"}],
            "count": 1,
            "next_page_token": None,
        },
    )

    response = client.get("/channels?limit=20", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_get_channel(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        channels_router.channel_service,
        "get_channel",
        lambda channel_code, table: {
            "ChannelCode": channel_code,
            "Service": "TESTService-A",
            "URLs": ["http://example.com/live.m3u8"],
            "_table": table or "test-table",
        },
    )

    response = client.get("/channels/UST59FOXWEATHER", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["ChannelCode"] == "UST59FOXWEATHER"


def test_create_channel(client, auth_headers, monkeypatch):
    payload = _channel_payload()

    monkeypatch.setattr(channels_router, "validate_table", lambda _table: None)
    monkeypatch.setattr(
        channels_router.channel_service,
        "create_channel",
        lambda payload_obj, user: {
            "ChannelCode": payload_obj.ChannelCode,
            "Service": payload_obj.Service,
            "URLs": payload_obj.URLs,
            "_table": payload_obj.table,
        },
    )

    response = client.post("/channels", json=payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["ChannelCode"] == payload["ChannelCode"]


def test_replace_channel(client, auth_headers, monkeypatch):
    payload = _channel_payload()

    monkeypatch.setattr(channels_router, "validate_table", lambda _table: None)
    monkeypatch.setattr(
        channels_router.channel_service,
        "replace_channel",
        lambda channel_code, payload_obj, user: {
            "ChannelCode": channel_code,
            "Service": payload_obj.Service,
            "URLs": payload_obj.URLs,
            "_table": payload_obj.table,
        },
    )

    response = client.put(
        "/channels/UST59FOXWEATHER",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["ChannelCode"] == "UST59FOXWEATHER"


def test_replace_channel_code_mismatch_returns_400(client, auth_headers):
    response = client.put(
        "/channels/CHANNEL_A",
        json=_channel_payload(channel_code="CHANNEL_B"),
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "must match the URL path" in response.json()["detail"]


def test_patch_channel(client, auth_headers, monkeypatch):
    payload = _channel_payload()

    monkeypatch.setattr(channels_router, "validate_table", lambda _table: None)
    monkeypatch.setattr(
        channels_router.channel_service,
        "patch_channel",
        lambda channel_code, payload_obj, user: {
            "ChannelCode": channel_code,
            "Service": payload_obj.Service,
            "URLs": payload_obj.URLs,
            "_table": payload_obj.table,
        },
    )

    response = client.patch(
        "/channels/UST59FOXWEATHER",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["ChannelCode"] == "UST59FOXWEATHER"


def test_patch_channel_code_mismatch_returns_400(client, auth_headers):
    response = client.patch(
        "/channels/CHANNEL_A",
        json=_channel_payload(channel_code="CHANNEL_B"),
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_delete_channel(client, auth_headers, monkeypatch):
    monkeypatch.setattr(channels_router, "validate_table", lambda _table: None)
    monkeypatch.setattr(
        channels_router.channel_service,
        "delete_channel",
        lambda channel_code, table, user: {
            "deleted": True,
            "ChannelCode": channel_code,
            "_table": table,
        },
    )

    response = client.delete(
        "/channels/UST59FOXWEATHER?table=test-table",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_delete_channel_requires_table(client, auth_headers):
    response = client.delete("/channels/UST59FOXWEATHER", headers=auth_headers)

    assert response.status_code == 422


def test_protected_endpoint_without_token_returns_403(client):
    response = client.get("/channels")

    assert response.status_code == 403


def test_permission_denied_returns_403(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        auth_service,
        "decode_token",
        lambda _token: {"permissions": [PERMISSION_READ_CHANNEL]},
    )

    response = client.post(
        "/channels",
        json=_channel_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 403
