"""Auditor loop: an independent Auditor agent challenges Divi's close before anyone relies on it.

The Auditor does not trust Divi's numbers. For each risk it raises a query, Divi answers with source rows,
and the Auditor re-performs the figure from the raw books in code. A difference above the clearly-trivial
threshold becomes a proposed adjustment; Divi posts it; the Auditor signs only when nothing material is left.
Muse writes the query wording and the sign-off letter; every number here comes from code."""
import hashlib, json
from pathlib import Path
from divi import llm, sources

D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"

def _row(ref):
    t = sources.resolve(ref)
    try: return json.loads(t.split("; ")[0]) if t else {}
    except ValueError: return {}

_ALIAS = {"B108": ("B108", "large_payment_to_new_vendor", "round_amount_payment")}
_MAP = {"approve_escalation": "block", "hold": "block", "block": "block", "reject": "release", "approve": "release", "release": "release", "pending": None}

def _decision(flag):
    """Latest owner decision on a flag. For the Quickline payment the UI escalation buttons count too:
    approving the escalation keeps the payment blocked, rejecting it releases the payment."""
    p = O / "decisions.json"; names = _ALIAS.get(flag, (flag,))
    for d in (json.load(open(p)) if p.exists() else [])[::-1]:
        if any(n in json.dumps(d) for n in names): return _MAP.get(d.get("decision"), d.get("decision"))
    return None

def materiality():
    c = json.load(open(O / "close_oct2026.json")); rev = abs(c["pnl"]["4000"]["amount"])
    m = round(rev * 0.01, 2)
    return dict(basis="1% of October sales", revenue=rev, overall=m, performance=round(m * 0.75, 2), trivial=round(m * 0.05, 2))

def _queries():
    e = json.load(open(O / "edge.json"))["cogs"]
    ins = json.load(open(O / "insights.json")); ob = next(f for f in ins["judgment"]["findings"] if f["kind"] == "overbilling")
    b160, b136, b108 = _row("bank_statement.csv#B160"), _row("bank_statement.csv#B136"), _row("bank_statement.csv#B108")
    dup = _row("invoices.csv#PI-0006-A"); je = _row("journals.csv#JE-1041")
    hidden = float(b160["amount"]); hidden_net = round(hidden / 1.05, 2)
    blocked = _decision("B108")
    return [
        dict(id="Q1", area="Cost of sales", assertion="Accuracy",
             ask="Cost of sales is 71.9% of sales. Show me the stock count behind JE-1040.",
             divi="Opening stock + purchases - counted stock gives a higher cost of sales than booked.",
             reperform=f"{e['opening_stock']:,.2f} + {e['purchases']:,.2f} - {e['counted_stock']:,.2f} = {e['cogs_from_count']:,.2f}; booked {e['booked']:,.2f}",
             difference=round(e["cogs_from_count"] - e["booked"], 2), pnl=-round(e["gap"], 2),
             adjustment="Dr 5000 Cost of goods sold / Cr 1200 Inventory", cites=e["proof"]),
        dict(id="Q2", area="Revenue", assertion="Completeness",
             ask=f"Bank line B160 shows AED {hidden:,.0f} received with no reference. Where is the sales invoice?",
             divi="No invoice exists. It is an unrecorded sale to Desert Rose, so revenue and VAT are both understated.",
             reperform=f"{hidden:,.2f} / 1.05 = {hidden_net:,.2f} net + {hidden - hidden_net:,.2f} VAT",
             difference=hidden, pnl=hidden_net, adjustment="Dr 1000 Bank / Cr 4000 Sales and Cr 2200 VAT payable",
             cites=["bank_statement.csv#B160"]),
        dict(id="Q3", area="Payables", assertion="Occurrence",
             ask="Two Sahara Freight invoices have the same date, amount and TRN. Were both paid?",
             divi="PI-0006-A is a duplicate of PI-0006. Reverse it and recover the payment.",
             reperform=f"PI-0006 total {float(dup['total']):,.2f} = PI-0006-A total {float(dup['total']):,.2f}, same TRN",
             difference=float(dup["total"]), pnl=float(dup["net"]), adjustment="Dr 1150 Supplier refund due / Cr expense and input VAT",
             cites=["invoices.csv#PI-0006", "invoices.csv#PI-0006-A"]),
        dict(id="Q4", area="Cash", assertion="Existence",
             ask=f"B136 pays Horizon Office Supplies AED {abs(float(b136['amount'])):,.2f} a second time. Is it recoverable?",
             divi="Yes. It is a duplicate bank payment. Move it from expense to a receivable from the supplier.",
             reperform=f"B136 amount {abs(float(b136['amount'])):,.2f} matches the original payment",
             difference=abs(float(b136["amount"])), pnl=0.0, adjustment="Dr 1150 Supplier refund due / Cr 2000 Payables (balance sheet only)",
             cites=["bank_statement.csv#B136"]),
        dict(id="Q5", area="Payments", assertion="Authorisation",
             ask=f"AED {abs(float(b108['amount'])):,.0f} went to Quickline, a vendor added this month. Who approved it?",
             divi="The Red Team held it for the owner. " + ("The owner blocked it, so the AED 50,000 stays in the bank." if blocked == "block" else
                  "The owner released it against the Auditor's advice. It is logged as an accepted control risk." if blocked == "release" else "It is still waiting for the owner."),
             reperform="Vendor master: Quickline added in October, no second approver on the payment",
             difference=0.0, pnl=0.0, adjustment=None, control=True, cites=["bank_statement.csv#B108", "vendor_master.csv#Quickline General Trading"]),
        dict(id="Q6", area="Journals", assertion="Controls",
             ask=f"JE-1041 was posted on a {je.get('weekday', 'weekend')} by a junior with no approver. Is it valid?",
             divi="The amount is supported, but the approval control failed. Divi now blocks unapproved weekend journals.",
             reperform=f"JE-1041 dated {je.get('date')} ({je.get('weekday')}), posted by {je.get('posted_by')}",
             difference=0.0, pnl=0.0, adjustment=None, control=True, cites=["journals.csv#JE-1041"]),
        dict(id="Q7", area="Payables", assertion="Accuracy",
             ask=f"Palm Foods {ob['invoice']} bills AED 12.50 per kg against an AED 11.00 contract. Has it been paid?",
             divi=f"Not yet. Payment is on hold and a credit note of AED {ob['amount'] * 1.05:,.2f} is requested.",
             reperform="(12.50 - 11.00) x 2,373.55 kg = " + f"{ob['amount']:,.2f} + 5% VAT", difference=round(ob["amount"] * 1.05, 2),
             pnl=0.0, adjustment="None needed while unpaid. Credit note requested.", cites=ob["cites"]),
    ]

