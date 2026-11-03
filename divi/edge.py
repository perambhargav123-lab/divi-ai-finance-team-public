"""Edge features: owner-written controls, Beat the Controller, model router, long-document covenant check,
debate scorecard, control alerts and missing-receipt requests. All fictional data, drafts only, nothing is sent."""
import csv, json, re
from datetime import date
from pathlib import Path
from divi import llm, sources

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; O = ROOT / "out"
RULES = O / "custom_rules.json"; BOARD = O / "leaderboard.json"


def _csv(n):
    from divi.agents import redteam
    return redteam._csv(n)


def _json(t, default):
    try:
        s = t[min([i for i in (t.find("{"), t.find("[")) if i >= 0]):]; return json.loads(s[: max(s.rfind("}"), s.rfind("]")) + 1])
    except Exception:
        return default


# 1. Write your own control ---------------------------------------------------------------------------------
SCHEMA = {
    "payments": {"amount": "number AED paid out", "date": "YYYY-MM-DD", "weekday": "Monday..Sunday", "payee": "text from bank narrative",
                 "vendor": "matched vendor name or empty", "vendor_created": "YYYY-MM-DD or empty", "vendor_age_days": "days from vendor creation to payment (999 if unknown)",
                 "vendor_created_this_month": "true/false (created in October 2026)", "payee_in_vendor_master": "true/false",
                 "transfer_out": "true/false (outward transfer or TT, not a card purchase or direct debit)", "round_thousand": "true/false", "bank_changed": "true/false"},
    "invoices": {"type": "sale or purchase", "party": "text", "net": "number", "vat": "number", "total": "number", "date": "YYYY-MM-DD", "weekday": "text", "status": "text"},
    "journals": {"amount": "number", "posted_by": "text", "weekday": "text", "memo": "text", "debit": "account code", "credit": "account code"},
}
OPS = (">", ">=", "<", "<=", "==", "!=", "contains", "not_contains")


def rows(source):
    if source == "payments":
        vm = {v["vendor"]: v for v in _csv("vendor_master.csv")}; out = []
        for b in _csv("bank_statement.csv"):
            amt = -float(b["amount"])
            if amt <= 0: continue
            v = next((k for k in vm if k.upper() in b["description"].upper()), ""); m = vm.get(v, {})
            d = date.fromisoformat(b["date"]); vc = m.get("created", "")
            out.append(dict(id=b["bank_id"], ref=f"bank_statement.csv#{b['bank_id']}", amount=amt, date=b["date"], weekday=d.strftime("%A"), payee=b["description"],
                            vendor=v, vendor_created=vc, vendor_age_days=(d - date.fromisoformat(vc)).days if vc else 999,
                            vendor_created_this_month=bool(vc) and vc.startswith("2026-10"), round_thousand=amt >= 1000 and amt % 1000 == 0,
                            bank_changed=m.get("bank_iban_changed") == "yes", payee_in_vendor_master=bool(v),
                            transfer_out=bool(re.match(r"(OUTWARD PAYMENT|TT |TRANSFER|TT$)", b["description"].upper()))))
        return out
    if source == "invoices":
        return [dict(i, id=i["invoice_no"], ref=f"invoices.csv#{i['invoice_no']}", net=float(i["net"]), vat=float(i["vat"]), total=float(i["total"]),
                     weekday=date.fromisoformat(i["date"]).strftime("%A")) for i in _csv("invoices.csv")]
    if source == "journals":
        return [dict(j, id=j["je"], ref=f"journals.csv#{j['je']}", amount=float(j["amount"])) for j in _csv("journals.csv")]
    return []


def _test(v, op, x):
    if isinstance(v, bool): x = str(x).lower() in ("true", "1", "yes") if not isinstance(x, bool) else x
    elif isinstance(v, (int, float)): x = float(x)
    else: v, x = str(v).lower(), str(x).lower()
    return {">": lambda: v > x, ">=": lambda: v >= x, "<": lambda: v < x, "<=": lambda: v <= x, "==": lambda: v == x, "!=": lambda: v != x,
            "contains": lambda: x in v, "not_contains": lambda: x not in v}[op]()


