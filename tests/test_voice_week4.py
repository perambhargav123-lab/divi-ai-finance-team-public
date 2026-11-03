from fastapi.testclient import TestClient
from divi.app import app

def test_voice_week4_replays_recorded_answer():
    c = TestClient(app); r = c.get("/api/voice_week4").json()
    assert r["question"] == "Are we safe in week 4?" and "247,376" in r["answer"] and r["proof"]
    assert c.get("/audio/q_week4.mp3").status_code == 200
