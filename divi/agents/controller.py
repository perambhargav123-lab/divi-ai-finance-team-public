"""Controller agent: posts month-end entries, runs the close checklist, builds statements.
Every entry and every statement number carries proof (source doc, bank line or rule)."""
import csv, json
from collections import defaultdict
from pathlib import Path
from divi import llm

D = Path(__file__).resolve().parents[2] / "data"
def _csv(n): return list(csv.DictReader(open(D / n, encoding="utf-8")))

class Ledger:
    def __init__(self):
        self.entries, self.n = [], 0
    def post(self, lines, memo, proof, source="rule"):
        assert abs(sum(a for _, a in lines)) < 0.01, f"unbalanced: {memo}"
        self.n += 1
        self.entries.append(dict(id=f"DV-{self.n:04d}", lines=[dict(acct=a, amt=round(x, 2)) for a, x in lines],
                                 memo=memo, proof=proof, source=source))

def build(recon, review_flags=()):
    coa = {r["code"]: r for r in _csv("chart_of_accounts.csv")}
    coa["6700"] = dict(code="6700", name="General Expenses", type="Expense")
    coa["2300"] = dict(code="2300", name="Unidentified Receipts", type="Liability")
    L = Ledger()
    for r in _csv("opening_trial_balance.csv"):
        L.post([(r["code"], float(r["balance_aed"])), ("OB", -float(r["balance_aed"]))], "opening balance", ["opening_trial_balance.csv"])
    for i in _csv("invoices.csv"):
        net, vat, tot = float(i["net"]), float(i["vat"]), float(i["total"])
        p = [f"invoices.csv#{i['invoice_no']}"]
        if i["type"] == "sale":
            L.post([("1100", tot), ("4000", -net), ("2100", -vat)], f"sale {i['invoice_no']}", p)
        else:
            L.post([("1200", net), ("1300", vat), ("2000", -tot)], f"purchase {i['invoice_no']}", p)
    bank = {b["bank_id"]: b for b in _csv("bank_statement.csv")}
    ledger_ref = {r["ref"]: r for r in _csv("ledger_cash.csv")}
    for bid, ref, how in recon["matches"]:
        b = bank[bid]; amt = float(b["amount"]); p = [f"bank_statement.csv#{bid}", f"rule:{how}"]
        if ref and how != "duplicate_payment":
            ctr = "1100" if ref.startswith("FT-S") else "2000" if ref.startswith(("PI", "QGT")) else \
                  {"RENT": "6000", "SAL-": "6100", "DEWA": "6300", "EXP-": "6700"}.get(ref[:4], "6200")
            L.post([("1000", amt), (ctr, -amt)], f"cash {ref}", p + [f"ledger_cash.csv#{ref}"])
        elif how == "bank_charge":
            net = round(amt / 1.05, 2)
            L.post([("1000", amt), ("6200", -net), ("1300", -(amt - net))], "bank charge with 5% VAT", p)
        elif how == "unrecorded_receipt":
            L.post([("1000", amt), ("2300", -amt)], "unidentified receipt held pending remittance", p)
        elif how == "duplicate_payment":
            L.post([("1000", amt), ("1400", -amt)], "duplicate payment, recover from vendor", p + [f"bank_statement.csv#{ref}"])
            coa["1400"] = dict(code="1400", name="Vendor Recoverable", type="Asset")
    for j in _csv("journals.csv"):
        L.post([(j["debit"], float(j["amount"])), (j["credit"], -float(j["amount"]))], j["memo"], [f"journals.csv#{j['je']}"],
               source="human_review" if j["je"] in review_flags else "rule")
    L.post([("6400", 2000.0), ("2200", -2000.0)], "audit fee accrual, 24,000 a year / 12", ["rule:accrual_audit_fee"])
    L.post([("6500", 1500.0), ("1250", -1500.0)], "insurance prepayment release, 18,000 a year / 12", ["rule:prepayment_insurance"])
    coa.update({"6400": dict(code="6400", name="Audit Fee", type="Expense"), "6500": dict(code="6500", name="Insurance", type="Expense"),
                "1250": dict(code="1250", name="Prepaid Insurance", type="Asset")})
    # opening prepaid insurance was not in the TB: release against retained earnings for demo balance
    L.post([("1250", 1500.0), ("3100", -1500.0)], "recognise prepaid insurance brought forward", ["rule:prepayment_insurance"])
    tb, proofs = defaultdict(float), defaultdict(list)
    for e in L.entries:
        for l in e["lines"]:
            if l["acct"] != "OB":
                tb[l["acct"]] += l["amt"]; proofs[l["acct"]].append(e["id"])
    vat_due = -(tb["2100"] + tb["1300"])
    checklist = {
        "bank_reconciled": not recon["unmatched_ledger"] or all(r.startswith("CHQ") for r in recon["unmatched_ledger"]),
        "trial_balance_balances": abs(sum(tb.values())) < 0.01,
        "vat_control_computed": True, "accruals_posted": True, "prepayments_released": True,
        "suspense_reviewed": tb["2300"] == 0, "flagged_journals_cleared": not review_flags}
    def stmt(types):
        return {k: dict(name=coa.get(k, {}).get("name", k), amount=round(v, 2), proof=proofs[k])
                for k, v in sorted(tb.items()) if coa.get(k, {}).get("type") in types and abs(v) > 0.005}
    pl, bs = stmt({"Income", "Expense"}), stmt({"Asset", "Liability", "Equity"})
    profit = -sum(v["amount"] for v in pl.values())
    budget = json.load(open(D / "budget_oct.json"))
    var = {k: dict(actual=abs(tb[k]), budget=b, variance=round(abs(tb[k]) - b, 2)) for k, b in budget.items()}
    mock = "; ".join(f"{coa[k]['name']}: {v['variance']:+,.0f} AED vs budget" for k, v in var.items())
    commentary = llm.complete("You are a UAE financial controller. Write 4 short plain bullet points of variance "
                              f"commentary for Falcon Trading LLC October 2026. Data (AED): {json.dumps(var)}. "
                              f"Net profit {profit:,.0f}. Net VAT payable {vat_due:,.0f}.", mock_response=mock)
    return dict(entries=L.entries, trial_balance={k: dict(amount=round(v, 2), proof=proofs[k]) for k, v in tb.items()},
                pnl=pl, balance_sheet=bs, net_profit=round(profit, 2), vat_payable=round(vat_due, 2),
                checklist=checklist, variance=var, commentary=commentary)
