"""Run the October 2026 close for Falcon Trading LLC and write outputs to out/."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from divi import llm, meter
from divi.agents import reconciler, controller, redteam
O = Path(__file__).resolve().parents[1] / "out"; O.mkdir(exist_ok=True)
D = Path(__file__).resolve().parents[1] / "data"
bank, led = reconciler.load(D/"bank_statement.csv"), reconciler.load(D/"ledger_cash.csv")
rec = reconciler.reconcile(bank, led)
rt = redteam.scan()
flag_je = {i for x in rt for i in x["items"] if i.startswith("JE-")}
close = controller.build(rec, review_flags=flag_je)
json.dump(close, open(O/"close_oct2026.json", "w"), indent=2)
json.dump(rt, open(O/"redteam_oct2026.json", "w"), indent=2)
docs = len(json.load(open(D/"docs"/"ground_truth.json")))
src = [e["source"] for e in close["entries"]]
m = meter.write({
    "capture": meter.stage(0, docs - 1, 1),  # smoke test: 1 Arabic date needed a fix
    "reconciler": meter.stage(rec["stats"]["rule"], rec["stats"]["llm"], 0),
    "controller": meter.stage(src.count("rule"), 1, src.count("human_review")),
    "red_team": meter.stage(len(rt), 1, len(rt))}, O/"automation_meter.json")
print(json.dumps(dict(net_profit=close["net_profit"], vat=close["vat_payable"], checklist=close["checklist"],
      findings=[x["rule"] for x in rt], meter={k: v["automated_pct"] for k, v in m["stages"].items()} | {"overall": m["overall"]["automated_pct"]},
      calls=llm.CALLS["count"]), indent=1))
