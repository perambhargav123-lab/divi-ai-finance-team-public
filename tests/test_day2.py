import os
os.environ["DIVI_MOCK"] = "1"
from pathlib import Path
from divi.agents import reconciler, controller, redteam
D = Path(__file__).resolve().parent.parent / "data"

def _close():
    rec = reconciler.reconcile(reconciler.load(D/"bank_statement.csv"), reconciler.load(D/"ledger_cash.csv"))
    return controller.build(rec, review_flags={"JE-1041"})

def test_controller_balances_and_proves():
    c = _close()
    assert c["checklist"]["trial_balance_balances"]
    assert all(e["proof"] for e in c["entries"])
    assert all(v["proof"] for v in list(c["pnl"].values()) + list(c["balance_sheet"].values()))
    assert c["trial_balance"]["2300"]["amount"] == -18500.0  # hidden sale held for review
    assert 0 < c["vat_payable"] < 100000 and 0 < c["net_profit"] < 600000
    assert c["checklist"]["suspense_reviewed"] is False and c["commentary"]

def test_redteam_finds_seeded_anomalies():
    rules = {x["rule"] for x in redteam.scan()}
    assert {"duplicate_vendor_invoice", "large_payment_to_new_vendor", "round_amount_payment",
            "duplicate_bank_payment", "weekend_journal_by_junior"} <= rules
    assert "large_journal_without_senior" not in rules  # senior COGS journal is fine

def test_redteam_explanations_present():
    assert all("explanation" in x for x in redteam.scan())

def test_bank_charges_only_real_charges():
    assert _close()["trial_balance"]["6200"]["amount"] < 500
