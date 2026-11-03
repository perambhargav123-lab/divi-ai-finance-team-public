import os
os.environ["DIVI_MOCK"] = "1"
from divi.agents import treasurer as t

def test_forecast_shape_and_downside_worse():
    b, d = t.forecast(316223.42, "base"), t.forecast(316223.42, "downside")
    assert len(b["closing"]) == 13 and b["weeks"][0] == "2026-11-02"
    assert d["lowest_cash"] < b["lowest_cash"] and d["closing"][-1] < b["closing"][-1]

def test_levers_total_240k_and_lift_curve():
    p = t.plan(316223.42)
    assert sum(L["amount"] for L in p["levers"]) == 240000.0
    assert abs(p["base_with_levers"]["savings"] - 4887.5) < 1 and 50000 < p["base_with_levers"]["released_total"] < 240000
    assert p["downside_with_levers"]["lowest_cash"] > p["downside"]["lowest_cash"]
    assert p["levers"][0]["id"] == "L1" and all(L["owner"] and L["action"] for L in p["levers"])
    assert p["narrative"]
