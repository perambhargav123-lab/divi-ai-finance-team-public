"""AI-predicted cash: per-customer payment behaviour (12 months of history plus Muse-read promises, disputes and payment plans)
drives a Monte Carlo 13-week forecast. Output: P10/P50/P90 band and probability cash goes below zero."""
import csv, json, random, statistics as st
from datetime import date, timedelta
from pathlib import Path
from divi.agents import treasurer as T
D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"
def _csv(n): return list(csv.DictReader(open(D / n, encoding="utf-8")))
END = T.WEEKS[-1] + timedelta(days=6)

def behaviour(signals):
    h = {}
    for r in _csv("payment_history.csv"): h.setdefault(r["customer"], []).append(int(r["days_late"]))
    m = {c: dict(history=v, mean=round(st.mean(v), 1), sd=round(st.pstdev(v), 1), signals=[], cites=[f"payment_history.csv#{c}"]) for c, v in h.items()}
    for s in signals:
        c = next((k for k in m if s.get("customer", "").split()[0].lower() in k.lower()), None)
        if c and s.get("verified"): m[c]["signals"].append(dict(kind=s["kind"], pay_after=s.get("pay_after"), amount=s.get("amount_aed"), claim=s["claim"])); m[c]["cites"] += s["cites"]
    return m

# how likely each overdue balance or plan is honoured; actions (collections drafts) raise these
BASE_P = {"Gulf Star Supermarkets": 0.4, "Sharjah Wholesale Co": 0.75, "Oasis Hotels FZE": 0.6}
PLANS = {"Sharjah Wholesale Co": [(date(2026, 11, 20), 20000), (date(2026, 12, 10), 20000)], "Oasis Hotels FZE": [(date(2026, 11, 16), 26000), (date(2026, 12, 15), 26000)]}

def simulate(opening, model, n=2000, p_over=None, ap_shift=None, seed=7):
    p_over = {**BASE_P, **(p_over or {})}; R = random.Random(seed)
    base = T.forecast(opening, "base"); inv = _csv("invoices.csv"); aging = {r["customer"]: r for r in _csv("ar_aging.csv")}
    # remove the deterministic AR and new-business pieces from the base forecast, keep everything else
    det_in = list(base["inflow"]); det_out = list(base["outflow"])
    for i in inv:
        if i["type"] == "sale" and i["status"] == "open":
            d = date.fromisoformat(i["due"]) + timedelta(days=T.DELAY.get(i["party"], 0))
            if d <= END: det_in[T.week_of(d)] -= float(i["total"])
    for w in range(4): det_in[w] -= (610000 - 140000) / 4
    det_in[11] -= 140000 * 0.3
    sales = sum(float(i["net"]) for i in inv if i["type"] == "sale"); wk = sales * 1.05 * 12 / 52; nb_in = [0.0] * 13; nb_out = [0.0] * 13
    for w in range(13):
        if T.WEEKS[w] - timedelta(days=37) >= T.START: nb_in[w] = wk; det_in[w] -= wk
        if T.WEEKS[w] - timedelta(days=45) >= T.START: nb_out[w] = wk * 0.72; det_out[w] -= wk * 0.72
    for (no, days) in (ap_shift or {}).items():
        r = next(i for i in inv if i["invoice_no"] == no); w0 = T.week_of(date.fromisoformat(r["due"]))
        det_out[w0] -= float(r["total"]); d1 = date.fromisoformat(r["due"]) + timedelta(days=days)
        if d1 <= END: det_out[T.week_of(d1)] += float(r["total"])
    paths = []
    for _ in range(n):
        inflow = list(det_in); out = list(det_out); vol = R.gauss(1, 0.10)
        lag = {c: (lambda h: lambda: R.choice(h) + R.gauss(0, 3))(m["history"]) for c, m in model.items()}
        after = {c: max((date.fromisoformat(s["pay_after"]) for s in m["signals"] if s.get("pay_after")), default=None) for c, m in model.items()}
        withheld = {c: sum(float(s["amount"] or 0) for s in m["signals"] if s["kind"] == "dispute") for c, m in model.items()}
        def land(c, due, amt):
            d = due + timedelta(days=round(lag[c]()))
            if after.get(c) and d <= after[c]: d = after[c] + timedelta(days=R.randint(1, 5))
            if d <= END: inflow[T.week_of(max(d, T.START))] += amt
        for i in inv:
            if i["type"] == "sale" and i["status"] == "open":
                amt = float(i["total"]); c = i["party"]
                if withheld.get(c) and i["invoice_no"] in " ".join(s["claim"] for s in model[c]["signals"]) and R.random() < 0.8: amt -= withheld[c]
                land(c, date.fromisoformat(i["due"]), amt)
        for c, a in aging.items():
            land(c, T.START + timedelta(days=R.randint(0, 27)), float(a["current"]))
            over = float(a["d31_60"]) + float(a["d61_90"]) + float(a["d90_plus"])
            if not over: continue
            if c in PLANS:
                for d, amt in PLANS[c]:
                    if R.random() < p_over[c]: inflow[T.week_of(d)] += amt
                    elif d + timedelta(days=28) <= END: inflow[T.week_of(d + timedelta(days=28))] += amt * 0.5
            elif R.random() < p_over.get(c, 0.5):
                inflow[R.randint(1, 12)] += over
        cash = opening; path = []
        for w in range(13):
            f = vol * R.gauss(1, 0.08)
            cash += inflow[w] + nb_in[w] * f - out[w] - nb_out[w] * f; path.append(cash)
        paths.append(path)
    q = lambda w, p: round(sorted(x[w] for x in paths)[int(p * (n - 1))], 2)
    band = dict(p10=[q(w, .1) for w in range(13)], p50=[q(w, .5) for w in range(13)], p90=[q(w, .9) for w in range(13)])
    return dict(weeks=base["weeks"], deterministic=base["closing"], n=n, **band,
                p_negative_by_week=[round(sum(x[w] < 0 for x in paths) / n, 3) for w in range(13)],
                p_negative_any=round(sum(min(x) < 0 for x in paths) / n, 3), p_negative_w6=round(sum(x[5] < 0 for x in paths) / n, 3))

def opening_cash(): t = json.load(open(O / "treasury_13w.json"))["base"]; return round(t["closing"][0] - t["inflow"][0] + t["outflow"][0], 2)
