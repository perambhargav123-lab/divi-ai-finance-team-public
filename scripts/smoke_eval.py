import json, time, os
from divi import llm
from divi.agents import capture, reconciler
from openai import OpenAI
truth = {t["file"]: t for t in json.load(open("data/docs/ground_truth.json", encoding="utf-8"))}
c = OpenAI(base_url=llm.META_BASE_URL, api_key=os.environ["META_API_KEY"])
orig = c.responses.create; usage = []
def wrap(**k):
    t = time.time(); r = orig(**k); u = r.usage
    usage.append((round(time.time()-t,1), u.input_tokens, u.output_tokens)); return r
c.responses.create = wrap
llm._client = lambda p: (c, llm.META_MODEL)
print("text:", llm.complete("In one line: what is the UAE standard VAT rate?")[:150], usage[-1])
for f in ["doc_02_en.png", "doc_01_ar.png"]:
    try:
        o = capture.capture("data/docs/" + f); t = truth[f]
        ok = {k: str(o["fields"].get(k)).strip() == str(t[k]) or (isinstance(t[k], float) and abs(float(o["fields"].get(k) or 0) - t[k]) < .01) for k in capture.FIELDS}
        print(f, sum(ok.values()), "/8", {k: (o["fields"].get(k), t[k]) for k, v in ok.items() if not v}, o["issues"], usage[-1])
    except Exception as e: print(f, "ERR", repr(e)[:300])
bank = reconciler.load("data/bank_statement.csv"); led = reconciler.load("data/ledger_cash.csv")
r = reconciler.reconcile(bank, led, use_llm=False)
ex = [b for b in bank if b["bank_id"] in {m[0] for m in r["matches"] if m[1] is None}]
p = ("UAE month-end bank rec. For each unmatched bank line return JSON list of {bank_id, category (bank_charge|unrecorded_receipt|duplicate_payment|unexplained_payment), action}. Lines: " + json.dumps(ex))
try: print("recon:", llm.complete(p)[:900], usage[-1])
except Exception as e: print("recon ERR", repr(e)[:300])
print("calls", len(usage), "tokens in/out", sum(u[1] for u in usage), sum(u[2] for u in usage))