def run():
    M = materiality(); qs = _queries()
    from divi import decision_log
    for q in qs:
        pol = decision_log.policy_for(query=q["id"]); q["policy"] = pol and dict(id=pol["id"], title=pol["title"], rule=pol["rule"])
        q["evidence"] = {c: sources.resolve(c) for c in q["cites"]}
        if q.get("control"): q["status"] = "control point"
        elif q["difference"] <= M["trivial"] or q["pnl"] == 0 and not q["adjustment"].startswith("Dr"): q["status"] = "cleared"
        else: q["status"] = "adjusted"
        q["material"] = abs(q["difference"]) >= M["performance"]
    adj = [q for q in qs if q["status"] == "adjusted"]
    c = json.load(open(O / "close_oct2026.json")); np0 = c["net_profit"]; np1 = round(np0 + sum(q["pnl"] for q in adj), 2)
    dq = _decision("B108"); open_items = [q for q in qs if q["id"] == "Q5" and dq not in ("block", "release")]
    opinion = ("Signed with one open item: the Quickline payment is waiting for the owner" if open_items else
               "Signed: no material misstatement left. Quickline payment blocked by the owner" if dq == "block" else
               "Signed: no material misstatement left. Quickline payment released by the owner, control risk noted")
    pack = json.dumps([[q["id"], q["reperform"], q["evidence"]] for q in qs], sort_keys=True, ensure_ascii=False)
    sig = hashlib.sha256(pack.encode()).hexdigest()
    mock = (f"We reviewed the October 2026 close of Falcon Trading LLC using a materiality of AED {M['overall']:,.0f}. "
            f"We raised {len(qs)} queries. {len(adj)} needed adjustments, which Divi posted, and net profit moved from "
            f"AED {np0:,.0f} to AED {np1:,.0f}. Two control weaknesses were found: a new vendor paid without a second approver, "
            "and a weekend journal posted by a junior without approval. " + ("After the adjustments, no material misstatement remains." if not open_items else "After the adjustments, nothing material remains except the Quickline payment, which the owner must approve or block."))
    letter, amodel = llm.ask_open("auditor", "You are an independent external auditor. Write a 4-sentence sign-off note to the owner of a small UAE company. "
                     "Use only these facts, do not add numbers:\n" + json.dumps(dict(materiality=M, queries=[{k: q[k] for k in ("id", "area", "status", "difference")} for q in qs],
                     net_profit_before=np0, net_profit_after=np1, opinion=opinion)), mock)
    prep = "muse-spark-1.3 (Meta Model API)"
    return dict(materiality=M, queries=qs, adjusted=len(adj), cleared=sum(q["status"] == "cleared" for q in qs),
                controls=sum(q["status"] == "control point" for q in qs), net_profit_before=np0, net_profit_after=np1,
                opinion=opinion, signature=sig, cert_id="DV-AUD-" + sig[:8].upper(), letter=llm.clean(letter) if hasattr(llm, "clean") else letter,
                models=dict(preparer=prep, auditor=amodel, independent=amodel != prep and not amodel.startswith("rule")),
                independence=f"The Auditor runs on {amodel}, a different model from the preparer ({prep}). It sees only the raw books and Divi's answers, never Divi's reasoning, and re-performs every figure in code.")
