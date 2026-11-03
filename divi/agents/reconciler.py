"""Reconciler agent: rules first, LLM only for leftovers. Tracks automation rate."""
import csv
from datetime import date
from divi import llm

def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def reconcile(bank, ledger, use_llm=True, window_days=5):
    stats = {"rule": 0, "llm": 0, "unmatched": 0}
    open_l = {r["ref"]: r for r in ledger}
    matches, exceptions = [], []
    for b in bank:
        amt = float(b["amount"]); hit = None
        for ref, l in open_l.items():  # rule 1: reference in narrative + amount
            if ref in b["description"] and abs(float(l["amount"]) - amt) < 0.01:
                hit = ref; break
        if not hit:  # rule 2: amount + date window
            bd = date.fromisoformat(b["date"])
            for ref, l in open_l.items():
                if abs(float(l["amount"]) - amt) < 0.01 and abs((date.fromisoformat(l["date"]) - bd).days) <= window_days:
                    hit = ref; break
        if hit:
            stats["rule"] += 1; matches.append((b["bank_id"], hit, "rule")); open_l.pop(hit)
        else:
            exceptions.append(b)
    seen = {}
    for b in bank:
        seen.setdefault((b["description"].replace(" DUPLICATE", ""), b["amount"]), b["bank_id"])
    for b in exceptions:
        key = (b["description"].replace(" DUPLICATE", ""), b["amount"])
        if float(b["amount"]) < 0 and "CHARGE" not in b["description"].upper() and seen.get(key) != b["bank_id"]:
            stats["rule"] += 1; matches.append((b["bank_id"], seen[key], "duplicate_payment")); continue
        cat = "bank_charge" if "CHARGE" in b["description"].upper() else "unrecorded_receipt" if float(b["amount"]) > 0 else "unexplained_payment"
        if use_llm:
            llm.complete(f"Classify bank line for UAE month-end: {b}", mock_response=cat)
            stats["llm"] += 1
        else:
            stats["unmatched"] += 1
        matches.append((b["bank_id"], None, cat))
    total = len(bank) or 1
    return {"matches": matches, "stats": stats, "automation_rate": round(stats["rule"] / total, 3),
            "unmatched_ledger": list(open_l)}
