"""Muse reads unstructured contracts and messages, then the engine checks invoices against them.
Outputs: contract findings (overbilling, early-pay discount, escalation), customer payment signals, cut-off / IFRS 15 adjustments.
Every finding is a claim with citations and goes through the Verifier."""
import csv, json
from pathlib import Path
from divi import llm, sources, verify
D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"
CONTRACTS = sorted(p.name for p in (D / "contracts").glob("*.txt"))
def _csv(n): return list(csv.DictReader(open(D / n, encoding="utf-8")))
def messages(): return [json.loads(l) for l in open(D / "messages.jsonl", encoding="utf-8")]

def read_contracts():
    text = "\n\n".join(f"== contracts/{n}\n" + sources.line_numbered(f"contracts/{n}") for n in CONTRACTS)
    mock = json.dumps(dict(prices=[dict(vendor="Palm Foods Import", item="Basmati rice per kg", price=11.0, cite="contracts/palm_foods_supply.txt#L5")],
                           terms=[]))
    raw = llm.ask("contracts: extract prices and terms", "Read these fictional UAE contracts. Return only JSON {prices:[{vendor,item,price,cite}], "
                  "terms:[{party, kind (early_pay_discount|price_escalation|credit_terms|rebate|dispute_clause|title_transfer), summary, "
                  "pct (number or null), days (number or null), effective (date or null), cite}]}. cite is like contracts/<file>#L<n> for the exact line.\n" + text, mock)
    return llm.parse(raw, {"prices": [], "terms": []})

def contract_findings(ct):
    out = []; lines = _csv("invoice_lines.csv"); inv = {r["invoice_no"]: r for r in _csv("invoices.csv")}
    price = {(p["vendor"], p["item"].lower()[:12]): p for p in ct["prices"]}
    for l in lines:
        p = next((v for (vn, it), v in price.items() if vn == l["party"] and it[:6] in l["item"].lower()), None)
        if not p: continue
        diff = round(float(l["unit_price"]) - float(p["price"]), 4)
        if diff > 0.001:
            over = round(float(l["qty"]) * diff, 2)
            out.append(dict(kind="overbilling", party=l["party"], invoice=l["invoice_no"], amount=over, status=inv[l["invoice_no"]]["status"],
                claim=f"{l['party']} invoice {l['invoice_no']} charges AED {float(l['unit_price']):.2f} per unit against the contract price of AED {float(p['price']):.2f}; "
                      f"{float(l['qty']):,.2f} units overbilled by AED {over:,.2f} before VAT (AED {over*1.05:,.2f} with VAT).",
                cites=[f"invoice_lines.csv#{l['invoice_no']}", p["cite"]], calc_inputs=[diff],
                action=f"Hold payment of {l['invoice_no']} and request a credit note of AED {over*1.05:,.2f} under the overbilling clause."))
    for t in ct["terms"]:
        if t["kind"] == "early_pay_discount":
            spend = sum(float(i["total"]) for i in inv.values() if i["party"] == t["party"])
            out.append(dict(kind="early_pay_discount", party=t["party"], amount=round(spend * (t.get("pct") or 0) / 100, 2),
                claim=f"{t['party']} offers {t.get('pct')}% off for payment within {t.get('days')} days; on October spend of AED {spend:,.2f} that is worth AED {spend*(t.get('pct') or 0)/100:,.2f} a month.",
                cites=[t["cite"], f"agg:invoices#{t['party']}|total"], action="Pay this supplier on day 10 when cash allows."))
        if t["kind"] == "price_escalation" and t.get("pct"):
            spend = sum(float(i["net"]) for i in inv.values() if i["party"] == t["party"])
            out.append(dict(kind="price_escalation", party=t["party"], amount=round(spend * (t.get("pct") or 0) / 100, 2),
                claim=f"{t['party']} prices rise {t.get('pct')}% from {t.get('effective')}; at October volume of AED {spend:,.2f} that adds AED {spend*(t.get('pct') or 0)/100:,.2f} a month to cost.",
                cites=[t["cite"], "messages.jsonl#M07", f"agg:invoices#{t['party']}|net"], action="Buy ahead in November or renegotiate before 1 December."))
    return out

def read_messages():
    ar = {}
    for i in _csv("invoices.csv"):
        if i["type"] == "sale" and i["status"] == "open": ar.setdefault(i["party"], []).append(dict(no=i["invoice_no"], total=i["total"], due=i["due"]))
    mock = json.dumps(dict(signals=[], adjustments=[]))
    raw = llm.ask("messages: payment signals and cut-off", "You are the controller of Falcon Trading LLC (UAE, IFRS). Close date 31 Oct 2026. Read these emails and "
        "WhatsApp messages. Return only JSON {signals:[{customer, kind (promise_to_pay|dispute|payment_plan|on_time|unbilled_receipt), "
        "pay_after (YYYY-MM-DD or null), amount_aed (number or null), claim (one plain sentence), cites:[\"messages.jsonl#Mxx\"]}], "
        "adjustments:[{kind (accrued_revenue|prepayment|unbilled_revenue|supplier_price_notice), standard (e.g. IFRS 15), dr, cr, amount_aed, "
        "claim (one plain sentence with the reason), cites:[...]}]}. Cite invoice rows as invoices.csv#<no> and bank rows as bank_statement.csv#<id> when used. "
        "Bank line B160 is an unexplained AED 18,500 receipt.\nMESSAGES:\n" + "\n".join(json.dumps(m, ensure_ascii=False) for m in messages())
        + "\nOPEN AR:\n" + json.dumps(ar) + "\nBANK B160: " + sources.resolve("bank_statement.csv#B160") + "\nINVOICE PI-0001: " + sources.resolve("invoices.csv#PI-0001"), mock)
    return llm.parse(raw, {"signals": [], "adjustments": []})

def run():
    ct = read_contracts(); cf = contract_findings(ct); ms = read_messages()
    claims = [dict(source="contracts", **f) for f in cf]
    claims += [dict(source="messages", **s) for s in ms["signals"]]
    for a in ms["adjustments"]:
        if a.get("amount_aed"): a["claim"] = a["claim"].rstrip(".") + f". Adjustment AED {float(a['amount_aed']):,.2f}: Dr {a.get('dr')}, Cr {a.get('cr')}."
        claims.append(dict(source="cut-off", **a))
    verify.verify(claims, "verifier: contracts and messages")
    out = dict(contract_terms=ct, findings=[c for c in claims if c["source"] == "contracts"],
               signals=[c for c in claims if c["source"] == "messages"], adjustments=[c for c in claims if c["source"] == "cut-off"])
    json.dump(out, open(O / "judgment.json", "w"), indent=1, ensure_ascii=False)
    return out
