"""Basic cash leak finder in QAR (rules, no AI). Flags on bank CSV + ledger + usage:
duplicate payments, unused or price-raised subscriptions, vendor price creep, unmatched charges.
Every flag cites the transaction ids it is based on. Sample data only: data/qatar/."""
import csv, json, sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from divi import fingerprint
D = Path(__file__).resolve().parent.parent / "data" / "qatar"
rd = lambda p: list(csv.DictReader(open(p)))

def find(bank=D / "sample_bank_qar.csv", ledger=D / "sample_ledger_qar.csv", usage=D / "sample_usage.csv", as_of="2026-10-31", creep_pct=8.0, idle_days=60):
    tx = [t for t in rd(bank) if float(t["amount_qar"]) < 0]
    for t in tx: t["amt"] = -float(t["amount_qar"])
    led = {r["reference"] for r in rd(ledger)}; use = {u["vendor"]: u for u in rd(usage)}
    leaks, seen = [], {}
    for t in tx:  # duplicates: same vendor, amount and reference (or same vendor+amount within 3 days)
        k = (t["vendor"], t["amt"], t["reference"])
        if t["reference"] and k in seen:
            leaks.append(dict(type="duplicate payment", vendor=t["vendor"], amount_qar=t["amt"], detail=f"paid twice for {t['reference']}", sources=[seen[k]["txn_id"], t["txn_id"]]))
        seen[k] = t
    byv = defaultdict(list)
    for t in tx: byv[t["vendor"]].append(t)
    for v, ts in byv.items():
        ts.sort(key=lambda t: t["date"]); dedup = list({t["reference"] or t["txn_id"]: t for t in ts}.values())
        subs = all(t["reference"].startswith("SUB-") for t in dedup) and len(dedup) >= 3
        u = use.get(v)
        if subs and u:
            idle = (date.fromisoformat(as_of) - date.fromisoformat(u["last_used"])).days
            if idle >= idle_days:
                leaks.append(dict(type="unused subscription", vendor=v, amount_qar=dedup[-1]["amt"], detail=f"no use for {idle} days, still billed monthly", sources=[t["txn_id"] for t in dedup if t["date"] > u["last_used"]]))
            elif int(u["seats_active"]) < int(u["seats_paid"]):
                per = dedup[-1]["amt"] / int(u["seats_paid"]); idle_s = int(u["seats_paid"]) - int(u["seats_active"])
                leaks.append(dict(type="idle seats", vendor=v, amount_qar=round(per * idle_s, 2), detail=f"{idle_s} of {u['seats_paid']} seats unused", sources=[dedup[-1]["txn_id"]]))
        if len(dedup) >= 2:
            first, last = dedup[0]["amt"], dedup[-1]["amt"]; pct = (last - first) / first * 100
            if subs and last > first:
                leaks.append(dict(type="subscription price increase", vendor=v, amount_qar=round(last - first, 2), detail=f"QAR {first:,.2f} to {last:,.2f} a month (+{pct:.1f}%)", sources=[dedup[0]["txn_id"], dedup[-1]["txn_id"]]))
            elif not subs and len(dedup) >= 3 and pct >= creep_pct and all(b["amt"] >= a["amt"] for a, b in zip(dedup, dedup[1:])):
                leaks.append(dict(type="vendor price creep", vendor=v, amount_qar=round(last - first, 2), detail=f"QAR {first:,.2f} to {last:,.2f} over {len(dedup)} bills (+{pct:.1f}%)", sources=[t["txn_id"] for t in dedup]))
    for t in tx:
        if not t["reference"] or t["reference"] not in led:
            leaks.append(dict(type="unmatched charge", vendor=t["vendor"], amount_qar=t["amt"], detail="no invoice or ledger entry", sources=[t["txn_id"]]))
    total = round(sum(l["amount_qar"] for l in leaks), 2)
    return {"currency": "QAR", "as_of": as_of, "data": "sample data only", "leaks": leaks, "total_qar": total,
            "by_type": {k: round(sum(l["amount_qar"] for l in leaks if l["type"] == k), 2) for k in dict.fromkeys(l["type"] for l in leaks)}}

def report_text(r, v=None):
    lines = [f"Divi cash leak report (SAMPLE DATA), as of {r['as_of']}", f"Total flagged: QAR {r['total_qar']:,.2f} across {len(r['leaks'])} items", ""]
    lines += [f"- {l['type']}: {l['vendor']}, QAR {l['amount_qar']:,.2f}. {l['detail']}. Source: {', '.join(l['sources'])}" for l in r["leaks"]]
    if v: lines += ["", ("Evidence fingerprint: VERIFIED. " if v["verified"] else "Evidence fingerprint: NOT VERIFIED. ") + v["reason"] + f" (key: {v['key_mode']})"]
    return "\n".join(lines)

if __name__ == "__main__":  # python -m divi.cashleak [out.json]
    r = find(); signed = fingerprint.sign(fingerprint.pack_from_leaks(r))
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out/cash_leak_pack.json"); out.parent.mkdir(exist_ok=True)
    json.dump({**signed, "report": r}, open(out, "w"), indent=1)
    print(report_text(r, fingerprint.verify(signed))); print(f"\nSigned pack: {out}  sha256 {signed['fingerprint']['sha256'][:16]}...")
