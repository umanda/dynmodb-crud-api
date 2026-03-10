def test_health_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tables_list(client):
    response = client.get("/tables")

    assert response.status_code == 200
    payload = response.json()
    assert "tables" in payload
    assert isinstance(payload["tables"], list)
