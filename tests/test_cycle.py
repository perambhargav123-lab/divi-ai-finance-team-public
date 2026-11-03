import json
from divi import cycle, cashcounter
from divi.cycle import O

def _reset(): json.dump([], open(O / "decisions.json", "w"))

def test_three_way_flags_only_palm_foods():
    bad = [r for r in cycle.three_way() if not r["match"]]
    assert [r["invoice"] for r in bad] == ["PI-0012"] and bad[0]["held_with_vat"] == 3738.35

def test_new_vendor_blocked():
    assert [v["vendor"] for v in cycle.vendor_checks() if not v["ok"]] == ["Quickline General Trading"]

def test_payment_run_reconciles():
    r = cycle.run()["payment_run"]
    assert r["pay_total"] == 168937.03 and r["hold_total"] == 31152.84 and r["defer_total"] == 69220.79
    assert all(x["invoice"] != "PI-0012" for x in r["pay"])

def test_runway_and_collections():
    r = cycle.run()
    assert r["runway"]["headroom"] == 105891.1 and r["runway"]["safe"]
    c = r["collections"]; assert c["total"] == 140000.0 and c["rows"][0]["customer"] == "Oasis Hotels FZE"
    o = c["rows"][0]; assert (o["overdue"], o["disputed"], o["chase"]) == (52000.0, 12000.0, 40000.0)
    assert c["chase_total"] == 128000.0 and "AED 40,000" in o["draft_en"] and "12,000" in o["draft_en"] and "12,000" in o["draft_ar"]
    assert all(x["status"] == "draft, not sent" and x["draft_ar"] for x in c["rows"])

def test_p2p_matches_cash_counter():
    _reset(); p2p = cycle.run()["strip"][0]["value"]
    cc = {l["label"]: l["amount"] for l in cashcounter.run()["lines"]}
    assert p2p == round(cc["Palm Foods overbilling held"] + cc["Risky payment to a new vendor stopped"], 2)

def test_close_checklist():
    k = cycle.close_checklist(); assert (k["done"], k["total"]) == (5, 7) and len(k["accruals"]) == 4
