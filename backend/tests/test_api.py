import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from tests.test_core import TEXT  # noqa: E402


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import app.db as db

    db.DB_PATH = str(tmp_path_factory.mktemp("db") / "t.db")
    with TestClient(app) as c:
        yield c


def test_health_and_methods(client):
    assert client.get("/api/health").json()["status"] == "ok"
    ids = [m["id"] for m in client.get("/api/methods").json()["methods"]]
    assert {"textrank", "abstractive", "hybrid"} <= set(ids)


def test_summarize_compare_history(client):
    r = client.post("/api/summarize", json={"text": TEXT, "method": "textrank", "ratio": 0.3}).json()
    assert r["summary"] and r["history_id"]
    c = client.post("/api/compare", json={"text": TEXT, "methods": ["lead", "lsa"], "reference": "Solar is growing."}).json()
    assert len(c["results"]) == 2 and "rouge" in c["results"][0]
    assert client.get("/api/history").json()["items"]
    assert client.delete(f"/api/history/{r['history_id']}").status_code == 200


def test_validation(client):
    assert client.post("/api/summarize", json={"text": "short"}).status_code == 422
    assert client.post("/api/summarize", json={"text": TEXT, "method": "nope"}).status_code == 422


def test_url_ssrf_blocked(client):
    assert client.post("/api/fetch-url", json={"url": "http://127.0.0.1:8000"}).status_code == 422
