"""Extra depth: multi currency revaluation, long-context Controller review, native tool calling,
Arabic and crumpled receipt read live, and vision grounding boxes. Writes out/max.json.
Every Muse call goes through llm.ask or llm.ask_tools, so it is cached and traced."""
import csv, json, random
from pathlib import Path
from divi import llm, sources
from divi.agents import capture

D = Path(__file__).resolve().parents[1] / "data"; O = D.parent / "out"; V = O / "vision"


def fx():
    rates = json.load(open(D / "fx_rates.json")); rows = list(csv.DictReader(open(D / "fx_items.csv", encoding="utf-8"))); out = []
    for r in rows:
        fc = float(r["amount_fc"]); booked = round(fc * float(r["booked_rate"]), 2); now = round(fc * rates[r["currency"]], 2)
        diff = round(now - booked, 2); gain = diff if r["kind"] in ("receivable", "bank") else -diff
        out.append(dict(**r, booked_aed=booked, closing_rate=rates[r["currency"]], closing_aed=now, gain_loss=round(gain, 2)))
    net = round(sum(x["gain_loss"] for x in out), 2)
    entry = dict(je="JE-FX-OCT", date=rates["date"], memo="Month-end revaluation of foreign currency balances (IAS 21)",
                 lines=[dict(account="1100/1000/2000 balances", debit=net if net > 0 else 0, credit=-net if net < 0 else 0),
                        dict(account="7900 Unrealised FX gain or loss", debit=-net if net < 0 else 0, credit=net if net > 0 else 0)])
    return dict(items=out, net_gain_loss=net, entry=entry, rates=rates)


def _csvtext(n): return (D / n).read_text(encoding="utf-8")


def long_context():
    books = {n: _csvtext(n) for n in ("invoices.csv", "bank_statement.csv", "journals.csv", "vendor_master.csv", "ap_aging.csv", "ar_aging.csv")}
    size = sum(len(v) for v in books.values())
    prompt = ("You are the Controller of Falcon Trading LLC (fictional, UAE). Below is the whole month of October 2026 books in one context. "
              "Review it end to end like a senior reviewer. Return only JSON: {\"findings\": [{\"title\": str, \"why\": str, \"amount_aed\": number, "
              "\"refs\": [\"file.csv#key\"]}]} with at most 6 findings, most material first. Use refs of the form invoices.csv#<invoice_no>, "
              "bank_statement.csv#<bank_id>, journals.csv#<je>, vendor_master.csv#<vendor>. Only cite rows that exist.\n\n" +
              "\n\n".join(f"=== {k} ===\n{v}" for k, v in books.items()))
    mock = json.dumps({"findings": [{"title": "Payment to new vendor", "why": "Quickline paid 2 days after creation", "amount_aed": 50000, "refs": ["bank_statement.csv#B108"]}]})
    j = llm.parse(llm.ask("controller_long_context_review", prompt, mock), {"findings": []})
    for f in j.get("findings", []):
        f["refs_checked"] = [dict(ref=r, found=sources.resolve(r) is not None) for r in f.get("refs", [])]
        f["grounded"] = bool(f["refs_checked"]) and all(x["found"] for x in f["refs_checked"])
    t = llm.TRACE[-1]
    return dict(chars=size, tokens_in=t["tokens_in"], findings=j.get("findings", []), grounded=sum(f["grounded"] for f in j.get("findings", [])))


TOOLS = [
    dict(type="function", name="get_lowest_cash", description="Lowest weekly cash in the 13-week forecast for a scenario",
         parameters=dict(type="object", properties=dict(scenario=dict(type="string", enum=["base", "downside", "base_with_levers", "downside_with_levers"])), required=["scenario"])),
    dict(type="function", name="get_invoice", description="Look up one invoice by number",
         parameters=dict(type="object", properties=dict(invoice_no=dict(type="string")), required=["invoice_no"])),
    dict(type="function", name="get_vat_payable", description="VAT payable for October from the close", parameters=dict(type="object", properties={})),
]


def _run_tool(name, a):
    t = json.load(open(O / "treasury_13w.json")); c = json.load(open(O / "close_oct2026.json"))
    if name == "get_lowest_cash": s = t[a.get("scenario", "base")]; return dict(aed=s["lowest_cash"], week=s["lowest_week"], ref=f"treasury#{a.get('scenario')}")
    if name == "get_invoice": return dict(row=sources.resolve(f"invoices.csv#{a.get('invoice_no')}"), ref=f"invoices.csv#{a.get('invoice_no')}")
    if name == "get_vat_payable": return dict(aed=c["vat_payable"], ref="close_oct2026.json#vat_payable")
    return dict(error="unknown tool")


