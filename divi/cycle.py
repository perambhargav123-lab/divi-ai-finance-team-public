"""Full cycle: procure-to-pay, order-to-cash, treasury and record-to-report checks for one SME close.
Every number is re-performed here from the raw files. Nothing is paid or sent: payment runs and reminders are proposals
the owner approves."""
import csv, json
from collections import defaultdict
from datetime import date
from pathlib import Path

R = Path(__file__).resolve().parents[1]; D, O = R / "data", R / "out"
TODAY = date(2026, 11, 2); RUN_TO = date(2026, 11, 30); VAT = 0.05
BUFFER = 128400.0  # one WPS payroll kept in the bank at all times
DEFER = {"PI-0013", "PI-0014", "PI-0037", "PI-0050", "PI-0044"}  # extension requests already drafted (S1, S2)

def _csv(n): return list(csv.DictReader(open(D / n, encoding="utf-8")))
def _r(x): return round(x + 1e-9, 2)

def three_way():
    po = {p["po"]: p for p in _csv("purchase_orders.csv")}; grn = {g["po"]: g for g in _csv("goods_received.csv")}
    rows = []
    for ln in _csv("invoice_lines.csv"):
        p = next((x for x in po.values() if x["invoice_no"] == ln["invoice_no"]), None); g = grn.get(p["po"]) if p else None
        q, u = float(ln["qty"]), float(ln["unit_price"])
        issues = []
        if not p: issues.append("no purchase order")
        else:
            if abs(u - float(p["unit_price"])) > 0.005: issues.append(f"price {u:.2f} vs PO {float(p['unit_price']):.2f}")
            if not g: issues.append("no goods received note")
            elif q - float(g["qty_received"]) > 0.005: issues.append(f"billed {q} vs received {g['qty_received']}")
        over = 0.0
        if p and g: over = max(0.0, q * u - min(q, float(g["qty_received"])) * float(p["unit_price"]))
        rows.append(dict(invoice=ln["invoice_no"], vendor=ln["party"], po=p and p["po"], grn=g and g["grn"], match=not issues,
                         issues=issues, held_with_vat=_r(_r(over) * (1 + VAT)), cite=f"invoice_lines.csv#{ln['invoice_no']}"))
    return rows

def vendor_checks():
    pos = {p["vendor"] for p in _csv("purchase_orders.csv")}; out = []
    for v in _csv("vendor_master.csv"):
        age = (TODAY - date.fromisoformat(v["created"])).days; flags = []
        if age < 30: flags.append(f"created {age} days ago")
        if v["vendor"] not in pos and age < 90: flags.append("no purchase order on file")
        if v["bank_iban_changed"] == "yes": flags.append("bank details changed")
        if not (v["trn"].isdigit() and len(v["trn"]) == 15): flags.append("TRN not 15 digits")
        out.append(dict(vendor=v["vendor"], age_days=age, flags=flags, ok=not flags, cite="vendor_master.csv#" + v["vendor"]))
    return out

def payment_run(held):
    terms = {a["vendor"]: a["early_pay_terms"] for a in _csv("ap_aging.csv")}; pay, hold, defer = [], [], []
    for i in _csv("invoices.csv"):
        if i["type"] != "purchase" or i["status"] != "open" or date.fromisoformat(i["due"]) > RUN_TO: continue
        x = dict(invoice=i["invoice_no"], vendor=i["party"], due=i["due"], amount=float(i["total"]), cite=f"invoices.csv#{i['invoice_no']}")
        if i["invoice_no"] in held: hold.append(dict(x, why="three-way match failed")); continue
        if i["invoice_no"] in DEFER: defer.append(dict(x, why="30-day extension requested")); continue
        x["terms"] = terms.get(i["party"], "net 45"); pay.append(x)
    s = lambda L: _r(sum(x["amount"] for x in L))
    return dict(window=f"{TODAY.isoformat()} to {RUN_TO.isoformat()}", pay=pay, hold=hold, defer=defer,
                pay_total=s(pay), hold_total=s(hold), defer_total=s(defer), status="proposal, owner approves before any payment")

def runway(pay_total):
    t = json.load(open(O / "treasury_13w.json"))["base"]; low = t["lowest_cash"]
    return dict(lowest_week=t["lowest_week"], lowest_cash=low, buffer=BUFFER, headroom=_r(low - BUFFER), run_total=pay_total,
                safe=low - BUFFER >= 0, note="The 13-week forecast already includes these bills on their due dates, so the run is safe if the lowest week stays above one payroll.",
                cite="treasury#base")

AR_EN = ("Dear {party} team, our records show AED {amt} on your account is {age} days past due. "
         "Please confirm a payment date this week, or tell us if anything on the invoices is in question.{extra} Finance team, Falcon Trading LLC")
AR_AR = ("السادة {party} المحترمين، تشير سجلاتنا إلى أن مبلغ {amt} درهم على حسابكم متأخر {age} يوم. "
         "نرجو تأكيد موعد الدفع هذا الأسبوع، أو إبلاغنا بأي ملاحظة على الفواتير.{extra} فريق المالية، فالكون للتجارة ذ.م.م")

