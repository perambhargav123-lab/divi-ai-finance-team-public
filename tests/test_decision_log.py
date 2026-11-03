import json
from fastapi.testclient import TestClient
from divi.app import app
from divi import decision_log, auditor

def test_policy_and_decision_log_follow_owner():
    c = TestClient(app); p = auditor.O / "decisions.json"; old = p.read_text() if p.exists() else "[]"
    try:
        assert len(c.get("/api/policy").json()["policies"]) == 6
        p.write_text("[]"); r = c.get("/api/decision_log").json(); b = next(x for x in r["rows"] if x["flag"] == "large_payment_to_new_vendor")
        assert b["decision"] == "waiting for the owner" and b["policy"]["id"] == "P1"
        p.write_text(json.dumps([{"flag": "large_payment_to_new_vendor", "decision": "block", "time": "t"}]))
        b = next(x for x in c.get("/api/decision_log").json()["rows"] if x["flag"] == "large_payment_to_new_vendor")
        assert b["decision"] == "blocked" and b["decided_by"] == "Owner" and "blocked until a PO" in b["next_month"]
        assert all(q.get("policy") for q in auditor.run()["queries"])
    finally:
        p.write_text(old)