def tool_calls():
    qs = ["Can we survive week 6 if customers pay late?", "What does invoice PI-0012 charge Palm Foods?", "How much VAT do we owe for October?"]
    mocks = [[dict(name="get_lowest_cash", arguments=dict(scenario="downside"))], [dict(name="get_invoice", arguments=dict(invoice_no="PI-0012"))],
             [dict(name="get_vat_payable", arguments={})]]
    out = []
    for q, m in zip(qs, mocks):
        calls = llm.ask_tools("cfo_tool_calling", "You are the CFO assistant of Falcon Trading LLC. Call the right tool to answer: " + q, TOOLS, m)
        out.append(dict(question=q, calls=[dict(**c, result=_run_tool(c["name"], c["arguments"])) for c in calls]))
    return out


def crumple(src, dst, seed=7):
    from PIL import Image, ImageDraw, ImageFilter
    R = random.Random(seed); im = Image.open(src).convert("RGB"); w, h = im.size
    sh = Image.new("L", (w, h), 255); d = ImageDraw.Draw(sh)
    for _ in range(14):  # creases
        x0, y0, x1, y1 = R.randint(0, w), 0, R.randint(0, w), h
        if R.random() < .5: x0, y0, x1, y1 = 0, R.randint(0, h), w, R.randint(0, h)
        d.line([(x0, y0), (x1, y1)], fill=R.randint(150, 205), width=R.randint(2, 5))
    sh = sh.filter(ImageFilter.GaussianBlur(5))
    im = Image.composite(im, Image.new("RGB", (w, h), (120, 110, 95)), sh)
    im = im.rotate(-6, expand=True, fillcolor=(205, 200, 190)).filter(ImageFilter.GaussianBlur(0.8))
    tint = Image.new("RGB", im.size, (240, 228, 200)); im = Image.blend(im, tint, 0.18)
    im.save(dst); return dst


def vision():
    V.mkdir(parents=True, exist_ok=True); gt = json.load(open(D / "docs" / "ground_truth.json"))
    gt = {g["file"]: g for g in (gt if isinstance(gt, list) else gt.values())}
    out = []
    for f in ("doc_06_ar.png", "doc_11_ar.png"):
        p = crumple(D / "docs" / f, V / f"crumpled_{f}")
        d = capture.normalise(capture.parse_json(llm.ask("capture_crumpled_receipt", capture.PROMPT, json.dumps(gt[f]), image=str(p))))
        t = gt[f]; match = {k: str(d.get(k, "")).strip().lower() == str(t.get(k)).strip().lower() if k not in ("net", "vat", "total")
                            else abs(float(d.get(k) or 0) - float(t[k])) < 0.02 for k in capture.FIELDS}
        out.append(dict(file=f"vision/crumpled_{f}", source=f"docs/{f}", lang=t.get("lang"), fields=d, matched=sum(match.values()), of=len(match), match=match))
    # grounding: boxes for key fields on one invoice
    f = "doc_02_en.png"; from PIL import Image, ImageDraw
    im = Image.open(D / "docs" / f).convert("RGB"); w, h = im.size
    prompt = (f"This invoice image is {w} by {h} pixels. Find where these fields are printed: invoice_no, date, trn, net, vat, total. "
              "Return only JSON {\"boxes\": {field: {\"value\": str, \"box\": [x0, y0, x1, y1]}}} with box coordinates normalised 0 to 1000 "
              "relative to the image width and height, tight around the printed value.")
    j = llm.parse(llm.ask("vision_grounding_boxes", prompt, json.dumps({"boxes": {}}), image=str(D / "docs" / f)), {"boxes": {}})
    dr = ImageDraw.Draw(im); boxes = {}
    for k, v in (j.get("boxes") or {}).items():
        try:
            x0, y0, x1, y1 = [float(c) for c in v["box"]]; bx = [x0 * w / 1000, y0 * h / 1000, x1 * w / 1000, y1 * h / 1000]
            dr.rectangle(bx, outline=(15, 118, 110), width=3); dr.text((bx[0], max(0, bx[1] - 12)), k, fill=(15, 118, 110)); boxes[k] = dict(value=v.get("value"), box=[round(c) for c in bx])
        except (KeyError, TypeError, ValueError): pass
    im.save(V / "grounded_doc_02.png")
    return dict(crumpled=out, grounding=dict(file="vision/grounded_doc_02.png", source=f"docs/{f}", boxes=boxes))


def run():
    n0 = len(llm.TRACE)
    res = dict(fx=fx(), long_context=long_context(), tool_calls=tool_calls(), vision=vision())
    res["trace"] = llm.TRACE[n0:]; json.dump(res, open(O / "max.json", "w"), indent=1, ensure_ascii=False); return res


if __name__ == "__main__":
    r = run()
    print("fx net", r["fx"]["net_gain_loss"]); print("long ctx", r["long_context"]["tokens_in"], "tokens,", len(r["long_context"]["findings"]), "findings,", r["long_context"]["grounded"], "grounded")
    print("tools", [[c["name"] for c in t["calls"]] for t in r["tool_calls"]])
    print("vision", [(v["file"], v["matched"], v["of"]) for v in r["vision"]["crumpled"]], list(r["vision"]["grounding"]["boxes"]))
    print("cost AED", round(sum(t["cost_aed"] for t in r["trace"]), 3), [t["source"][:30] for t in r["trace"]])
