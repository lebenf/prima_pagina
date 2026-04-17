import pytest


async def test_health_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["env"] == "development"


async def test_missing_route(client):
    response = await client.get("/api/v1/nonexistent")
    assert response.status_code == 404
