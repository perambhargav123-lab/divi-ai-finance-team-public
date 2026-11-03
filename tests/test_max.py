import os
from divi import llm


def test_fallback_when_model_fails(monkeypatch):
    class Boom:
        class responses:
            @staticmethod
            def create(**k): raise TimeoutError("down")
    monkeypatch.setattr(llm, "is_mock", lambda *a: False)
    monkeypatch.setattr(llm, "_client", lambda p: (Boom, "m"))
    monkeypatch.setattr(llm._time, "sleep", lambda s: None)
    out = llm.ask("test_fallback", "unique prompt never cached 9f3a", mock_response="SAFE")
    assert out == "SAFE" and llm.TRACE[-1]["source"].startswith("fallback")
    assert llm.complete("x", mock_response="OK2") == "OK2"


def test_near_duplicate_rule_and_benchmark():
    from divi import benchmark
    r = benchmark.run()
    assert r["detected"] == r["injected"] == 20 and r["precision"] == 1.0
    near = [x for x in r["rows"] if x.get("hard") and "near" in x["kind"]][0]
    assert near["detected"] and "near_duplicate_vendor_invoice" in near["by"]


def test_max_endpoints():
    from fastapi.testclient import TestClient
    from divi.app import app
    c = TestClient(app)
    s = c.get("/api/scoreboard").json(); assert s["fraud_caught"] == "20/20" and s["aed_found"] > 100000
    m = c.get("/api/max").json(); assert m["long_context"]["grounded"] >= 1 and len(m["tool_calls"]) == 3
    assert all(v["matched"] == v["of"] for v in m["vision"]["crumpled"])
    assert c.get("/api/sample.csv").status_code == 200 and c.get("/favicon.ico").status_code == 200
    assert "events" in c.get("/api/audit").json()
    assert "B160" in c.get("/api/cite/bank_statement.csv%23B160").json()["text"]


def test_fx_revaluation_balances():
    from divi import maxai
    r = maxai.fx(); e = r["entry"]["lines"]
    assert round(sum(l["debit"] for l in e), 2) == round(sum(l["credit"] for l in e), 2) == abs(r["net_gain_loss"])
