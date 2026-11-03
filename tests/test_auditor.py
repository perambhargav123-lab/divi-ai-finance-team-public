import os
os.environ.setdefault("DIVI_MOCK", "1")
from fastapi.testclient import TestClient
from divi import auditor, cashcounter, sources
from divi.app import app

c = TestClient(app)


def test_auditor_reperforms_and_adjusts():
    r = auditor.run(); q = {x["id"]: x for x in r["queries"]}
    assert q["Q1"]["status"] == "adjusted" and abs(q["Q1"]["difference"] - 78459.47) < 0.01
    assert abs(q["Q2"]["pnl"] - 18500 / 1.05) < 0.01
    assert q["Q5"]["status"] == "control point" and q["Q7"]["status"] == "cleared"
    assert r["net_profit_after"] < r["net_profit_before"] and r["cert_id"].startswith("DV-AUD-")
    assert all(all(v for v in x["evidence"].values()) for x in r["queries"])  # every citation resolves


def test_signature_is_stable():
    assert auditor.run()["signature"] == auditor.run()["signature"]


def test_cash_counter_lines_resolve_and_sum():
    r = cashcounter.run()
    assert abs(r["total"] - sum(l["amount"] for l in r["lines"])) < 0.01
    assert all(sources.resolve(l["ref"]) for l in r["lines"])


def test_endpoints():
    assert c.get("/api/auditor").json()["queries"]
    assert c.get("/api/cash_counter").json()["total"] > 0
    assert "Auditor signs off" in c.get("/").text


def test_q5_follows_ui_escalation_buttons(tmp_path, monkeypatch):
    import json
    from divi import auditor
    p = auditor.O / "decisions.json"; old = p.read_text() if p.exists() else "[]"
    try:
        p.write_text(json.dumps([{"flag": "large_payment_to_new_vendor", "decision": "approve_escalation"}]))
        r = auditor.run(); q5 = next(q for q in r["queries"] if q["id"] == "Q5")
        assert "blocked" in q5["divi"] and r["opinion"].startswith("Signed: no material")
        assert r["models"]["auditor"] != r["models"]["preparer"]
    finally:
        p.write_text(old)


def test_b108_three_states_and_cash():
    import json
    from divi import auditor, cashcounter
    p = auditor.O / "decisions.json"; old = p.read_text() if p.exists() else "[]"
    try:
        for d, q5, op, cash in ((None, "still waiting", "open item", 315527.2), ("block", "blocked", "blocked by the owner", 315527.2),
                                ("release", "released", "released by the owner", 265527.2)):
            p.write_text(json.dumps([{"flag": "large_payment_to_new_vendor", "decision": d}] if d else []))
            r = auditor.run(); assert q5 in r["queries"][4]["divi"] and op in r["opinion"]
            assert cashcounter.run()["total"] == cash
    finally:
        p.write_text(old)