def validate(rule):
    """The generated rule is data, never code: only known sources, fields and operators are accepted."""
    src = rule.get("source"); conds = rule.get("conditions") or []
    if src not in SCHEMA: raise ValueError(f"unknown source {src}")
    if not conds: raise ValueError("no conditions")
    for c in conds:
        if c.get("field") not in SCHEMA[src]: raise ValueError(f"unknown field {c.get('field')}")
        if c.get("op") not in OPS: raise ValueError(f"unknown operator {c.get('op')}")
    rule["severity"] = rule.get("severity") if rule.get("severity") in ("high", "medium", "low") else "high"
    return rule


def _mock_compile(text):
    t = text.lower(); conds = []
    m = re.search(r"(?:over|above|more than|exceeding|>)\s*(?:aed\s*)?([\d,.]+)\s*(k|m)?", t)
    if m:
        n = float(m.group(1).replace(",", "")) * {"k": 1e3, "m": 1e6}.get(m.group(2) or "", 1)
        conds.append(dict(field="amount", op=">", value=n))
    if "this month" in t or "new vendor" in t: conds.append(dict(field="vendor_created_this_month", op="==", value=True))
    if "weekend" in t: conds.append(dict(field="weekday", op="contains", value="sat"))
    return dict(name=re.sub(r"\W+", "_", t)[:40].strip("_"), source="journals" if "journal" in t else "payments", conditions=conds or [dict(field="amount", op=">", value=20000)],
                severity="high", plain=text)


def compile_rule(text):
    prompt = ("You turn a finance owner's control, written in plain English, into a JSON rule that a program will run. "
              "Use ONLY these sources and fields: " + json.dumps(SCHEMA) + f". Operators: {list(OPS)}. All conditions are ANDed. "
              "Return JSON {name: snake_case, source, conditions:[{field, op, value}], severity: high|medium|low, plain: one sentence restating the rule}. "
              f"Owner's rule: {text}")
    r = _json(llm.ask("compile_owner_control", prompt, json.dumps(_mock_compile(text))), {})
    try:
        return validate(r), "Muse Spark"
    except Exception:
        return validate(_mock_compile(text)), "fallback parser (model output failed validation)"


def evaluate(rule):
    hits = [r for r in rows(rule["source"]) if all(_test(r.get(c["field"]), c["op"], c["value"]) for c in rule["conditions"])]
    return hits


def add_rule(text):
    rule, by = compile_rule(text); hits = evaluate(rule)
    cur = load_rules(); cur = [r for r in cur if r["name"] != rule["name"]] + [dict(rule, text=text, compiled_by=by)]
    json.dump(cur, open(RULES, "w"), indent=1)
    return dict(rule=rule, compiled_by=by, hits=[dict(id=h["id"], ref=h["ref"], amount=h.get("amount", h.get("total")), what=h.get("payee") or h.get("party") or h.get("memo")) for h in hits])


def load_rules(): return json.load(open(RULES)) if RULES.exists() else []


def run_rules():
    f = []
    for r in load_rules():
        for h in evaluate(r):
            f.append(dict(rule=f"owner_rule_{r['name']}", severity=r["severity"], items=[h["id"]], proof=[h["ref"]], owner_rule=True,
                          explanation=f"Your control: {r.get('plain') or r.get('text')}"))
    return f


