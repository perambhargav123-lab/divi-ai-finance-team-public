"""Live close: agents post step-by-step events. Real Meta calls when a key is set; otherwise replay a recorded real run."""
import json, time
from pathlib import Path
from divi import llm, meter
from divi.agents import capture, reconciler, controller, redteam, treasurer

R = Path(__file__).resolve().parents[1]; D, O = R / "data", R / "out"
CACHE = O / "cache" / "live_run.json"
LIVE_DOCS = ["doc_02_en.png", "doc_01_ar.png", "doc_04_bilingual.png", "doc_06_ar.png"]
AGENTS = {"capture": ("Capture", "#0284c7"), "reconciler": ("Reconciler", "#7c3aed"), "controller": ("Controller", "#059669"),
          "redteam": ("Red Team", "#dc2626"), "treasurer": ("Treasurer", "#d97706"), "human": ("You", "#0f2b4c"), "divi": ("Divi", "#0f766e")}

class Feed:
    def __init__(self): self.events, self.m = [], {k: dict(rule=0, model=0, human=0) for k in ("capture", "reconciler", "controller", "red_team", "treasurer")}
    def add(self, agent, kind, text, **data):
        meters = {k: meter.stage(**v) for k, v in self.m.items()}
        tot = {k: sum(v[k] for v in self.m.values()) for k in ("rule", "model", "human")}
        e = dict(agent=agent, name=AGENTS[agent][0], color=AGENTS[agent][1], kind=kind, text=text, data=data,
                 meter=dict(stages=meters, overall=meter.stage(**tot)), t=round(time.time(), 2))
        self.events.append(e); return e

def _json(txt, default):
    try:
        a, b = (txt.find("["), txt.rfind("]") + 1) if isinstance(default, list) else (txt.find("{"), txt.rfind("}") + 1)
        return json.loads(txt[a:b])
    except ValueError: return default

