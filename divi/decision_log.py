"""Decision log: every exception the agents raised, the close policy it falls under, the evidence, what the owner decided
(who, when, why) and the precedent Divi carries into next month. One place an auditor or a new accountant can read."""
import json
from pathlib import Path
from divi import learning

R = Path(__file__).resolve().parents[1]; D, O = R / "data", R / "out"
_STATE = {"block": "blocked", "approve_escalation": "blocked", "release": "released", "reject": "released", "approve": "released",
          "send_query": "query approved", "dismiss": "dismissed"}

def policy():
    return json.load(open(D / "close_policy.json", encoding="utf-8"))

def policy_for(flag=None, query=None):
    for p in policy()["policies"]:
        if (flag and flag in p["applies_to"]) or (query and query in p["auditor"]): return p
    return None

def _decisions():
    p = O / "decisions.json"; latest = {}
    for d in (json.load(open(p)) if p.exists() else []): latest[d["flag"]] = d
    return latest

def run():
    rt = json.load(open(O / "redteam_oct2026.json")); dec = _decisions()
    items = [dict(flag=x["rule"], items=x["items"], evidence=x.get("proof", [])) for x in rt]
    items = [i for i in items if i["flag"] != "round_amount_payment"]  # same B108 payment as the new-vendor flag
    ins = json.load(open(O / "insights.json")); ob = next(f for f in ins["judgment"]["findings"] if f["kind"] == "overbilling")
    items.append(dict(flag="overbilling", items=[ob["invoice"]], evidence=ob["cites"]))
    items.append(dict(flag="hidden_sale", items=["B160"], evidence=["bank_statement.csv#B160"]))
    rows, seen = [], set()
    for it in items:
        if it["flag"] in seen: continue
        seen.add(it["flag"]); pol = policy_for(it["flag"]); d = dec.get(it["flag"])
        st = _STATE.get(d["decision"], d["decision"]) if d and d.get("decision") != "pending" else None
        auto = it["flag"] in ("duplicate_vendor_invoice", "duplicate_bank_payment", "overbilling")
        book = learning.BOOK.get("S3" if it["flag"] == "overbilling" else it["flag"])
        prec = (book[0] if st in ("blocked", "query approved") or auto else book[1] or book[0]) if book else \
               ("Unexplained receipts are queried automatically next month." if it["flag"] == "hidden_sale" else "")
        rows.append(dict(flag=it["flag"], label=it["flag"].replace("_", " "), items=it["items"], evidence=it["evidence"] or [f"bank_statement.csv#{it['items'][0]}"],
                         policy=pol and dict(id=pol["id"], title=pol["title"], rule=pol["rule"]),
                         decided_by="Divi, by policy" if auto else ("Owner" if st else None),
                         decision=("held, credit note requested" if it["flag"] == "overbilling" else "held and recovered") if auto else (st or "waiting for the owner"),
                         when=d.get("time") if d and st else None, why=(d.get("note") or None) if d else None,
                         next_month=prec if (st or auto) else "Decide once and Divi applies it next month."))
    done = sum(1 for r in rows if r["decided_by"])
    return dict(rows=rows, decided=done, waiting=len(rows) - done, policy_version=policy()["version"],
                note="Each decision becomes precedent: next month the same case is handled the same way, and the owner only sees new ones.")