# 2. Beat the Controller --------------------------------------------------------------------------------------
def challenge(name, bank=(), vendors=(), invoices=(), journals=()):
    bank_in = list(bank)
    """Sneak rows into a copy of the books; Divi's Red Team (plus owner controls) tries to catch them. Local only."""
    from divi.agents import redteam
    bank = [dict(bank_id=f"X{i:02d}", date=b["date"], description=str(b["description"]).upper(), amount=-abs(float(b["amount"]))) for i, b in enumerate(bank, 1)]
    inv = [dict(type="purchase", invoice_no=v.get("invoice_no") or f"PX-{i:02d}", party=v["party"], trn=v.get("trn", ""), date=v["date"], due=v.get("due", v["date"]),
                net=f"{float(v['net']):.2f}", vat=f"{float(v['net']) * .05:.2f}", total=f"{float(v['net']) * 1.05:.2f}", currency="AED", status="open", flag="")
           for i, v in enumerate(invoices, 1)]
    jr = [dict(je=f"JX-{i:02d}", date=j["date"], weekday=date.fromisoformat(j["date"]).strftime("%A"), posted_by=j["posted_by"], debit=j.get("debit", "6700"),
               credit=j.get("credit", "1000"), amount=float(j["amount"]), memo=j.get("memo", ""), flag="") for i, j in enumerate(journals, 1)]
    vm = [dict(vendor=v["vendor"], created=v["created"], bank_iban_changed=v.get("bank_iban_changed", "no"), trn=v.get("trn", "")) for v in vendors]
    redteam.OVERRIDE.clear(); redteam.OVERRIDE.update({"bank_statement.csv": bank, "vendor_master.csv": vm, "invoices.csv": inv, "journals.csv": jr})
    try:
        f = redteam.scan(explain=False)
    finally:
        redteam.OVERRIDE.clear()
    mine = {b["bank_id"] for b in bank} | {i["invoice_no"] for i in inv} | {j["je"] for j in jr} | {v["vendor"] for v in vm}
    caught = [x for x in f if set(x["items"]) & mine]
    amount = sum(abs(b["amount"]) for b in bank) + sum(float(i["total"]) for i in inv) + sum(j["amount"] for j in jr)
    slipped = sorted(mine - {i for x in caught for i in x["items"]} - {v["vendor"] for v in vm})
    won = bool(mine) and not caught
    score = round(amount) if won else 0
    entry = dict(name=(name or "anonymous")[:24], rows=len(mine), amount=round(amount, 2), caught_by=sorted({x["rule"] for x in caught}), won=won, score=score,
                 time=__import__("datetime").datetime.now().strftime("%d %b %H:%M IST"))
    b = json.load(open(BOARD)) if BOARD.exists() else []; b.append(entry); json.dump(b, open(BOARD, "w"), indent=1)
    json.dump(dict(name=name, bank=list(bank_in), vendors=list(vendors), invoices=list(invoices), journals=list(journals)), open(O / "last_sneak.json", "w"))
    proposal = learn_proposal(bank) if won else None
    return dict(entry, proposal=proposal, caught=caught, slipped=slipped, verdict=("Divi missed it, so this becomes a new benchmark case." if won else
                                                              f"Caught by: {', '.join(r.replace('_', ' ') for r in entry['caught_by'])}."), leaderboard=leaderboard())


LEARN = dict(name="transfer_to_payee_not_in_vendor_master", source="payments", severity="high",
             conditions=[dict(field="transfer_out", op="==", value=True), dict(field="payee_in_vendor_master", op="==", value=False), dict(field="amount", op=">=", value=5000)],
             plain="Flag any outward transfer of AED 5,000 or more to a payee that is not in the vendor master.")


def learn_proposal(bank):
    """Learning loop: a sneak that got through becomes a proposed rule. Shows what it would flag on the real October books first."""
    if not any(b["description"].startswith(("TT", "OUTWARD", "TRANSFER")) for b in bank): return None
    real = evaluate(LEARN)
    return dict(rule=LEARN, why="Your payment went to a payee Divi had never seen and no rule looked at unknown payees.",
                real_book_hits=[dict(id=h["id"], ref=h["ref"], amount=h["amount"], what=h["payee"]) for h in real],
                status="proposed, needs your approval")


def learn_approve():
    """Approve the learned rule, then re-run the last sneak on the same rows."""
    cur = [r for r in load_rules() if r["name"] != LEARN["name"]] + [dict(LEARN, text=LEARN["plain"], compiled_by="learning loop (approved)")]
    json.dump(cur, open(RULES, "w"), indent=1)
    last = json.load(open(O / "last_sneak.json"))
    r = challenge(f"{last['name']} (re-run)", last["bank"], last["vendors"], last["invoices"], last["journals"])
    return r


def leaderboard():
    b = json.load(open(BOARD)) if BOARD.exists() else []
    return sorted(b, key=lambda e: (-e["score"], e["rows"]))[:10]


