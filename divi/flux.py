"""Board flux commentary: October vs September by P&L line, drivers explained, every sentence cited and verified."""
import json
from pathlib import Path
from divi import llm, verify
D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"

def table():
    sep = json.load(open(D / "sept_2026.json")); pnl = json.load(open(O / "close_oct2026.json"))["pnl"]; rows = []
    for k, v in pnl.items():
        s = sep["pnl"].get(k); o = v["amount"]
        if s is None: continue
        rows.append(dict(acct=k, name=v["name"], oct=o, sep=s, change=round(o - s, 2), pct=round((o - s) / abs(s) * 100, 1) if s else None))
    return rows, sep

def run():
    rows, sep = table()
    mock = json.dumps([dict(sentence=f"{r['name']} moved from AED {abs(r['sep']):,.2f} to AED {abs(r['oct']):,.2f}.", cites=[f"pnl_sep#{r['acct']}", f"pnl_oct#{r['acct']}"]) for r in rows[:4]])
    raw = llm.ask("board flux commentary", "Write board variance commentary for Falcon Trading LLC, October 2026 versus September 2026 (AED). "
        "Sales are negative numbers in the ledger; describe them as positive revenue. Explain the material moves (over 5% or AED 5,000) with drivers. "
        "6 to 8 sentences, plain words, no em dashes. Every sentence must cite its sources using only these refs: pnl_oct#<acct>, pnl_sep#<acct>, "
        "drivers_oct#<key>, drivers_sep#<key>. Only use numbers that appear in the data or simple differences of two of them. "
        "Return only a JSON list of {sentence, cites}.\nP&L: " + json.dumps(rows) + "\nDRIVERS SEP: " + json.dumps(sep["drivers"]) + "\nDRIVERS OCT: " + json.dumps(sep["drivers_oct"]), mock)
    sents = llm.parse(raw, [])
    claims = verify.verify([dict(claim=s["sentence"], cites=s.get("cites", [])) for s in sents], "verifier: flux commentary")
    out = dict(table=rows, commentary=claims); json.dump(out, open(O / "flux.json", "w"), indent=1, ensure_ascii=False); return out
