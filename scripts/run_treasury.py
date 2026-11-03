import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from divi import llm, meter
from divi.agents import treasurer
O = Path(__file__).resolve().parents[1] / "out"
close = json.load(open(O / "close_oct2026.json"))
p = treasurer.plan(close["trial_balance"]["1000"]["amount"])
json.dump(p, open(O / "treasury_13w.json", "w"), indent=2)
m = json.load(open(O / "automation_meter.json"))["stages"]
m["treasurer"] = meter.stage(len(p["levers"]) + 4 * 13, 1, len(p["levers"]))  # weekly lines by rules, owners approve levers
meter.write(m, O / "automation_meter.json")
for k in ("base", "downside", "base_with_levers", "downside_with_levers"):
    print(k, p[k]["lowest_week"], p[k]["lowest_cash"], p[k]["closing"][-1], p[k]["released_total"])
print("calls", llm.CALLS["count"])