# 3. Model router ------------------------------------------------------------------------------------------------
WHY = {"muse-spark-1.3": "reasoning, structured JSON and tool calls over the books", "muse-voice-transcribe-1.0": "speech to text for voice questions and voice notes",
       "sam-3.1": "cut the receipt out of a messy photo before reading it", "muse-image-1.0": "thumbnail and end card art (no real people)",
       "rules": "deterministic maths: postings, VAT, matching, covenant tests. No model needed, zero cost"}


STEP_WHY = [("long", "long context: the whole document or month in one call, no chunking"), ("tool", "native function calling picks the right ledger tool"),
            ("vision", "image input: reads and boxes fields on the document"), ("receipt", "image input: reads a photographed receipt"),
            ("verifier", "second model pass checks every claim against its source"), ("debate", "judges two agents using only cited evidence"),
            ("compile", "turns plain English into a validated JSON rule"), ("whatsapp", "short, polite drafts in the owner's voice"),
            ("drafts", "short, polite drafts in the owner's voice"), ("flux", "writes board commentary from the numbers"),
            ("contracts", "extracts prices and terms as structured JSON"), ("messages", "reads emails for payment promises as structured JSON")]


def _why(step, model):
    if model != "muse-spark-1.3": return WHY.get(model, "general reasoning")
    return next((w for k, w in STEP_WHY if k in step.lower()), WHY[model])


def router():
    c = json.load(open(llm.CACHE_FILE)) if llm.CACHE_FILE.exists() else {}
    agg = {}
    for e in c.values():
        k = (e.get("purpose", "?"), e.get("model", "?")); a = agg.setdefault(k, dict(step=k[0], model=k[1], calls=0, tokens_in=0, tokens_out=0))
        a["calls"] += 1; a["tokens_in"] += e.get("tokens_in", 0); a["tokens_out"] += e.get("tokens_out", 0)
    xs = O / "cache" / "media_calls.json"
    for e in (json.load(open(xs)) if xs.exists() else []):
        a = agg.setdefault((e["step"], e["model"]), dict(step=e["step"], model=e["model"], calls=0, tokens_in=0, tokens_out=0)); a["calls"] += 1
        a["tokens_in"] += e.get("tokens_in", 0); a["tokens_out"] += e.get("tokens_out", 0); a["cost_aed"] = a.get("cost_aed", 0) + e.get("cost_aed", 0)
    out = []
    for a in agg.values():
        a.setdefault("cost_aed", llm._cost(a["tokens_in"], a["tokens_out"])); a["why"] = _why(a["step"], a["model"]); out.append(a)
    out.sort(key=lambda a: -a["cost_aed"])
    out.append(dict(step="postings, VAT, reconciliation, covenant maths", model="rules", calls=0, tokens_in=0, tokens_out=0, cost_aed=0, why=WHY["rules"]))
    return dict(steps=out, total_aed=round(sum(a["cost_aed"] for a in out), 2), total_tokens=sum(a["tokens_in"] + a["tokens_out"] for a in out))


