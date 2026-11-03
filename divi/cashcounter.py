"""Cash counter: one honest number for the owner, split by how sure it is.
recovered = money already lost that Divi can get back; protected = money stopped before it left;
released = cash the 13-week plan brings in earlier. Every line links to its source."""
import json
from pathlib import Path
from divi import sources

O = Path(__file__).resolve().parents[1] / "out"

def _amt(ref, field="amount"):
    t = sources.resolve(ref); return abs(float(json.loads(t.split("; ")[0])[field]))

def run():
    ins = json.load(open(O / "insights.json")); ob = next(f for f in ins["judgment"]["findings"] if f["kind"] == "overbilling")
    lev = {l["id"]: l for l in json.load(open(O / "treasury_13w.json"))["levers"]}
    lines = [
        dict(kind="recovered", label="Hidden sale found in the bank", amount=_amt("bank_statement.csv#B160"), ref="bank_statement.csv#B160"),
        dict(kind="recovered", label="Duplicate payment to Horizon", amount=_amt("bank_statement.csv#B136"), ref="bank_statement.csv#B136"),
        dict(kind="recovered", label="Duplicate Sahara Freight invoice", amount=_amt("invoices.csv#PI-0006-A", "total"), ref="invoices.csv#PI-0006-A"),
        dict(kind="protected", label="Palm Foods overbilling held", amount=round(ob["amount"] * 1.05, 2), ref=ob["cites"][0]),
        dict(kind="protected", label="Risky payment to a new vendor stopped", amount=_amt("bank_statement.csv#B108"), ref="bank_statement.csv#B108"),
        dict(kind="released", label=lev["L1"]["name"], amount=lev["L1"]["amount"], ref="treasury#L1"),
        dict(kind="released", label=lev["L2"]["name"], amount=lev["L2"]["amount"], ref="treasury#L2"),
    ]
    from divi import auditor
    if auditor._decision("B108") == "release":  # the owner let the payment go, so it is no longer protected
        lines = [l for l in lines if l["ref"] != "bank_statement.csv#B108"]
    tot = {k: round(sum(l["amount"] for l in lines if l["kind"] == k), 2) for k in ("recovered", "protected", "released")}
    return dict(lines=lines, totals=tot, total=round(sum(tot.values()), 2),
                note="Released cash is earlier collection and stock sales over 13 weeks, not new profit. Early-pay discounts are left out because they are annual.")
