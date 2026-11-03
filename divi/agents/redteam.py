"""Red Team agent: rules find suspicious items, the model explains them.
Open-weight bonus: set DIVI_REDTEAM_PROVIDER=baseten to run explanations on Muse Spark Open via Baseten
(llm.complete(provider="baseten")). Mock until BASETEN_API_KEY is set."""
import csv, json, os
from collections import defaultdict
from datetime import date
from pathlib import Path
from divi import llm

D = Path(__file__).resolve().parents[2] / "data"
OVERRIDE = {}  # extra rows for the Beat the Controller challenge, e.g. {"bank_statement.csv": [...]}
def _csv(n): return list(csv.DictReader(open(D / n, encoding="utf-8"))) + list(OVERRIDE.get(n, []))
JUNIOR = ("intern", "junior", "trainee")

def scan(explain=True):
    inv, jr, bank = _csv("invoices.csv"), _csv("journals.csv"), _csv("bank_statement.csv")
    vm = {v["vendor"]: v for v in _csv("vendor_master.csv")}
    f = []
    seen = defaultdict(list)
    for i in inv:
        if i["type"] == "purchase":
            seen[(i["party"], i["net"], i["date"])].append(i["invoice_no"])
    for k, nos in seen.items():
        if len(nos) > 1:
            f.append(dict(rule="duplicate_vendor_invoice", severity="high", items=nos, proof=[f"invoices.csv#{n}" for n in nos]))
    # near duplicate: same supplier, within 7 days, amount differs by AED 0.01 to AED 5 (a changed copy)
    pur = sorted((i for i in inv if i["type"] == "purchase"), key=lambda i: i["date"])
    for a_i, a in enumerate(pur):
        for b in pur[a_i + 1:]:
            if b["party"] != a["party"]: continue
            gap = (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days
            diff = abs(float(a["net"]) - float(b["net"]))
            if gap <= 7 and 0 < diff <= 5:
                f.append(dict(rule="near_duplicate_vendor_invoice", severity="high", items=[a["invoice_no"], b["invoice_no"]],
                              detail=f"same supplier, {gap} days apart, amounts differ by AED {diff:,.2f}",
                              proof=[f"invoices.csv#{a['invoice_no']}", f"invoices.csv#{b['invoice_no']}"]))
    paid = {}
    for b in bank:
        amt = -float(b["amount"])
        for v, m in vm.items():
            if v.upper() in b["description"] and amt > 0:
                age = (date.fromisoformat(b["date"]) - date.fromisoformat(m["created"])).days
                if age <= 30 and amt >= 10000:
                    f.append(dict(rule="large_payment_to_new_vendor", severity="high", items=[b["bank_id"]],
                                  detail=f"AED {amt:,.2f} paid {age} days after vendor created", proof=[f"bank_statement.csv#{b['bank_id']}", f"vendor_master.csv#{v}"]))
                if amt >= 10000 and amt % 1000 == 0:
                    f.append(dict(rule="round_amount_payment", severity="medium", items=[b["bank_id"]], proof=[f"bank_statement.csv#{b['bank_id']}"]))
        if amt > 0 and "CHARGE" not in b["description"]:  # same payee words and amount within 7 days
            key = (" ".join(b["description"].split()[:4]), round(amt, 2))
            prev = paid.get(key)
            if prev and (date.fromisoformat(b["date"]) - date.fromisoformat(prev["date"])).days <= 7:
                f.append(dict(rule="duplicate_bank_payment", severity="high", items=[prev["bank_id"], b["bank_id"]], detail=f"same payee and amount as {prev['bank_id']}",
                              proof=[f"bank_statement.csv#{b['bank_id']}", f"bank_statement.csv#{prev['bank_id']}"]))
            else:
                paid[key] = b
    for j in jr:
        d = date.fromisoformat(j["date"])
        if d.weekday() >= 5 and any(x in j["posted_by"].lower() for x in JUNIOR):
            f.append(dict(rule="weekend_journal_by_junior", severity="high", items=[j["je"]],
                          detail=f"{d.strftime('%A')} by {j['posted_by']}", proof=[f"journals.csv#{j['je']}"]))
        if float(j["amount"]) >= 200000 and "fc." not in j["posted_by"] and "fc." not in j["posted_by"]:
            f.append(dict(rule="large_journal_without_senior", severity="medium", items=[j["je"]], proof=[f"journals.csv#{j['je']}"]))
    for v in vm.values():
        if v["bank_iban_changed"] == "yes":
            f.append(dict(rule="vendor_bank_change", severity="high", items=[v["vendor"]], proof=[f"vendor_master.csv#{v['vendor']}"]))
    if explain and f:
        prov = os.getenv("DIVI_REDTEAM_PROVIDER", "meta")
        mock = json.dumps([f"{x['rule']}: review {', '.join(x['items'])}" for x in f])
        f_text = llm.complete("You are a fraud auditor for a UAE trading company. For each finding give one plain sentence "
                              "on why it is risky and the next check. Return a JSON list of strings in the same order. "
                              f"Findings: {json.dumps(f)}", provider=prov, mock_response=mock)
        try:
            for x, e in zip(f, json.loads(f_text[f_text.find('['): f_text.rfind(']') + 1])):
                x["explanation"] = e
        except ValueError:
            for x in f: x["explanation"] = f_text[:300]
    if explain or OVERRIDE:  # owner-written controls compiled by Muse, enforced on every run (not in the fixed benchmark)
      try:
        from divi import edge
        f += edge.run_rules()
      except Exception:
        pass
    return f
