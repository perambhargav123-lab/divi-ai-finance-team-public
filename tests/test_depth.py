import json, os
os.environ.setdefault("DIVI_MOCK", "1")
from divi import verify, sources, cashai, judgment

def test_planted_false_claims_rejected():
    out = verify.verify([dict(c) for c in verify.PLANTED], "test")
    assert all(not c["verified"] for c in out)

def test_true_claim_passes_det():
    ok, _ = verify.check_det(dict(claim="Desert Rose paid AED 18,500.", cites=["bank_statement.csv#B160"]))
    assert ok

def test_sources_resolve():
    assert "11.00" in sources.resolve("contracts/palm_foods_supply.txt#L5")
    assert sources.resolve("messages.jsonl#M01") and sources.resolve("nope.csv#x") is None

def test_overbilling_found_from_contract():
    f = judgment.contract_findings(dict(prices=[dict(vendor="Palm Foods Import", item="Basmati rice per kg", price=11.0, cite="contracts/palm_foods_supply.txt#L5")], terms=[]))
    assert [x["invoice"] for x in f] == ["PI-0012"] and abs(f[0]["amount"] - 3560.33) < 0.1

def test_monte_carlo_band_ordered():
    m = cashai.behaviour([]); r = cashai.simulate(cashai.opening_cash(), m, n=300)
    assert all(a <= b <= c for a, b, c in zip(r["p10"], r["p50"], r["p90"])) and 0 <= r["p_negative_w6"] <= 1

def test_benchmark_scores():
    from divi import benchmark
    r = benchmark.run()
    assert r["injected"] == 20 and r["detection_rate"] >= 0.9 and r["precision"] >= 0.9 and not r["decoys_flagged"]

def test_vat_form201_ties_and_ct_threshold():
    from divi import uae
    v = uae.vat201(); assert v["ties_to_ledger"]
    ct = uae.corporate_tax(); assert ct["estimated_tax"] == round(max(ct["annualised_profit"] - 375000, 0) * 0.09, 2)

def test_learning_projection_improves():
    from divi import learning
    s = learning.state(); assert s["months"][0]["automated_pct"] < s["months"][1]["automated_pct"] <= s["months"][2]["automated_pct"]
