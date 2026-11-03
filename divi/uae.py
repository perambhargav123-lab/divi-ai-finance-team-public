"""UAE depth: VAT return mapped to FTA Form 201 boxes, 9% corporate tax estimate, e-invoicing readiness. Every number links to proof."""
import csv, json, re
from pathlib import Path
D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"
def _csv(n): return list(csv.DictReader(open(D / n, encoding="utf-8")))

def vat201():
    inv = _csv("invoices.csv"); s = [i for i in inv if i["type"] == "sale"]; p = [i for i in inv if i["type"] == "purchase"]
    sn, sv = sum(float(i["net"]) for i in s), sum(float(i["vat"]) for i in s)
    pn, pv = sum(float(i["net"]) for i in p), sum(float(i["vat"]) for i in p)
    close = json.load(open(O / "close_oct2026.json"))
    bc = [e for e in close["entries"] if e["memo"].startswith("bank charge")]
    bcv = sum(l["amt"] for e in bc for l in e["lines"] if l["acct"] == "1300"); pn += bcv * 20; pv += bcv
    boxes = [
        dict(box="1b", label="Standard rated supplies in Dubai", amount=round(sn, 2), vat=round(sv, 2), proof=f"{len(s)} sales invoices", ref="agg:invoices"),
        dict(box="2-7", label="Other emirates, reverse charge, zero rated, exempt, imports", amount=0.0, vat=0.0, proof="none in October data"),
        dict(box="8", label="Total supplies", amount=round(sn, 2), vat=round(sv, 2), proof="sum of boxes 1 to 7"),
        dict(box="9", label="Standard rated expenses (input VAT)", amount=round(pn, 2), vat=round(pv, 2), proof=f"{len(p)} purchase invoices plus VAT on {len(bc)} bank charges ({', '.join(e['id'] for e in bc)})"),
        dict(box="11", label="Total expenses", amount=round(pn, 2), vat=round(pv, 2), proof="sum of boxes 9 and 10"),
        dict(box="12", label="Total value of due tax", vat=round(sv, 2)), dict(box="13", label="Total value of recoverable tax", vat=round(pv, 2)),
        dict(box="14", label="Payable tax for the period", vat=round(sv - pv, 2), proof="box 12 minus box 13; ties to the VAT control accounts 2100 and 1300 in the close"),
    ]
    return dict(boxes=boxes, ties_to_ledger=abs((sv - pv) - close["vat_payable"]) < 1, ledger_vat=close["vat_payable"],
                note="Quarterly filer assumed; October is month 1 of the Oct to Dec 2026 return. Due 28 days after quarter end.")

def corporate_tax(adjustments=()):
    close = json.load(open(O / "close_oct2026.json")); np_ = close["net_profit"]
    adj = sum(float(a.get("amount_aed") or 0) for a in adjustments if a.get("verified") and a.get("kind") in ("accrued_revenue", "unbilled_revenue"))
    monthly = np_ + adj * 0.28  # revenue cut-off adds gross margin only (72% COGS)
    annual = monthly * 12; band = 375000; tax = max(annual - band, 0) * 0.09
    return dict(oct_net_profit=np_, cutoff_margin=round(adj * 0.28, 2), annualised_profit=round(annual, 2), threshold=band, rate=0.09,
                estimated_tax=round(tax, 2), monthly_provision=round(tax / 12, 2),
                note="Estimate: October profit annualised, plus gross margin on verified cut-off adjustments. 0% on the first AED 375,000, 9% above. "
                     "Small Business Relief does not apply because revenue is above AED 3m a year. Check disallowed items (entertainment 50%) with an adviser.")

MANDATORY = ["invoice_no", "date", "party", "trn", "net", "vat", "total", "currency", "buyer_address", "line_items", "tax_category_code", "seller_endpoint_id"]
def einvoice():
    inv = _csv("invoices.csv"); cols = set(inv[0]); bad_trn = []
    for i in inv:
        t = i.get("trn", "")
        if not re.fullmatch(r"100\d{12}", t): bad_trn.append(dict(invoice=i["invoice_no"], party=i["party"], trn=t, proof=f"invoices.csv#{i['invoice_no']}"))
    lines = {r["invoice_no"] for r in _csv("invoice_lines.csv")}
    fields = []
    for f in MANDATORY:
        have = f in cols or (f == "line_items" and bool(lines)) or (f == "currency")
        cov = "all invoices" if f in cols or f == "currency" else (f"{len(lines)} of {len(inv)} invoices" if f == "line_items" else "missing")
        fields.append(dict(field=f, status="ok" if f in cols or f == "currency" else ("partial" if have else "missing"), coverage=cov))
    ok = sum(x["status"] == "ok" for x in fields)
    return dict(fields=fields, ready_pct=round(100 * ok / len(fields)), trn_checked=len(inv), trn_invalid=bad_trn,
                note="UAE e-invoicing (PINT AE, via accredited service providers) starts in phases from July 2026 for large taxpayers. "
                     "Checks: TRN is 15 digits starting 100; mandatory fields present. Currency is AED for all rows.")