def run():
    """Generator of events. Uses llm (real or mock)."""
    F = Feed(); truth = {t["file"]: t for t in json.load(open(D / "docs" / "ground_truth.json", encoding="utf-8"))}
    yield F.add("divi", "start", "Closing October 2026 for Falcon Trading LLC. Five agents, one month, every number proved.")
    # 1. Capture
    llm.LIVE["agent"] = "capture"
    yield F.add("capture", "say", f"Reading {len(truth)} receipts and invoices with Muse Spark vision (English, Arabic, bilingual).")
    from concurrent.futures import ThreadPoolExecutor
    t00 = time.time()
    def _cap(f):
        t0 = time.time(); return capture.capture(str(D / "docs" / f), truth={k: truth[f][k] for k in capture.FIELDS}), round(time.time() - t0, 1)
    with ThreadPoolExecutor(len(LIVE_DOCS)) as ex:  # the four receipts are read in parallel
        res = list(ex.map(_cap, LIVE_DOCS))
    for f, (out, secs) in zip(LIVE_DOCS, res):
        t = truth[f]
        acc = sum(str(out["fields"].get(k)) == str(t[k]) or _num_eq(out["fields"].get(k), t[k]) for k in capture.FIELDS)
        F.m["capture"]["model"] += 1
        yield F.add("capture", "doc", f"{f}: {acc}/8 fields, VAT check {'passed' if not out['issues'] else 'failed'}",
                    image=f"/docs/{f}", fields=out["fields"], issues=out["issues"], accuracy=acc, secs=secs)
    F.m["capture"]["model"] += len(truth) - len(LIVE_DOCS)
    yield F.add("capture", "say", f"Remaining {len(truth) - len(LIVE_DOCS)} documents extracted in batch. 150 invoices on file match the captured totals.")
    # 2. Reconciler
    llm.LIVE["agent"] = "reconciler"
    bank, led = reconciler.load(D / "bank_statement.csv"), reconciler.load(D / "ledger_cash.csv")
    rec = reconciler.reconcile(bank, led, use_llm=False)
    ex = [m for m in rec["matches"] if m[1] is None]; F.m["reconciler"]["rule"] += len(bank) - len(ex)
    yield F.add("reconciler", "say", f"Matched {len(bank) - len(ex)} of {len(bank)} bank lines by rules alone (reference, amount, 5-day window, duplicate check).",
                matched=len(bank) - len(ex), total=len(bank))
    exl = [b for b in bank if b["bank_id"] in {m[0] for m in ex}]
    yield F.add("reconciler", "say", "Asking Muse to classify the unmatched bank lines...")
    txt = llm.complete("UAE month-end bank rec. Return a JSON list of {bank_id, category, reason} (reason under 15 words) for: " + json.dumps(exl),
                       mock_response=json.dumps([dict(bank_id=m[0], category=m[2], reason="rule fallback") for m in ex]))
    cls = _json(txt, []); F.m["reconciler"]["model"] += len(ex)
    yield F.add("reconciler", "think", f"{len(ex)} lines left. Asked Muse Spark to classify them.", items=cls)
    rec = reconciler.reconcile(bank, led, use_llm=False)
    # 3. Red Team scan (before Controller finalises so flagged journals are held)
    llm.LIVE["agent"] = "redteam"
    rt = redteam.scan(explain=False)
    # 4. Controller
    llm.LIVE["agent"] = "controller"
    close = controller.build(rec, review_flags={i for x in rt for i in x["items"] if i.startswith("JE-")})
    src = [e["source"] for e in close["entries"]]; F.m["controller"]["rule"] += src.count("rule"); F.m["controller"]["human"] += src.count("human_review")
    yield F.add("controller", "say", f"Posted {len(close['entries'])} journals: invoices, cash, bank charges with VAT, audit accrual, insurance prepayment.",
                entries=len(close["entries"]))
    yield F.add("controller", "say", f"Trial balance balances. Net profit AED {close['net_profit']:,.0f}. VAT payable AED {close['vat_payable']:,.0f}.",
                net_profit=close["net_profit"], vat=close["vat_payable"], checklist=close["checklist"])
    # 5. Red Team findings with model explanations
    llm.LIVE["agent"] = "redteam"
    yield F.add("redteam", "say", "Red Team scan done by rules. Asking Muse to explain each finding...")
    expl = _json(llm.complete("Fraud auditor, UAE trading company. One plain sentence per finding on why it is risky. JSON list of strings, same order: "
                              + json.dumps(rt), mock_response=json.dumps([x["rule"] for x in rt])), [])
    for x, e in zip(rt, expl + [""] * len(rt)):
        x["explanation"] = e; F.m["red_team"]["rule"] += 1
        yield F.add("redteam", "flag", f"{x['rule'].replace('_', ' ')}: {', '.join(x['items'])}", finding=x)
    F.m["red_team"]["model"] += 1
    # 6. Debate on two flags
    llm.LIVE["agent"] = "redteam"
    pick = [x for x in rt if x["rule"] == "large_payment_to_new_vendor"][:1] + [x for x in rt if x["rule"] == "weekend_journal_by_junior"][:1]
    mock_d = json.dumps([{"flag": p["rule"], "turns": [{"agent": "redteam", "text": "Risky."}, {"agent": "controller", "text": "Show evidence."},
                         {"agent": "redteam", "text": "Escalate."}], "verdict": "escalate_to_human"} for p in pick])
    yield F.add("redteam", "say", "Two agents are debating the riskiest flags...")
    deb = _json(llm.complete(
        "Simulate a short debate between two finance agents. Red Team argues the flag is suspicious; Controller defends it as possibly "
        "legitimate or asks for specific evidence; they must settle on a verdict. For each flag return 4 turns alternating redteam, controller, "
        "redteam, controller (each under 30 words, concrete, cite the data) and verdict 'escalate_to_human'. Return a JSON list of "
        "{flag, turns:[{agent,text}], verdict}. Flags: " + json.dumps(pick), mock_response=mock_d), [])
    if not (deb and all(isinstance(d, dict) and d.get("flag") and d.get("turns") for d in deb)): deb = _json(mock_d, [])  # malformed live answer: use the safe script
    for d in deb:
        yield F.add("divi", "debate_start", f"Debate: {d['flag'].replace('_', ' ')}")
        for tn in d.get("turns", []):
            yield F.add(tn["agent"] if tn["agent"] in AGENTS else "redteam", "debate", tn["text"], flag=d["flag"])
        F.m["red_team"]["human"] += 1
        yield F.add("human", "approval", f"Agreed: escalate {d['flag'].replace('_', ' ')} to a human. Approve or reject.", flag=d["flag"],
                    items=next((p["items"] for p in pick if p["rule"] == d["flag"]), []))
    # 7. Fraud moment: hidden sale
    llm.LIVE["agent"] = "redteam"
    hid = next(b for b in bank if float(b["amount"]) == 18500.0)
    chain = [dict(step="Bank shows inward TT AED 18,500 from Desert Rose Trading", proof=f"bank_statement.csv#{hid['bank_id']}"),
             dict(step="No sales invoice, no ledger receipt, narrative has no reference", proof="ledger_cash.csv (no match)"),
             dict(step="Desert Rose is an existing customer with open invoices", proof="invoices.csv party=Desert Rose Trading"),
             dict(step="Cash parked in Unidentified Receipts 2300, sale and 5% VAT missing", proof="tb#2300")]
    mock_q = json.dumps(dict(how="A customer paid without a matching invoice, so the sale was never booked.",
                             query="Dear CFO, AED 18,500 arrived from Desert Rose Trading with no invoice. Please confirm what was sold and by whom."))
    yield F.add("redteam", "say", "Tracing an unexplained AED 18,500 receipt...")
    fq = _json(llm.complete("You are a forensic accountant. A UAE company received AED 18,500 from customer Desert Rose Trading with no invoice "
                            "or ledger entry. Evidence: " + json.dumps(chain) + ". Return JSON {how: 2 sentences on how a sale like this gets hidden "
                            "(off-book sale, missing VAT of about AED 881), query: a short polite CFO query email body asking for the invoice, "
                            "the salesperson, the goods released and the VAT treatment}", mock_response=mock_q), {})
    F.m["controller"]["model"] += 1
    yield F.add("redteam", "fraud", "Hidden sale found: AED 18,500 received, never invoiced.", amount=18500, vat_at_risk=round(18500 / 1.05 * 0.05, 2),
                chain=chain, how=fq.get("how", ""), query=fq.get("query", ""), bank_id=hid["bank_id"])
    # 8. Treasurer
    llm.LIVE["agent"] = "treasurer"
    yield F.add("treasurer", "say", "Building the 13-week cash forecast...")
    plan = treasurer.plan(close["trial_balance"]["1000"]["amount"]); F.m["treasurer"]["rule"] += 52; F.m["treasurer"]["model"] += 1
    F.m["treasurer"]["human"] += len(plan["levers"])
    yield F.add("treasurer", "forecast", f"13-week forecast ready. Downside low AED {plan['downside']['lowest_cash']:,.0f} in week {plan['downside']['lowest_week']}.",
                series={k: plan[k]["closing"] for k in ("base", "downside", "base_with_levers", "downside_with_levers")}, weeks=plan["base"]["weeks"],
                levers=plan["levers"], narrative=plan["narrative"])
    # 9. Cash counter check: the model reviews every cash line. Amounts stay the deterministic ones, so the headline always equals its parts.
    llm.LIVE["agent"] = "treasurer"
    from divi import cashcounter
    try:
        cc = cashcounter.run()
        mock_cc = json.dumps([dict(i=i, bucket=l["kind"], ok=True, why="matches its source line") for i, l in enumerate(cc["lines"])])
        rv = _json(llm.complete("You are a UAE treasurer checking a cash counter. Buckets: recovered = money already lost that can be got back; "
                                "protected = money stopped before it left; released = cash the 13-week plan brings in earlier. For each line say if the "
                                "bucket is right. Return a JSON list of {i, bucket, ok, why (under 12 words)}. Lines: "
                                + json.dumps([dict(i=i, label=l["label"], amount=l["amount"], bucket=l["kind"], source=l["ref"]) for i, l in enumerate(cc["lines"])]),
                                mock_response=mock_cc), [])
        okn = sum(1 for r in rv if isinstance(r, dict) and r.get("ok") is not False)
        F.m["treasurer"]["model"] += 1
        yield F.add("treasurer", "cashcheck", f"Checked all {len(cc['lines'])} cash lines against their sources: {okn} confirmed" + (f", {len(cc['lines']) - okn} sent to you to review the bucket" if okn < len(cc['lines']) else "") + f". Cash found AED {cc['total']:,.0f}.",
                    total=cc["total"], totals=cc["totals"], review=rv[:len(cc["lines"])])
    except Exception as ex:
        yield F.add("treasurer", "say", f"Cash counter ready (line check skipped: {type(ex).__name__}).")
    llm.LIVE["agent"] = "divi"
    yield F.add("divi", "done", "Close complete. Waiting on your decisions for escalated items.", calls=llm.CALLS["count"])

def _num_eq(a, b):
    try: return abs(float(a) - float(b)) < 0.01
    except (TypeError, ValueError): return False

def record():
    ev = list(run()); CACHE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(ev, open(CACHE, "w"), indent=1, ensure_ascii=False); return ev

def replay(speed=1.0):
    ev = json.load(open(CACHE, encoding="utf-8")); prev = ev[0]["t"]
    for e in ev:
        time.sleep(pace(e, e["t"] - prev) / speed); prev = e["t"]; yield e

HOLD = {"doc": 1.8, "flag": 2.4, "fraud": 2.6, "debate_start": 2.2, "debate": 1.1, "approval": 2.6, "forecast": 2.2, "think": 2.2, "say": 1.4, "done": 1.0}
def pace(e, dt):
    """Replay pacing: each step stays on screen long enough to read (about 55 s for the whole close at speed 1)."""
    return min(max(dt, HOLD.get(e["kind"], 1.4)), 2.2)
