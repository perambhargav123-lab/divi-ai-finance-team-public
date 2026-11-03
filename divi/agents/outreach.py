"""Collections and Supplier agents: Muse drafts tailored messages, the Monte Carlo model prices each one's cash impact.
Drafts are never sent; the UI only offers Approve or Reject."""
import json
from pathlib import Path
from divi import llm, cashai
O = Path(__file__).resolve().parents[2] / "out"
COLL = [  # customer, situation, action effect on the cash model
    dict(id="C1", party="Gulf Star Supermarkets", effect=dict(p_over={"Gulf Star Supermarkets": 0.8}), facts="AED 48,000 is 61 to 90 days overdue; they wrote they pay after 15 Nov (messages.jsonl#M01); history pays 26 days late on average; credit limit 150,000 and contract allows suspending deliveries over 30 days overdue (gulf_star_customer.txt L4). Long relationship, big account.", tone="firm but warm"),
    dict(id="C2", party="Oasis Hotels FZE", effect=dict(p_over={"Oasis Hotels FZE": 0.85}), facts="AED 52,000 over 90 days; they propose 26,000 mid Nov and 26,000 mid Dec (M14); separately dispute AED 12,000 of FT-S-0066 for water-damaged linen (M02); contract says undisputed amounts stay payable on time and disputes go to finance directors within 14 days (oasis_hotels_customer.txt L5-L6).", tone="dispute path: acknowledge claim, separate undisputed amount"),
    dict(id="C3", party="Sharjah Wholesale Co", effect=dict(p_over={"Sharjah Wholesale Co": 0.92}), facts="AED 40,000 31 to 60 days overdue; they offered 20,000 on 20 Nov and 20,000 on 10 Dec (M06); history 20 days late with high variability.", tone="supportive, lock in dates"),
]
SUPP = [
    dict(id="S1", party="Zenith Electronics FZCO", effect=dict(ap_shift={"PI-0050": 30, "PI-0014": 30, "PI-0037": 30, "PI-0013": 30}), facts="Invoices PI-0050, PI-0014, PI-0037, PI-0013 (about AED 60,400) fall due 18 to 25 Nov, our tightest weeks. Ask for 30 more days on these. Contract terms are 60 days. They plan a 3% increase from 1 Dec (M07); offer an early volume commitment instead.", tone="partner"),
    dict(id="S2", party="Sahara Freight Services", effect=dict(ap_shift={"PI-0044": 30}), facts="PI-0044 AED 8,790.54 due 20 Nov. Ask for 30 days. Fuel surcharge stays flat in Nov (M12).", tone="polite"),
    dict(id="S3", party="Palm Foods Import", effect=dict(ap_shift={"PI-0012": 21}), facts="PI-0012 bills basmati at AED 12.50 per kg but the contract fixes AED 11.00 (palm_foods_supply.txt L5) and price changes need 60 days notice and a signed amendment (L8). Overbilled AED 3,738.35 with VAT. Request a credit note within 14 days (L9); we hold PI-0012 until then.", tone="firm, contract based"),
]

def run():
    j = json.load(open(O / "judgment.json")); model = cashai.behaviour(j["signals"]); op = cashai.opening_cash()
    base = cashai.simulate(op, model); low = min(range(13), key=lambda w: base["p50"][w])
    items = COLL + SUPP
    mock = json.dumps({x["id"]: dict(subject=f"{x['party']} account", body="Draft (mock).") for x in items})
    raw = llm.ask("collections and supplier drafts", "You write for Falcon Trading LLC finance (Dubai). Draft one short email per item (max 110 words body, plain words, "
        "no em dashes, sign off 'Finance team, Falcon Trading LLC'). Match the tone. Use only the facts given. Return only JSON {id: {subject, body}}.\n"
        + json.dumps([{k: x[k] for k in ("id", "party", "facts", "tone")} for x in items]), mock)
    drafts = llm.parse(raw, {})
    out = []
    for x in items:
        s = cashai.simulate(op, model, **x["effect"])
        out.append(dict(id=x["id"], agent="Collections" if x in COLL else "Supplier", party=x["party"], tone=x["tone"], **drafts.get(x["id"], {}),
                        impact=dict(p50_low_week=low + 1, p50_delta=round(s["p50"][low] - base["p50"][low], 2),
                                    p_neg_before=base["p_negative_any"], p_neg_after=s["p_negative_any"]), status="draft, not sent"))
    allfx = dict(p_over={}, ap_shift={})
    for x in items:
        for k, v in x["effect"].items(): allfx[k].update(v)
    combined = cashai.simulate(op, model, **allfx)
    res = dict(base=base, with_actions=combined, drafts=out, model={c: {k: v for k, v in m.items() if k != "history"} for c, m in model.items()})
    json.dump(res, open(O / "cash_ai.json", "w"), indent=1, ensure_ascii=False); return res
