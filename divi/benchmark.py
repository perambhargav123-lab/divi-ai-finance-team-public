"""Fraud and error benchmark: inject 20 varied synthetic anomalies plus 6 harmless decoys into a copy of the books,
run the same detectors, and score detection rate, precision and false positives."""
import csv, json, random, shutil
from pathlib import Path
from divi.agents import redteam, capture
from divi import judgment
D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"; B = O / "bench" / "data"
KNOWN = {"PI-0006-A", "PI-0006", "B108", "B136", "B140", "JE-1041", "PI-0012"}  # anomalies already planted in the real books

def _rw(name, fn):
    rows = list(csv.DictReader(open(B / name, encoding="utf-8"))); cols = list(rows[0]); rows = fn(rows) or rows
    w = csv.DictWriter(open(B / name, "w", newline="", encoding="utf-8"), fieldnames=cols); w.writeheader(); w.writerows(rows)

def inject(seed=20):
    R = random.Random(seed); shutil.rmtree(B.parent, ignore_errors=True); shutil.copytree(D, B); truth = []
    def inv(rows):
        pur = [r for r in rows if r["type"] == "purchase" and r["invoice_no"] != "PI-0006"]
        picks = R.sample(pur, 4)
        for k, r in enumerate(picks[:3]):
            rows.append({**r, "invoice_no": r["invoice_no"] + "-X", "flag": ""}); truth.append(dict(id=r["invoice_no"] + "-X", kind="duplicate vendor invoice"))
        r = picks[3]; n = float(r["net"]) + 1  # hard case: near-duplicate, amount changed by AED 1
        rows.append({**r, "invoice_no": r["invoice_no"] + "-X", "net": f"{n:.2f}", "vat": f"{n*.05:.2f}", "total": f"{n*1.05:.2f}", "flag": ""})
        truth.append(dict(id=r["invoice_no"] + "-X", kind="near-duplicate vendor invoice (AED 1 different)", hard=True))
        for r in R.sample([r for r in rows if r["type"] == "sale"], 2):
            r["vat"] = f"{float(r['net']) * 0.04:.2f}"; r["total"] = f"{float(r['net']) + float(r['vat']):.2f}"; truth.append(dict(id=r["invoice_no"], kind="wrong VAT rate (4%)"))
        r = R.choice([r for r in rows if r["type"] == "sale" and r["invoice_no"] not in {t["id"] for t in truth}])
        r["total"] = f"{float(r['total']) + 900:.2f}"; truth.append(dict(id=r["invoice_no"], kind="total does not add up"))
    _rw("invoices.csv", inv)
    def vm(rows):
        for n, c in (("Swift Star Trading", "2026-10-20"), ("Nova Gulf Supplies", "2026-10-25"), ("Prime Edge General Trading", "2026-10-12")):
            rows.append(dict(vendor=n, created=c, bank_iban_changed="no", trn="100" + str(R.randint(10**11, 10**12 - 1))))
        for v in R.sample([r for r in rows if r["vendor"] not in ("Quickline General Trading",)][:7], 2):
            v["bank_iban_changed"] = "yes"; truth.append(dict(id=v["vendor"], kind="vendor bank details changed"))
    _rw("vendor_master.csv", vm)
    def bank(rows):
        n = len(rows)
        for k, (v, a, d) in enumerate((("SWIFT STAR TRADING", 30000, "2026-10-26"), ("NOVA GULF SUPPLIES", 24500, "2026-10-28"), )):
            bid = f"BX{k+1}"; rows.append(dict(bank_id=bid, date=d, description=f"OUTWARD PAYMENT {v}", amount=-a)); truth.append(dict(id=bid, kind="large payment to new vendor"))
        for k, d in enumerate(("2026-10-29", "2026-10-30")):  # hard case: split payment under the 10,000 threshold
            rows.append(dict(bank_id=f"BS{k+1}", date=d, description="OUTWARD PAYMENT PRIME EDGE GENERAL TRADING", amount=-9800))
        truth.append(dict(id="BS1", kind="split payments under threshold to new vendor (2 x 9,800)", hard=True, pair_of="BS2"))
        outs = [r for r in rows if float(r["amount"]) < -5000 and "CHARGE" not in r["description"] and r["date"] < "2026-10-24" and not r["bank_id"].startswith("BX")]
        for k, r in enumerate(R.sample(outs, 3)):
            bid = f"BD{k+1}"; rows.append(dict(bank_id=bid, date=r["date"], description=r["description"], amount=r["amount"])); truth.append(dict(id=bid, kind="duplicate bank payment", pair_of=r["bank_id"]))
        # decoys: large but legitimate payments to long-standing payees
        rows.append(dict(bank_id="BOK1", date="2026-10-29", description="OUTWARD PAYMENT SAHARA FREIGHT SERVICES REF PI-0053", amount=-12345.67))
        rows.append(dict(bank_id="BOK2", date="2026-10-30", description="DIRECT DEBIT DEWA OCT", amount=-3180.4))
    _rw("bank_statement.csv", bank)
    def jr(rows):
        for k, (d, who) in enumerate((("2026-10-17", "trainee.s (junior)"), ("2026-10-18", "junior.m"), ("2026-10-31", "intern.k (junior)"))):
            rows.append(dict(je=f"JE-20{k+1}", date=d, weekday="", posted_by=who, debit="6700", credit="2200", amount=4200 + 1000 * k, memo="adj", flag=""))
            truth.append(dict(id=f"JE-20{k+1}", kind="weekend journal by junior"))
        rows.append(dict(je="JE-2OK1", date="2026-10-25", weekday="", posted_by="fc.ahmed", debit="6000", credit="2200", amount=5000, memo="rent accrual", flag=""))  # decoy: senior on weekend
        rows.append(dict(je="JE-2OK2", date="2026-10-27", weekday="", posted_by="acct.lina", debit="6700", credit="2200", amount=8000, memo="accrual", flag=""))
    _rw("journals.csv", jr)
    def lines(rows):
        for r in R.sample([r for r in rows if r["party"] != "Palm Foods Import"], 2):
            r["unit_price"] = round(float(r["unit_price"]) * 1.12, 2); r["qty"] = round(float(r["net"]) / r["unit_price"], 2)
            truth.append(dict(id=r["invoice_no"], kind="price above contract"))
    _rw("invoice_lines.csv", lines)
    return truth

