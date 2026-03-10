import src.activity_logs.router as activity_router


def test_list_activity_logs(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        activity_router.activity_log_service,
        "list_activity_logs",
        lambda limit, last_evaluated_key: {
            "items": [{"id": "1", "action": "CREATE"}],
            "count": 1,
            "next_page_token": None,
        },
    )

    response = client.get("/activity-logs?limit=10", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_search_activity_logs(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        activity_router.activity_log_service,
        "search_activity_logs",
        lambda keyword, limit, last_evaluated_key: {
            "items": [{"id": "1", "keyword": keyword}],
            "count": 1,
            "next_page_token": None,
        },
    )

    response = client.get(
        "/activity-logs/search?keyword=admin&limit=5",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["keyword"] == "admin"


def test_search_activity_logs_requires_keyword(client, auth_headers):
    response = client.get("/activity-logs/search", headers=auth_headers)

    assert response.status_code == 422