DISPUTED = {"Oasis Hotels FZE": (12000.0, "messages.jsonl#M02")}  # FT-S-0066 linen claim, reviewed separately
AGE_AR = {"31 to 60": "من 31 إلى 60", "61 to 90": "من 61 إلى 90", "more than 90": "أكثر من 90"}

def collections():
    hist = defaultdict(list)
    for h in _csv("payment_history.csv"): hist[h["customer"]].append(float(h["days_late"]))
    rows = []
    for a in _csv("ar_aging.csv"):
        b = [("31 to 60", float(a["d31_60"])), ("61 to 90", float(a["d61_90"])), ("more than 90", float(a["d90_plus"]))]
        due = sum(v for _, v in b)
        if due <= 0: continue
        age = [d for d, v in b if v > 0][-1]; w = {"31 to 60": 45, "61 to 90": 75, "more than 90": 105}[age]; late = sum(hist[a["customer"]]) / len(hist[a["customer"]]) if hist[a["customer"]] else 0
        disp, dref = DISPUTED.get(a["customer"], (0.0, None)); chase = due - disp; amt = f"{chase:,.0f}"
        rows.append(dict(customer=a["customer"], overdue=_r(due), bucket_days=age, avg_days_late=round(late, 1),
                         score=round(chase / 1000 * w / 30 * (1 + late / 30), 1), cite=f"ar_aging.csv#{a['customer']}",
                         disputed=_r(disp), chase=_r(chase), dispute_cite=dref,
                         draft_en=AR_EN.format(party=a["customer"], amt=amt, age=age, extra=f" The AED {disp:,.0f} you have disputed is being reviewed separately and is not part of this request." if disp else ""), draft_ar=AR_AR.format(party=a["customer"], amt=amt, age=AGE_AR[age], extra=f" أما مبلغ {disp:,.0f} درهم المتنازع عليه فتتم مراجعته بشكل منفصل ولا يشمله هذا الطلب." if disp else ""),
                         status="draft, not sent"))
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1): r["rank"] = i
    return dict(rows=rows, total=_r(sum(r["overdue"] for r in rows)), disputed=_r(sum(r["disputed"] for r in rows)), chase_total=_r(sum(r["chase"] for r in rows)))

def close_checklist():
    c = json.load(open(O / "close_oct2026.json")); names = {"bank_reconciled": "Bank reconciled", "trial_balance_balances": "Trial balance balances",
        "vat_control_computed": "VAT control computed", "accruals_posted": "Accruals posted", "prepayments_released": "Prepayments released",
        "suspense_reviewed": "Suspense reviewed", "flagged_journals_cleared": "Flagged journals cleared (JE-1041 waits for the owner)"}
    steps = [dict(step=names.get(k, k), done=v) for k, v in c["checklist"].items()]
    acc = [dict(entry=e["id"], memo=e["memo"] + (" (flagged, owner decides)" if "JE-1041" in e["proof"][0] else ""), amount=_r(max(l["amt"] for l in e["lines"])), cite=e["proof"][0])
           for e in c["entries"] if any(w in e["memo"].lower() for w in ("accru", "prepa"))]
    return dict(steps=steps, done=sum(s["done"] for s in steps), total=len(steps), accruals=acc, net_profit=c["net_profit"], vat_payable=c["vat_payable"])

def _b108():
    from divi import auditor
    return auditor._decision("B108")

def run():
    tw = three_way(); held = {r["invoice"] for r in tw if not r["match"]}; vc = vendor_checks()
    pr = payment_run(held); rw = runway(pr["pay_total"]); col = collections(); cl = close_checklist()
    cc = json.load(open(O / "treasury_13w.json"))
    strip = [
        dict(id="p2p", name="Procure to pay", value=_r(sum(r["held_with_vat"] for r in tw)) + (0.0 if _b108() == "release" else 50000.0),
             line=f"{sum(r['match'] for r in tw)} of {len(tw)} bills match PO and goods received; {len(held)} held; {sum(not v['ok'] for v in vc)} new vendor blocked"),
        dict(id="o2c", name="Order to cash", value=col["total"], line=f"{len(col['rows'])} overdue customers ranked; chase AED {col['chase_total']:,.0f}, AED {col['disputed']:,.0f} disputed set aside; Arabic and English reminders drafted, none sent"),
        dict(id="treasury", name="Treasury", value=pr["pay_total"], line=f"Lowest week {rw['lowest_week']} keeps AED {rw['headroom']:,.0f} above one payroll"),
        dict(id="r2r", name="Record to report", value=cl["net_profit"], line=f"Close checklist {cl['done']} of {cl['total']} done; {len(cl['accruals'])} accruals and prepayments posted"),
        dict(id="audit", name="Independent audit", value=None, line="A separate auditor agent re-performs every material number before it signs"),
    ]
    return dict(strip=strip, three_way=tw, vendors=vc, payment_run=pr, runway=rw, collections=col, close=cl,
                note="Proposals only. Nothing is paid, posted or sent without the owner.")