# 4. Long-document covenant check -------------------------------------------------------------------------------
def loan():
    txt = (D / "loan" / "facility_agreement.txt").read_text(encoding="utf-8")
    pages = {int(m.group(1)): m.start() for m in re.finditer(r"\[Page (\d+)\]", txt)}
    mock = json.dumps([dict(name="Minimum Liquidity", clause="22.3", page=57, quote="Cash is not, at the close of business on the last Business Day of any week, less than AED 250,000",
                            metric="min_weekly_cash_aed", threshold=250000, frequency="weekly"),
                       dict(name="Debt Service Cover", clause="22.2", page=57, quote="not less than 1.25:1", metric="dscr", threshold=1.25, frequency="quarterly")])
    prompt = ("You are a credit analyst. Read this whole facility agreement (pages are marked [Page n]). List every financial covenant. "
              "Return a JSON list of {name, clause, page, quote (exact words from the text, under 30 words), metric: min_weekly_cash_aed|dscr|other, threshold (number), "
              "frequency, cure (clause and one line if a cure right exists)}.\n\n" + txt)
    cov = _json(llm.ask("long_document_loan_covenants", prompt, mock), [])
    t = json.load(open(O / "treasury_13w.json"))
    for c in cov:
        p = int(c.get("page") or 0); s = pages.get(p, -1); e = pages.get(p + 1, len(txt)); pg = txt[s:e] if s >= 0 else ""
        q = str(c.get("quote", ""))[:60]
        c["grounded"] = bool(q) and (q.lower() in pg.lower()); c["found_on_page"] = next((n for n, st in sorted(pages.items()) if q and q.lower() in txt[st:pages.get(n + 1, len(txt))].lower()), None)
        if c.get("metric") == "min_weekly_cash_aed":
            thr = float(c.get("threshold") or 0); tests = []
            for sc in ("base", "base_with_levers", "downside", "downside_with_levers"):
                cl = t[sc]["closing"]; bad = [i + 1 for i, v in enumerate(cl) if v < thr]
                tests.append(dict(scenario=sc.replace("_", " "), lowest=round(min(cl)), week=cl.index(min(cl)) + 1, breach_weeks=bad, ok=not bad,
                                  headroom=round(min(cl) - thr), ref=f"treasury#{sc}"))
            c["tests"] = tests
        else:
            c["tests"] = [dict(scenario="next test 31 Dec 2026 (quarter date)", ok=None, note="Not due this month; Divi will test on the quarter date.")]
    return dict(pages=len(pages), words=len(txt.split()), file="data/loan/facility_agreement.pdf", covenants=cov)


# 5. Debate scorecard -------------------------------------------------------------------------------------------
def date_claims():
    """Debate text checked by the Verifier's date-fact rule, for the claims counter."""
    d = json.load(open(O / "edge.json")).get("debate", []) if (O / "edge.json").exists() else debate()
    n = sum(1 for r in d for k in ("redteam", "controller", "why") if r.get(k))
    fixes = [dict(flag=r["flag"], **c) for r in d for c in r.get("date_checks", [])]
    return n, fixes


def debate():
    rt = json.load(open(O / "redteam_oct2026.json")); pick = [x for x in rt if x["severity"] == "high"][:4]
    ev = {x["rule"]: [dict(ref=p, text=(sources.resolve(p) or "")[:300]) for p in x["proof"]] for x in pick}
    mock = json.dumps([dict(flag=x["rule"], redteam=f"{x['rule']} on {x['items']}", controller="Possibly legitimate, show support.", winner="redteam",
                            winning_evidence=x["proof"][0], why="Evidence supports the flag.", score_redteam=8, score_controller=4) for x in pick])
    prompt = ("Score a debate between a Red Team agent (says the item is suspicious) and a Controller agent (defends it or asks for support) for each flag below. "
              "Use only the evidence given. For each flag return {flag, redteam: its best argument under 25 words, controller: its best rebuttal under 25 words, "
              "winner: redteam|controller, winning_evidence: one ref copied exactly from the evidence, why: under 20 words, score_redteam 0-10, score_controller 0-10}. "
              "Return a JSON list. Flags and evidence: " + json.dumps(dict(flags=pick, evidence=ev)))
    rounds = _json(llm.ask("debate_scorecard", prompt, mock), [])
    from divi import verify
    for r in rounds:
        r["evidence_text"] = (sources.resolve(str(r.get("winning_evidence", ""))) or "")[:240]; r["grounded"] = bool(r["evidence_text"])
        allev = " ".join(e["text"] for e in ev.get(r.get("flag"), [])) + " " + r["evidence_text"]
        r["date_checks"] = []
        for k in ("redteam", "controller", "why"):
            fixed, errs = verify.check_dates(r.get(k, ""), allev)
            if errs: r["date_checks"].append(dict(field=k, original=r[k], corrected=fixed, errors=errs)); r[k] = fixed
    return rounds


# 6. Control alerts ---------------------------------------------------------------------------------------------
def alerts():
    rt = json.load(open(O / "redteam_oct2026.json")) + run_rules()
    out, seen = [], set()
    for x in rt:
        if x["severity"] != "high" or tuple(x["items"]) in seen: continue
        seen.add(tuple(x["items"]))
        out.append(dict(id=f"{x['rule']}:{'|'.join(x['items'])}", title=x["rule"].replace("owner_rule_", "Your rule: ").replace("_", " ").capitalize(),
                        text=x.get("explanation") or x.get("detail") or "", ref=x["proof"][0], owner_rule=x.get("owner_rule", False)))
    return out


