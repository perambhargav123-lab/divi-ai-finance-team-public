import json, os
os.environ.setdefault("DIVI_MOCK", "1")
from fastapi.testclient import TestClient
from divi import edge
from divi.app import app

c = TestClient(app)


def test_rule_validation_rejects_unknown_fields():
    import pytest
    with pytest.raises(ValueError):
        edge.validate(dict(source="payments", conditions=[dict(field="__import__", op=">", value=1)]))


def test_owner_rule_catches_new_vendor_payment(tmp_path, monkeypatch):
    monkeypatch.setattr(edge, "RULES", tmp_path / "r.json")
    r = edge.add_rule("flag any payment over AED 20k to a vendor added this month")
    assert any(h["id"] == "B108" for h in r["hits"])
    assert any(x["owner_rule"] for x in edge.run_rules())


def test_challenge_catches_fake_vendor_and_scores_a_miss(tmp_path, monkeypatch):
    monkeypatch.setattr(edge, "BOARD", tmp_path / "b.json")
    caught = edge.challenge("a", bank=[dict(date="2026-10-27", description="TT TO DUNE STAR GENERAL TRADING", amount=45000)],
                            vendors=[dict(vendor="DUNE STAR GENERAL TRADING", created="2026-10-24")])
    assert not caught["won"] and caught["score"] == 0
    miss = edge.challenge("b", bank=[dict(date="2026-10-20", description="TT TO DUNES CONSULTING FZE", amount=9400)])
    assert miss["won"] and miss["score"] == 9400
    from divi.agents import redteam
    assert redteam.OVERRIDE == {}


def test_edge_endpoint_and_covenant_grounded():
    r = c.get("/api/edge").json()
    liq = next(x for x in r["loan"]["covenants"] if x["metric"] == "min_weekly_cash_aed")
    assert liq["grounded"] and liq["page"] == 57
    base = next(t for t in liq["tests"] if t["scenario"] == "base")
    assert not base["ok"] and base["week"] == 3
    assert all("model" in s and "why" in s for s in r["router"]["steps"])
    assert c.get("/challenge").status_code == 200


def test_je1040_cogs_rollforward_ties():
    g = edge.cogs_check()
    assert abs(g["opening_stock"] + g["purchases"] - g["counted_stock"] - g["cogs_from_count"]) < 0.01
    assert round(g["gap"], 2) == 78459.47 and "not posted" in g["proposal"]["status"]


def test_extras_endpoint_and_exports_balance():
    x = c.get("/api/extras").json()
    assert x["sam"]["matched"] == x["sam"]["of"] and all(ch["agrees"] for ch in x["tax"]["checks"])
    import csv
    from collections import defaultdict
    tot = defaultdict(float)
    for r in csv.DictReader(open("out/exports/xero_manual_journals.csv")): tot[r["*Narration"]] += float(r["*Amount"])
    assert all(abs(v) < 0.01 for v in tot.values())
    assert c.get("/media/sam/receipt_cutout.png").status_code == 200


def test_verifier_date_fact_check_corrects_weekday():
    from divi import verify
    fixed, errs = verify.check_dates("Weekday, junior poster", '{"date": "2026-10-24"}')
    assert fixed.startswith("Weekend") and "Saturday" in errs[0]
    p = c.get("/api/insights").json()["proof"]
    assert any("Date-fact" in r["why"] for r in p["rejected_items"])


def test_challenge_learning_loop_catches_rerun(tmp_path, monkeypatch):
    monkeypatch.setattr(edge, "BOARD", tmp_path / "b.json"); monkeypatch.setattr(edge, "RULES", tmp_path / "r.json")
    monkeypatch.setattr(edge, "O", tmp_path)
    miss = edge.challenge("b", bank=[dict(date="2026-10-20", description="TT TO DUNES CONSULTING FZE", amount=9400)])
    assert miss["won"] and miss["proposal"] and miss["proposal"]["real_book_hits"] == []
    again = edge.learn_approve()
    assert not again["won"] and any("vendor_master" in r for r in again["caught_by"])
