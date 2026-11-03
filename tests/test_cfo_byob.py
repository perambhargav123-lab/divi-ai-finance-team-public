import os
os.environ["DIVI_MOCK"] = "1"
from pathlib import Path
from fastapi.testclient import TestClient
from divi.app import app
from divi import byob, voice, llm
import json
c = TestClient(app); D = Path(__file__).resolve().parent.parent / "data"; O = D.parent / "out"

def test_chat_survive_week6_offers_credit_action():
    r = c.post("/api/chat", json={"q": "Can we survive week 6?"}).json()
    assert r["answer"] and r["actions"]

def test_credit_need_and_pdf_pack():
    t = json.load(open(O / "treasury_13w.json")); assert voice.credit_need(t) == 165000
    r = c.post("/api/credit_line").json(); assert r["amount"] == 165000 and r["letter"]
    pdf = c.get(r["pdf"]); assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"

def test_byob_mapping_checks_and_forecast():
    r = byob.run((D / "sample_byob_bank.csv").read_text(), None)
    assert r["mapping"]["debit"] == "Withdrawal (AED)" and r["mapping"]["credit"] == "Deposit (AED)"
    assert r["checks"]["transactions"] == 61 and len(r["forecast"]) == 13
    assert any("Round payment AED 25,000" in f for f in r["findings"])
    up = c.post("/api/byob", files={"bank": ("b.csv", (D / "sample_byob_bank.csv").read_bytes(), "text/csv")}).json()
    assert up["checks"]["transactions"] == 61

def test_baseten_flag_mock_ready(monkeypatch):
    monkeypatch.setenv("DIVI_PROVIDER", "baseten"); monkeypatch.delenv("BASETEN_API_KEY", raising=False); monkeypatch.delenv("DIVI_MOCK", raising=False)
    assert llm.default_provider() == "baseten" and llm.is_mock("baseten")
    assert llm.complete("hi", mock_response="ok") == "ok"