# 7. Missing receipts -------------------------------------------------------------------------------------------
def receipts():
    close = json.load(open(O / "close_oct2026.json")); bank = {b["bank_id"]: b for b in _csv("bank_statement.csv")}
    items = []
    for e in close["entries"]:
        if any(l["acct"] == "6700" for l in e["lines"]):
            bid = next((p.split("#")[1] for p in e["proof"] if p.startswith("bank_statement.csv#")), None); amt = -sum(l["amt"] for l in e["lines"] if l["acct"] == "1000")
            if bid and amt >= 250: items.append(dict(bank_id=bid, date=bank[bid]["date"], payee=bank[bid]["description"], amount=round(amt, 2), ref=f"bank_statement.csv#{bid}"))
    items = sorted(items, key=lambda i: -i["amount"])[:6]
    mock = json.dumps([f"Hi, quick one from Falcon Trading accounts: please share the receipt for AED {i['amount']:,.2f} paid on {i['date']} ({i['payee'].title()}). A photo is fine. Thanks!" for i in items])
    msgs = _json(llm.ask("missing_receipt_whatsapp", "Write one short, friendly WhatsApp message per item asking the staff member who spent it to send the receipt photo. "
                         "Mention amount in AED with commas, date and payee. Under 40 words each, no emojis. Return a JSON list of strings, same order. Items: " + json.dumps(items), mock), [])
    for i, m in zip(items, msgs + [""] * len(items)): i["whatsapp"] = m
    return items


def build():
    r = dict(cogs=cogs_check(), router=router(), loan=loan(), debate=debate(), alerts=alerts(), receipts=receipts(), rules=load_rules(), leaderboard=leaderboard(), schema=SCHEMA)
    json.dump(r, open(O / "edge.json", "w"), indent=1, ensure_ascii=False); return r



def cogs_check():
    """JE-1040 is a deliberate demo case: Oct cost of sales was booked on a 72% cost-ratio estimate, not a stock count.
    Divi rebuilds it from the stock roll-forward and the stock count in inventory.csv."""
    close = json.load(open(O / "close_oct2026.json")); opening = next(float(r["balance_aed"]) for r in csv.DictReader(open(D / "opening_trial_balance.csv")) if r["code"] == "1200")
    purchases = round(sum(float(i["net"]) for i in csv.DictReader(open(D / "invoices.csv")) if i["type"] == "purchase"), 2)
    sales = -close["pnl"]["4000"]["amount"]; booked = close["pnl"]["5000"]["amount"]
    counted = round(sum(float(r["qty"]) * float(r["unit_cost"]) for r in csv.DictReader(open(D / "inventory.csv"))), 2)
    actual = round(opening + purchases - counted, 2); gap = round(actual - booked, 2)
    return dict(je="JE-1040", booked=booked, booked_ratio=round(booked / sales, 3), opening_stock=opening, purchases=purchases, counted_stock=counted,
                book_stock=round(opening + purchases - booked, 2), cogs_from_count=actual, gap=gap, gross_margin_booked=round(1 - booked / sales, 3),
                gross_margin_count=round(1 - actual / sales, 3), proof=["journals.csv#JE-1040", "opening_trial_balance.csv", "inventory.csv"],
                proposal=dict(debit="5000 Cost of Goods Sold", credit="1200 Inventory", amount=gap, status="proposed, needs your approval, not posted"),
                note="Deliberate demo case. The 1.19m is a real month-end estimate (72 percent of sales), not a data error; the stock count shows it is AED " + f"{gap:,.2f} too low.")


if __name__ == "__main__":
    r = build(); print(json.dumps(dict(loan=r["loan"]["covenants"], debate=[(d.get("flag"), d.get("winner"), d.get("grounded")) for d in r["debate"]],
                                       receipts=[i["whatsapp"] for i in r["receipts"]], router=r["router"]["total_aed"]), indent=1)[:4000])