def detect():
    found = {}
    old = redteam.D; redteam.D = B
    try:
        for f in redteam.scan(explain=False):
            for i in f["items"]: found.setdefault(i, set()).add(f["rule"])
    finally:
        redteam.D = old
    for r in csv.DictReader(open(B / "invoices.csv", encoding="utf-8")):
        for issue in [x for x in capture.validate({**r, "vendor": r["party"]}) if not x.startswith("missing")]: found.setdefault(r["invoice_no"], set()).add(issue)
    ct = json.load(open(O / "judgment.json"))["contract_terms"]
    oldj = judgment.D; judgment.D = B
    try:
        for f in judgment.contract_findings(dict(prices=ct["prices"], terms=[])): found.setdefault(f["invoice"], set()).add("price above contract")
    finally:
        judgment.D = oldj
    return found

def run():
    truth = inject(); found = detect(); ids = {t["id"] for t in truth}
    # a duplicate is caught when either copy is flagged
    def hit(t):
        if t["id"] in found: return True
        base = t["id"].removesuffix("-X")
        return (t["kind"].startswith("duplicate vendor") and base in found) or (t.get("pair_of") in found and t["kind"].startswith("split"))
    rows = [dict(**t, detected=hit(t), by=sorted(found.get(t["id"], found.get(t["id"].removesuffix("-X"), set())))) for t in truth]
    allowed = ids | KNOWN | {t["id"].removesuffix("-X") for t in truth} | {t.get("pair_of") for t in truth}
    fp = sorted(k for k in found if k not in allowed)
    fp_detail = {k: sorted(found[k]) for k in fp}
    tp = sum(r["detected"] for r in rows)
    flagged_inj = len([k for k in found if k in allowed and k not in KNOWN])
    res = dict(injected=len(truth), decoys=4, decoy_ids=["BOK1", "BOK2", "JE-2OK1", "JE-2OK2"], decoys_flagged=sorted(k for k in found if k in ("BOK1", "BOK2", "JE-2OK1", "JE-2OK2")), detected=tp, detection_rate=round(tp / len(truth), 3), false_positives=fp, false_positive_detail=fp_detail,
               precision=round(tp / (tp + len(fp)), 3) if tp + len(fp) else 0, rows=rows)
    json.dump(res, open(O / "benchmark.json", "w"), indent=1); return res
