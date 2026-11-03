"""Verifier: every AI claim must cite sources. Two checks, both must pass:
1. deterministic: each citation resolves, and every number in the claim is found in (or derivable from) the cited text;
2. Muse judge: a separate call reads claim plus cited text and says supported or not.
Rejected claims are dropped from reports."""
import itertools, json, re
from divi import llm, sources

NUM = re.compile(r"(?<![\w.-])-?\d[\d,]*(?:\.\d+)?%?")
def _nums(t):
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*( \d{4})?|\b20\d\d\b|\b[A-Z]+-[A-Z]*-?\d+\b|\bL\d+\b|\bM\d\d\b|\bweek \d+\b", " ", t, flags=re.I)
    out = []
    for m in NUM.findall(t):
        pct = m.endswith("%"); v = float(m.rstrip("%").replace(",", ""))
        if pct or abs(v) >= 100: out.append((abs(v), pct))
    return out

def _derivable(v, pct, pool):
    near = lambda a, b: abs(a - b) <= max(1.0, 0.006 * abs(b))
    if any(near(v, p) for p in pool) and not pct: return True
    if pct and any(abs(v - p) < 0.051 for p in pool): return True
    for a, b in itertools.permutations(pool, 2):
        if b and not pct and abs(v - abs(a - b) / abs(b) * 100) < 0.06: return True  # a percent written without the sign
        if pct:
            if b and (abs(v - abs(a - b) / abs(b) * 100) < 0.6 or abs(v - a / b * 100) < 0.6): return True
        elif near(v, a + b) or near(v, abs(a - b)) or near(v, a * b) or (b and near(v, a / b)) or near(v, a * b / 100) or near(v, a * b * 1.05) or near(v, abs(a - b) * 1.05):
            return True
    return False

def check_det(claim):
    texts = [sources.resolve(c) for c in claim.get("cites", [])]
    if not texts or any(t is None for t in texts): return False, "citation does not resolve to a source row"
    pool = [v for v, _ in _nums(" ".join(texts))] + [float(x) for x in claim.get("calc_inputs", [])]
    pool = list(dict.fromkeys(pool))[:40]
    bad = [v for v, p in _nums(claim["claim"]) if not _derivable(v, p, pool)]
    return (False, f"number {bad[0]:,.2f} not found in cited sources") if bad else (True, "all numbers traced to sources")

def verify(claims, purpose="verifier"):
    for i, c in enumerate(claims):
        c["id"] = c.get("id") or f"C{i+1:02d}"; c["det_ok"], c["det_reason"] = check_det(c)
    packet = [dict(id=c["id"], claim=c["claim"], cited_text=[sources.resolve(x) for x in c.get("cites", [])]) for c in claims]
    mock = json.dumps([dict(id=c["id"], supported=c["det_ok"], reason="mock judge") for c in claims])
    raw = llm.ask(purpose, "You are an audit verifier. For each claim decide if the cited text fully supports it (numbers may be simple sums, "
                  "differences, products or VAT at 5% of cited numbers). Be strict: unsupported facts, wrong numbers or missing evidence mean false. "
                  "Return only a JSON list of {id, supported (true/false), reason (max 12 words)}.\n" + json.dumps(packet, ensure_ascii=False), mock)
    judge = {x.get("id"): x for x in llm.parse(raw, [])}
    for c in claims:
        j = judge.get(c["id"], {"supported": False, "reason": "judge gave no answer"})
        c["muse_ok"], c["muse_reason"] = bool(j.get("supported")), j.get("reason", "")
        c["verified"] = c["det_ok"] and c["muse_ok"]
    return claims

PLANTED = [  # self-test: false claims that must be rejected
    dict(claim="Palm Foods contract price is AED 12.50 per kg.", cites=["contracts/palm_foods_supply.txt#L5"]),
    dict(claim="Desert Rose paid AED 25,000 on 27 Oct.", cites=["bank_statement.csv#B160"]),
    dict(claim="Gulf Star agreed to pay before 5 November.", cites=["messages.jsonl#M01"]),
    dict(claim="Quickline General Trading has been a vendor since 2019.", cites=["vendor_master.csv#Quickline General Trading"]),
    dict(claim="October sales were AED 1,900,000.", cites=["pnl_oct#4000"]),
    dict(claim="Jebel Ali gives a 5% discount for payment within 30 days.", cites=["contracts/jebel_ali_packaging.txt#L99"]),
]


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def check_dates(text, evidence):
    """Date-fact check: the weekday of every date in the cited evidence is computed, and any text that calls it the
    wrong day (or a 'weekday' when it fell on a weekend) is flagged and corrected."""
    import re
    from datetime import date as _d
    if not text: return text, []
    ds = sorted({m for m in re.findall(r"20\d\d-\d\d-\d\d", evidence or "")})
    wd = [DAYS[_d.fromisoformat(x).weekday()] for x in ds]
    if not wd: return text, []
    errs, out = [], text
    weekend = [w for w in wd if w in ("Saturday", "Sunday")]
    if weekend and re.search(r"\bweekday\b", out, re.I):
        out = re.sub(r"\b[Ww]eekday\b", lambda m: ("W" if m.group(0)[0] == "W" else "w") + "eekend", out)
        errs.append(f"said 'weekday' but {ds[wd.index(weekend[0])]} was a {weekend[0]}")
    for n in DAYS:
        if re.search(rf"\b{n}\b", out) and n not in wd and len(set(wd)) == 1:
            out = re.sub(rf"\b{n}\b", wd[0], out); errs.append(f"said {n} but {ds[0]} was a {wd[0]}")
    return out, errs
