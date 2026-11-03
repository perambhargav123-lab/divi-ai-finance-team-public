import json, os
from pathlib import Path
os.environ["DIVI_MOCK"] = "1"
from divi import llm
from divi.agents import capture, reconciler
D = Path(__file__).resolve().parent.parent / "data"

def test_capture_mock_all_docs_valid():
    truth = json.load(open(D/"docs"/"ground_truth.json", encoding="utf-8"))
    assert len(truth) == 15
    for t in truth:
        out = capture.capture(str(D/"docs"/t["file"]), truth={k: t[k] for k in capture.FIELDS})
        assert out["issues"] == [], out

def test_capture_flags_bad_vat():
    assert "VAT is not 5% of net" in capture.validate(dict(vendor="x",invoice_no="1",date="d",net=100,vat=7,total=107,currency="AED",trn="1"))

def test_reconciler_rate_and_exceptions():
    bank = reconciler.load(D/"bank_statement.csv"); ledger = reconciler.load(D/"ledger_cash.csv")
    assert len(bank) == 200
    r = reconciler.reconcile(bank, ledger)
    assert r["automation_rate"] >= 0.9
    cats = [m[2] for m in r["matches"] if m[1] is None]
    assert "unrecorded_receipt" in cats and cats.count("bank_charge") == 3
    hidden = [b for b in bank if float(b["amount"]) == 18500.0]
    assert any(m[0] == hidden[0]["bank_id"] and m[2] == "unrecorded_receipt" for m in r["matches"])
    assert {"CHQ-1", "CHQ-2", "CHQ-3"} <= set(r["unmatched_ledger"])  # timing differences
    assert r["stats"]["llm"] == len(cats)

def test_levers_about_240k():
    assert abs(json.load(open(D/"levers_expected.json"))["total"] - 240000) < 5000

def test_anomalies_seeded():
    inv = (D/"invoices.csv").read_text(); j = (D/"journals.csv").read_text()
    assert "duplicate vendor invoice" in inv and "round 50,000" in inv and "weekend journal" in j

def test_duplicate_payment_and_date_normalise():
    bank = reconciler.load(D/"bank_statement.csv"); r = reconciler.reconcile(bank, reconciler.load(D/"ledger_cash.csv"))
    assert sum(m[2] == "duplicate_payment" for m in r["matches"]) == 1 and r["stats"]["llm"] == 4
    assert capture.normalise({"date": "11-10-2026"})["date"] == "2026-10-11"
