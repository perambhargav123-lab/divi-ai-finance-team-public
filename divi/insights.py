"""Runs the depth layer and writes out/insights.json for the dashboard: proof counter, judgment, AI cash, drafts, UAE tax, flux, benchmark, trace."""
import json
from pathlib import Path
from divi import llm, judgment, flux, benchmark, verify, uae, learning
from divi.agents import outreach
O = Path(__file__).resolve().parents[1] / "out"
ACCOUNTANT = dict(hours=40, rate_aed=120, basis="assumption: 5 working days for one UAE accountant at AED 120 per hour for a manual month-end close of this size")

def trace():
    c = json.load(open(llm.CACHE_FILE, encoding="utf-8")) if llm.CACHE_FILE.exists() else {}
    rows = [dict(purpose=e["purpose"], model=e["model"], tokens_in=e["tokens_in"], tokens_out=e["tokens_out"], latency_s=e["latency_s"],
                 cost_aed=llm._cost(e["tokens_in"], e["tokens_out"])) for e in c.values()]
    close = [r for r in rows if True]
    tot = round(sum(r["cost_aed"] for r in close), 2); hrs = ACCOUNTANT["hours"] * ACCOUNTANT["rate_aed"]
    return dict(calls=rows, close_calls=len(close), tokens=sum(r["tokens_in"] + r["tokens_out"] for r in close), cost_aed=tot,
                latency_s=round(sum(r["latency_s"] for r in close), 1), accountant_cost_aed=hrs, accountant=ACCOUNTANT,
                price_note="muse-spark-1.3 standard mode: USD 1.25 per 1M input tokens, USD 4.25 per 1M output tokens (dev.meta.ai pricing, 27 Oct 2026), USD 1 = AED 3.6725",
                not_metered="Earlier day 1 to 4 agent calls (capture vision, commentary, red team explanations, treasury narrative, CFO chat, ASR) ran before token tracing and are not in this table.")

def build():
    j = judgment.run(); cash = outreach.run(); fx = flux.run(); bench = benchmark.run()
    planted = verify.verify([dict(c) for c in verify.PLANTED], "test")
    claims = j["findings"] + j["signals"] + j["adjustments"] + fx["commentary"]
    proof = dict(total=len(claims), verified=sum(c["verified"] for c in claims), rejected=sum(not c["verified"] for c in claims),
                 rejected_items=[dict(claim=c["claim"], why=c["muse_reason"] if c["det_ok"] else c["det_reason"]) for c in claims if not c["verified"]],
                 planted_total=len(planted), planted_caught=sum(not c["verified"] for c in planted), planted=planted)
    out = dict(proof=proof, judgment=j, cash=cash, flux=fx, benchmark=bench,
               uae=dict(vat=uae.vat201(), ct=uae.corporate_tax(j["adjustments"]), einv=uae.einvoice()), trace=trace())
    json.dump(out, open(O / "insights.json", "w"), indent=1, ensure_ascii=False); return out

if __name__ == "__main__":
    o = build(); p = o["proof"]
    print(f"claims verified {p['verified']}/{p['total']}, rejected {p['rejected']}; planted caught {p['planted_caught']}/{p['planted_total']}")
    print("P(cash<0) week6", o["cash"]["base"]["p_negative_w6"], "any", o["cash"]["base"]["p_negative_any"], "with actions", o["cash"]["with_actions"]["p_negative_any"])
    print("bench", o["benchmark"]["detection_rate"], o["benchmark"]["precision"], "trace", o["trace"]["close_calls"], o["trace"]["cost_aed"])
