from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_config_shape() -> None:
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "app_version" in data
    assert data["llm"]["provider"] == "mock"
    assert data["llm"]["configured"] is True
    assert "model" in data["llm"]
    assert data.get("demo_mode") is False
    assert data.get("demo_sample_video_url") is None
