"""Resolve a citation like 'invoices.csv#PI-0012' or 'contracts/palm_foods_supply.txt#L3' to the exact source text."""
import csv, json
from pathlib import Path
D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"
KEYS = {"invoices.csv": "invoice_no", "bank_statement.csv": "bank_id", "ledger_cash.csv": "ref", "journals.csv": "je",
        "vendor_master.csv": "vendor", "invoice_lines.csv": "invoice_no", "ar_aging.csv": "customer", "payment_history.csv": "customer"}

def resolve(ref):
    f, _, key = ref.partition("#")
    if f == "agg:invoices":  # e.g. agg:invoices#Jebel Ali Packaging LLC|total
        party, _, field = key.partition("|"); rows = [r for r in csv.DictReader(open(D / "invoices.csv", encoding="utf-8")) if r["party"] == party]
        return f"Sum of October invoice {field} for {party} over {len(rows)} invoices = {round(sum(float(r[field]) for r in rows), 2)}" if rows else None
    try:
        if f == "treasury" and key.startswith("L"):
            lv = [l for l in json.load(open(O / "treasury_13w.json"))["levers"] if l["id"] == key]
            return json.dumps(lv[0]) if lv else None
        if f in KEYS:
            rows = [r for r in csv.DictReader(open(D / f, encoding="utf-8")) if r.get(KEYS[f]) == key]
            return "; ".join(json.dumps(r) for r in rows) or None
        if f.startswith("contracts/") and key.startswith("L"):
            lines = (D / f).read_text(encoding="utf-8").splitlines(); n = int(key[1:])
            return lines[n - 1] if 0 < n <= len(lines) else None
        if f == "messages.jsonl":
            for l in open(D / f, encoding="utf-8"):
                m = json.loads(l)
                if m["id"] == key: return json.dumps(m, ensure_ascii=False)
            return None
        if f in ("pnl_oct", "pnl_sep", "tb_oct", "drivers_oct", "drivers_sep"):
            sep = json.load(open(D / "sept_2026.json"))
            if f == "pnl_sep": v = sep["pnl"].get(key)
            elif f == "drivers_sep": v = sep["drivers"].get(key)
            elif f == "drivers_oct": v = sep["drivers_oct"].get(key)
            else:
                c = json.load(open(O / "close_oct2026.json")); src = c["pnl"] if f == "pnl_oct" else c["trial_balance"]
                v = src.get(key, {}).get("amount")
            return None if v is None else f"{f} {key} = {v}"
        if not key and (D / f).is_file() and (D / f).stat().st_size < 3000:  # small whole files, e.g. inventory.csv
            return (D / f).read_text(encoding="utf-8")
        if f == "loan":  # loan#57 -> that page of the facility agreement (clause lines starting 22. shown first)
            import re
            t = (D / "loan" / "facility_agreement.txt").read_text(encoding="utf-8"); m = re.search(rf"\[Page {int(key)}\]\n(.*?)(?=\n\n\[Page |\Z)", t, re.S)
            if not m: return None
            ls = m.group(1).splitlines(); key_ls = [l for l in ls if re.match(r"(18\.4|22\.[1-5]|23\.3) [A-Z]", l)]
            return f"Facility agreement page {key}: " + " | ".join(key_ls or ls[:2])
        if f.startswith("treasury"):  # treasury#downside or treasury#downside:week6
            t = json.load(open(O / "treasury_13w.json")); k = key.split(":")[0]
            if k in t and isinstance(t[k], dict): return f"{k}: lowest cash AED {t[k]['lowest_cash']:,.2f} in week {t[k]['lowest_week']}; weekly closing {[round(x) for x in t[k]['closing']]}"
            if k == "levers": return json.dumps(t["levers"])
        if f == "close_oct2026.json" and key in ("net_profit", "vat_payable"): f = "close"
        if f == "close" and key in ("net_profit", "vat_payable"):
            return f"{key} = {json.load(open(O / 'close_oct2026.json'))[key]}"
    except (OSError, ValueError):
        return None
    return None

def line_numbered(path):
    return "\n".join(f"L{i}: {t}" for i, t in enumerate((D / path).read_text(encoding="utf-8").splitlines(), 1))
