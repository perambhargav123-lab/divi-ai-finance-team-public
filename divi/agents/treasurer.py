"""Treasurer agent: 13-week cash forecast (base and downside) and cash release ranking.
Numbers are rule-based; muse-spark-1.3 writes only the narrative and action list."""
import csv, json
from datetime import date, timedelta
from pathlib import Path
from divi import llm

D = Path(__file__).resolve().parents[2] / "data"
START = date(2026, 11, 2)  # week 1 starts Monday 2 Nov 2026
WEEKS = [START + timedelta(weeks=i) for i in range(13)]
# customer payment behaviour: extra days beyond 30-day terms (from October history assumption)
DELAY = {"Al Noor Retail LLC": 5, "Gulf Star Supermarkets": 25, "Emirates Home Supplies": 0, "Desert Rose Trading": 10,
         "Marina Hypermarket": 3, "Sharjah Wholesale Co": 20, "Oasis Hotels FZE": 35, "Blue Creek Catering": 7}
SCEN = {"base": dict(sales=1.0, extra_delay=0, bad_debt=0.0), "downside": dict(sales=0.8, extra_delay=15, bad_debt=0.05)}
LEVERS = [  # amount, weeks the cash lands (share per week), owner, action
    dict(id="L1", name="Collect overdue receivables", amount=140000.0, weeks={2: .3, 3: .3, 4: .4}, owner="Credit controller",
         action="Call Gulf Star (48,000), Oasis Hotels (52,000) and Sharjah Wholesale (40,000); agree dated payment plans; hold new orders over 90 days"),
    dict(id="L2", name="Sell slow-moving stock", amount=80450.0, weeks={4: .25, 5: .25, 6: .25, 7: .25}, owner="Sales manager",
         action="Clearance on Bluetooth speaker X2 and office chairs (over 120 days unsold) at cost to retail customers"),
    dict(id="L3", name="Take early-pay discounts", amount=19550.0, kind="early_pay", weeks={w: 1 / 11 for w in range(3, 14)}, note="annualised; 13-week share shown in forecast", owner="AP lead",
         action="Pay Jebel Ali Packaging, Al Futtaim Logistics Demo and Zenith Electronics inside 10 days for 2% off"),
]

def _csv(n): return list(csv.DictReader(open(D / n, encoding="utf-8")))
def week_of(d):
    i = (d - START).days // 7
    return min(max(i, 0), 12)

def forecast(opening_cash, scenario="base", levers=()):
    s = SCEN[scenario]; inflow = [0.0] * 13; outflow = [0.0] * 13; lines = []
    inv = _csv("invoices.csv")
    for i in inv:
        if i["status"] != "open": continue
        due = date.fromisoformat(i["due"]); t = float(i["total"])
        if i["type"] == "sale":
            d = due + timedelta(days=DELAY.get(i["party"], 0) + s["extra_delay"])
            if d <= WEEKS[-1] + timedelta(days=6):
                inflow[week_of(d)] += t * (1 - s["bad_debt"])
        else:
            outflow[week_of(due)] += t
    sales = sum(float(i["net"]) for i in inv if i["type"] == "sale") * s["sales"]
    cogs_rate = 0.72; wk_sales = sales * 1.05 * 12 / 52
    for w in range(13):  # new business from November
        sale_wk = WEEKS[w] - timedelta(days=30 + 7 + s["extra_delay"])  # invoices raised from 2 Nov
        if sale_wk >= START: inflow[w] += wk_sales * (1 - s["bad_debt"])
        if WEEKS[w] - timedelta(days=45) >= START: outflow[w] += wk_sales * cogs_rate
    # opening balances carried from the October close (sanity fix, day 4)
    ar_cur = 610000 - 140000                       # opening AR not yet overdue, collected weeks 1 to 4
    for w in range(4): inflow[w] += ar_cur / 4 * (1 - s["bad_debt"]) * (0.9 if scenario == "downside" else 1)
    if scenario == "base" and not any(L["id"] == "L1" for L in levers): inflow[11] += 140000 * 0.3  # without action only 30% of overdue AR arrives, late
    for w in range(3): outflow[w] += 455000 / 3     # opening AP (September bills) due now
    outflow[1] += 40000                              # opening accrued expenses settled
    exp = sum(-float(r["amount"]) for r in _csv("ledger_cash.csv") if r["ref"].startswith("EXP"))
    for w in range(13): outflow[w] += exp * 12 / 52  # card and general spend run rate
    for m in (11, 12, 1):
        y = 2027 if m == 1 else 2026
        outflow[week_of(date(y, m, 12))] += 3180.4 + 3500  # DEWA and telecom, insurance and audit accruals are non-cash here
    for m in (11, 12, 1):
        y = 2027 if m == 1 else 2026
        outflow[week_of(date(y, m, 1))] += 35000          # rent
        outflow[week_of(date(y, m, 28))] += 128400        # WPS payroll
        outflow[week_of(date(y, m, 28))] += 25000 * s["sales"]  # monthly VAT return payment
    rel = [0.0] * 13
    for L in levers:
        if L.get("kind") == "early_pay":
            base_amt = L["amount"] * 13 / 52 / 0.02  # 13 weeks of supplier spend on 2/10 terms
            for w, share in L["weeks"].items():
                rel[w - 1] -= base_amt * share * 0.98          # pay at day 10, 2% less
                if w - 1 + 5 < 13: rel[w - 1 + 5] += base_amt * share  # the day-45 payment no longer happens
            continue
        for w, share in L["weeks"].items():
            rel[w - 1] += L["amount"] * share * (1 if scenario == "base" or L["id"] != "L1" else 0.7)
    cash, bal = opening_cash, []
    for w in range(13):
        cash += inflow[w] - outflow[w] + rel[w]; bal.append(round(cash, 2))
    low = min(range(13), key=lambda w: bal[w])
    return dict(scenario=scenario, weeks=[d.isoformat() for d in WEEKS], inflow=[round(x, 2) for x in inflow],
                outflow=[round(x, 2) for x in outflow], released=[round(x, 2) for x in rel], closing=bal,
                lowest_week=low + 1, lowest_cash=bal[low], released_total=round(sum(rel), 2),
                savings=round(sum(L["amount"] * 13 / 52 for L in levers if L.get("kind") == "early_pay"), 2))

def plan(opening_cash):
    out = {k: forecast(opening_cash, k) for k in SCEN}
    out.update({f"{k}_with_levers": forecast(opening_cash, k, LEVERS) for k in SCEN})
    ranked = sorted(LEVERS, key=lambda L: (-L["amount"] / (min(L["weeks"]) or 1)))  # bigger and sooner first
    out["levers"] = [dict(rank=i + 1, **{k: v for k, v in L.items() if k != "weeks"}, first_week=min(L["weeks"]),
                          last_week=max(L["weeks"])) for i, L in enumerate(ranked)]
    summary = {k: dict(lowest_week=v["lowest_week"], lowest_cash=v["lowest_cash"], week13=v["closing"][-1])
               for k, v in out.items() if k != "levers"}
    mock = "Base and downside cash stay manageable; act on overdue receivables first."
    out["narrative"] = llm.complete(
        "You are the treasurer of Falcon Trading LLC (Dubai, AED). In plain words, write a 4 sentence cash outlook and then "
        "a numbered action list (one line each with owner and week) using only these numbers: "
        + json.dumps(dict(summary=summary, levers=out["levers"])), mock_response=mock)
    return out
