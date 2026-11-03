"""Bring your own books: map any bank CSV with Muse, then run close checks and a 13-week forecast."""
import csv, io, json, re
from collections import defaultdict
from datetime import date, datetime, timedelta
from divi import llm

def _guess(headers):
    h = {x.lower(): x for x in headers}; pick = lambda *ks: next((h[k] for k in h for w in ks if w in k), None)
    return dict(date=pick("date"), description=pick("desc", "narr", "detail", "particular"), amount=pick("amount"),
                debit=pick("debit", "withdraw", "out"), credit=pick("credit", "deposit", "in"), balance=pick("balance"), date_format="auto")

def map_columns(headers, sample):
    txt = llm.complete("Map this bank statement CSV to a standard schema. Return only JSON {date, description, amount, debit, credit, balance, "
                       "date_format} where each value is the exact source column name or null; use amount if one signed column, else debit and "
                       "credit; date_format is a Python strptime format. Headers: " + json.dumps(headers) + " Sample rows: " + json.dumps(sample),
                       mock_response=json.dumps(_guess(headers)))
    try: m = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    except ValueError: m = _guess(headers)
    return {k: (v if v in headers or k == "date_format" else None) for k, v in m.items()}

def _num(x):
    x = str(x or "").replace(",", "").replace("AED", "").strip()
    return float(x) if re.fullmatch(r"-?\d+(\.\d+)?", x) else 0.0

def _date(s, fmt):
    for f in ([fmt] if fmt and fmt != "auto" else []) + ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%m/%d/%Y"]:
        try: return datetime.strptime(s.strip(), f).date()
        except (ValueError, TypeError): pass
    return None

def run(text, opening_cash=None):
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows: return {"error": "The file has no rows."}
    m = map_columns(list(rows[0]), rows[:3]); tx = []
    for r in rows:
        d = _date(r.get(m["date"] or "", ""), m.get("date_format"))
        a = _num(r[m["amount"]]) if m.get("amount") else _num(r.get(m.get("credit") or "", 0)) - _num(r.get(m.get("debit") or "", 0))
        if d: tx.append(dict(date=d, desc=r.get(m["description"] or "", ""), amount=a, balance=_num(r.get(m.get("balance") or "", ""))))
    if not tx: return {"error": "Could not read dates from the file.", "mapping": m}
    tx.sort(key=lambda x: x["date"]); seen, findings = defaultdict(list), []
    for t in tx:
        seen[(t["desc"].upper().replace(" DUPLICATE", ""), t["amount"])].append(t["date"])
        if t["amount"] <= -10000 and t["amount"] % 1000 == 0: findings.append(f"Round payment AED {-t['amount']:,.0f} on {t['date']}: {t['desc']}")
    for (dsc, a), ds in seen.items():
        if len(ds) > 1 and a < 0 and "CHARGE" not in dsc: findings.append(f"Possible duplicate payment AED {-a:,.2f} x{len(ds)}: {dsc}")
    charges = sum(-t["amount"] for t in tx if re.search(r"charge|fee|commission", t["desc"], re.I) and t["amount"] < 0)
    days = max((tx[-1]["date"] - tx[0]["date"]).days, 1); inflow = sum(t["amount"] for t in tx if t["amount"] > 0); outflow = -sum(t["amount"] for t in tx if t["amount"] < 0)
    start = opening_cash if opening_cash is not None else (tx[-1]["balance"] or sum(t["amount"] for t in tx))
    wk = (inflow - outflow) / days * 7; fc = [round(start + wk * (i + 1), 2) for i in range(13)]
    checks = dict(transactions=len(tx), period=f"{tx[0]['date']} to {tx[-1]['date']}", total_in=round(inflow, 2), total_out=round(outflow, 2),
                  bank_charges=round(charges, 2), vat_on_charges_recoverable=round(charges / 1.05 * 0.05, 2), weekly_net=round(wk, 2), starting_cash=round(start, 2))
    return dict(mapping=m, checks=checks, findings=findings, forecast=fc)
