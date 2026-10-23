from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "DevOps Automation Platform is running"
    }


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_metrics():
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "api_requests_total" in response.text


def test_workload_fast():
    response = client.get("/api/workload/fast")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_workload_slow():
    response = client.get("/api/workload/slow")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_workload_error():
    response = client.get("/api/workload/error")
    assert response.status_code == 500


def test_dashboard():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "ForgeOps" in response.text


def test_telemetry_stats():
    response = client.get("/api/telemetry/stats")
    assert response.status_code == 200
    assert "total" in response.json()
    assert "pods" in response.json()


def test_chaos_kill_pod():
    response = client.post("/api/chaos/kill-pod")
    assert response.status_code == 200
    assert response.json()["action"] == "pod_killed"
