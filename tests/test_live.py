import os, json
os.environ["DIVI_MOCK"] = "1"
from fastapi.testclient import TestClient
from divi import live
from divi.app import app
c = TestClient(app)

def test_cache_recorded_from_real_run():
    ev = json.load(open(live.CACHE, encoding="utf-8"))
    kinds = [e["kind"] for e in ev]
    assert kinds[0] == "start" and kinds[-1] == "done" and kinds.count("doc") == 4
    assert sum(e["data"].get("accuracy", 0) == 8 for e in ev if e["kind"] == "doc") >= 3
    assert {"debate", "approval", "fraud", "forecast"} <= set(kinds)

def test_debate_two_flags_escalated():
    ev = json.load(open(live.CACHE, encoding="utf-8"))
    ap = [e["data"]["flag"] for e in ev if e["kind"] == "approval"]
    assert set(ap) == {"large_payment_to_new_vendor", "weekend_journal_by_junior"}
    assert {e["agent"] for e in ev if e["kind"] == "debate"} == {"redteam", "controller"}

def test_fraud_card_and_meter_fills():
    ev = json.load(open(live.CACHE, encoding="utf-8"))
    fr = next(e for e in ev if e["kind"] == "fraud")["data"]
    assert fr["amount"] == 18500 and len(fr["chain"]) == 4 and fr["query"]
    pct = [e["meter"]["overall"]["total"] for e in ev]; assert pct == sorted(pct) and pct[-1] > 600

def test_mock_run_and_stream_replay():
    ev = list(live.run()); assert ev[-1]["kind"] == "done"
    with c.stream("GET", "/api/close/stream?replay=1&speed=50") as r:
        body = "".join(r.iter_text())
    assert body.count("data: ") == 1 + len(json.load(open(live.CACHE, encoding="utf-8")))
    assert c.post("/api/decision", json={"flag": "x", "decision": "approve_escalation"}).json()["ok"]
    assert c.post("/api/reset").json()["ok"]


def test_replay_pacing_45_to_60s():
    import json
    from divi.live import pace, CACHE
    ev = json.load(open(CACHE)); prev = ev[0]["t"]; s = 0
    for e in ev: s += pace(e, e["t"] - prev); prev = e["t"]
    assert 45 <= s <= 58
