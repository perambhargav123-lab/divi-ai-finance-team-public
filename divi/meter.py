"""Automation-rate meter: share of items handled by rules, model, or a human, per stage."""
import json
def stage(rule, model, human):
    t = rule + model + human or 1
    return dict(rule=rule, model=model, human=human, total=t, automated_pct=round(100 * (rule + model) / t, 1))
def write(stages, path):
    tot = {k: sum(s[k] for s in stages.values()) for k in ("rule", "model", "human")}
    out = dict(stages=stages, overall=stage(**tot))
    json.dump(out, open(path, "w"), indent=2); return out
