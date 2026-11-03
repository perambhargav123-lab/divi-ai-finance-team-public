import os
os.environ["DIVI_MOCK"] = "1"
from pathlib import Path
from fastapi.testclient import TestClient
from divi.app import app
c = TestClient(app); A = Path(__file__).resolve().parent.parent / "data" / "audio"

def test_dashboard_data_and_proof():
    assert "Divi" in c.get("/").text
    d = c.get("/api/data").json(); assert d["pnl"] and d["treasury"]["downside"]["lowest_week"]
    e = d["entries"][d["pnl"]["4000"]["proof"][0]]
    p = c.get("/api/proof/" + e["proof"][0].replace("#", "%23")).json(); assert p["row"]
    assert c.get("/api/proof/rule:accrual_audit_fee").json()["text"]

def test_proof_image_for_captured_doc():
    p = c.get("/api/proof/invoices.csv%23PI-0004").json(); assert p["image"].endswith(".png")
    assert c.get(p["image"]).status_code == 200

def test_voice_mock():
    r = c.post("/api/voice", files={"audio": ("q_en.wav", open(A / "q_en.wav", "rb"), "audio/wav")}).json()
    assert r["question"] and r["answer"] and r["proof"]
