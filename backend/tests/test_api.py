import time

from fastapi.testclient import TestClient

from jarvis.server import create_app


def test_api_requires_token(services):
    app = create_app(services, token="T")
    with TestClient(app) as c:
        assert c.get("/api/bootstrap").status_code == 401
        assert c.get("/api/bootstrap", headers={"x-jarvis-token": "wrong"}).status_code == 401
        r = c.get("/api/bootstrap", headers={"x-jarvis-token": "T"})
        assert r.status_code == 200 and r.json()["settings"]["provider"]["active"] == "mock"
        assert c.get("/api/bootstrap", headers={"x-jarvis-token": "T", "host": "evil.com"}).status_code == 403


def test_chat_roundtrip_and_memory_api(services):
    app = create_app(services, token="T")
    h = {"x-jarvis-token": "T"}
    with TestClient(app) as c:
        with c.websocket_connect("/ws?token=T") as ws:
            assert ws.receive_json()["type"] == "status"
            r = c.post("/api/chat", json={"text": "hello"}, headers=h).json()
            for _ in range(50):
                evt = ws.receive_json()
                if evt["type"] == "message" and evt["role"] == "assistant":
                    break
            assert "[Mock" in evt["content"]
        msgs = c.get(f"/api/conversations/{r['conversation_id']}", headers=h).json()
        assert [m["role"] for m in msgs] == ["user", "assistant"]
        mid = c.post("/api/memories", json={"category": "preference", "content": "likes dark UI"}, headers=h).json()["id"]
        assert c.get("/api/memories?q=dark", headers=h).json()[0]["id"] == mid
        assert c.post("/api/memories", json={"category": "fact", "content": "password: x"}, headers=h).status_code == 400
        assert c.delete(f"/api/memories/{mid}", headers=h).json()["ok"]
        s = c.patch("/api/settings", json={"security": {"safe_mode": True}}, headers=h).json()
        assert s["security"]["safe_mode"] is True
        assert c.post("/api/secrets", json={"name": "evil", "value": "x"}, headers=h).status_code == 400
