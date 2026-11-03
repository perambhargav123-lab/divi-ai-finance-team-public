"""Extras: SAM 3.1 receipt cut-out from a phone-style photo, live UAE tax rules via Muse web search,
Xero and Zoho Books journal exports, and Muse Image thumbnail art. Results saved to out/extras.json."""
import base64, csv, json, os, re, time
from pathlib import Path
import requests
from divi import llm
from divi.agents import capture

ROOT = Path(__file__).resolve().parents[1]; D = ROOT / "data"; O = ROOT / "out"; S = O / "sam"; MEDIA = O / "cache" / "media_calls.json"
API = "https://api.meta.ai/v1"


def _h(): return {"Authorization": "Bearer " + os.environ["META_API_KEY"]}
def _log(step, model, **kw):
    cur = json.load(open(MEDIA)) if MEDIA.exists() else []
    cur = [c for c in cur if c["step"] != step] + [dict(step=step, model=model, **kw)]; MEDIA.parent.mkdir(parents=True, exist_ok=True); json.dump(cur, open(MEDIA, "w"), indent=1)


def sam_cutout(photo=S / "desk_photo.png", concept="receipt"):
    """SAM 3.1 finds the receipt in a cluttered desk photo; we crop to its box, then Muse reads only the cut-out."""
    from PIL import Image, ImageDraw
    raw = S / "sam_response.json"
    if not raw.exists():
        b = base64.b64encode(open(photo, "rb").read()).decode(); t0 = time.time()
        r = requests.post(f"{API}/responses", headers=_h(), timeout=120, json={"model": "sam-3.1", "input": [{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": concept}, {"type": "input_image", "image_url": "data:image/png;base64," + b}]}]})
        r.raise_for_status(); j = r.json(); j["_latency_s"] = round(time.time() - t0, 1); json.dump(j, open(raw, "w"))
    j = json.load(open(raw)); txt = j["output"][0]["content"][0]["text"]
    boxes = [dict((kv.split("=") for kv in m.split(";"))) for m in re.findall(r"<\|box;([^|]*)\|>", txt)]
    _log("receipt cut-out from photo", "sam-3.1", calls=1, tokens_in=0, tokens_out=0, cost_aed=0)
    im = Image.open(photo).convert("RGB"); b = boxes[0]; x1, y1, x2, y2 = (int(b[k]) for k in ("x1", "y1", "x2", "y2"))
    pad = 6; crop = im.crop((max(0, x1 - pad), max(0, y1 - pad), x2 + pad, y2 + pad)); crop.save(S / "receipt_cutout.png")
    an = im.copy(); dr = ImageDraw.Draw(an); dr.rectangle([x1, y1, x2, y2], outline=(15, 118, 110), width=6); dr.text((x1 + 8, y1 - 22), f"SAM 3.1: {concept}", fill=(255, 255, 255))
    an.save(S / "photo_with_sam_box.png")
    gt = {g["file"]: g for g in (lambda g: g if isinstance(g, list) else g.values())(json.load(open(D / "docs" / "ground_truth.json")))}["doc_06_ar.png"]
    d = capture.normalise(capture.parse_json(llm.ask("capture_receipt_after_sam_cutout", capture.PROMPT, json.dumps(gt), image=str(S / "receipt_cutout.png"))))
    match = {k: (abs(float(d.get(k) or 0) - float(gt[k])) < 0.02 if k in ("net", "vat", "total") else str(d.get(k, "")).strip().lower() == str(gt.get(k)).strip().lower())
             for k in capture.FIELDS}
    w, h = crop.size
    prompt = (f"This receipt image is {w} by {h} pixels. Find where these fields are printed: vendor, trn, invoice_no, date, net, vat, total. "
              "Return only JSON {\"boxes\": {field: {\"value\": str, \"box\": [x0, y0, x1, y1]}}} with coordinates normalised 0 to 1000, tight around the printed value.")
    g = llm.parse(llm.ask("receipt_field_boxes_after_sam", prompt, json.dumps({"boxes": {}}), image=str(S / "receipt_cutout.png")), {"boxes": {}})
    gi = crop.copy(); dr = ImageDraw.Draw(gi); fb = {}
    for k, v in (g.get("boxes") or {}).items():
        try:
            a0, b0, a1, b1 = [float(c) for c in v["box"]]; bx = [a0 * w / 1000, b0 * h / 1000, a1 * w / 1000, b1 * h / 1000]
            dr.rectangle(bx, outline=(217, 119, 6), width=2); dr.text((bx[0], max(0, bx[1] - 11)), k, fill=(217, 119, 6)); fb[k] = v.get("value")
        except (KeyError, TypeError, ValueError): pass
    gi.save(S / "receipt_fields_boxed.png")
    return dict(concept=concept, sam_box=[x1, y1, x2, y2], photo_size=[im.width, im.height], matches=len(boxes), masks_returned="mask;" in txt,
                latency_s=j.get("_latency_s"), fields=d, matched=sum(match.values()), of=len(match), match=match, field_boxes=fb,
                images=dict(photo="sam/photo_with_sam_box.png", cutout="sam/receipt_cutout.png", boxed="sam/receipt_fields_boxed.png"),
                note="Scene is a synthetic desk photo built from a fictional receipt. SAM 3.1 returns a box and a mask; Divi crops by the box.")


def tax_rules():
    """Treasurer checks the current UAE VAT and corporate tax rules with Muse's built-in web search, then compares them to the rates Divi uses."""
    p = O / "cache" / "tax_web.json"
    if not p.exists():
        t0 = time.time()
        r = requests.post(f"{API}/responses", headers=_h(), timeout=180, json={"model": "muse-spark-1.3", "tools": [{"type": "web_search"}], "input":
            "Using official UAE government sources (tax.gov.ae, mof.gov.ae, u.ae), state: 1) the standard VAT rate, 2) the corporate tax rate and the taxable income "
            "threshold below which the rate is 0 percent, 3) the VAT return filing deadline after a tax period ends. Return JSON {vat_rate_pct, ct_rate_pct, "
            "ct_zero_band_aed, vat_return_due_days, sources:[{url, supports}]}. Only cite pages you opened or found."})
        r.raise_for_status(); j = r.json(); j["_latency_s"] = round(time.time() - t0, 1); json.dump(j, open(p, "w"))
    j = json.load(open(p)); text = "".join(c.get("text", "") for o in j["output"] if o["type"] == "message" for c in o["content"])
    queries = [o["action"].get("query") or o["action"].get("url") for o in j["output"] if o["type"] == "web_search_call"]
    ann = [a.get("url") for o in j["output"] if o["type"] == "message" for c in o["content"] for a in c.get("annotations", []) if a.get("url")]
    u = j.get("usage", {}); _log("treasurer web search: UAE tax rules", "muse-spark-1.3", calls=1, tokens_in=u.get("input_tokens", 0), tokens_out=u.get("output_tokens", 0),
                                 cost_aed=llm._cost(u.get("input_tokens", 0), u.get("output_tokens", 0)))
    found = llm.parse(text[text.rfind("{", 0, text.find("vat_rate_pct")):], {})
    used = dict(vat_rate_pct=5, ct_rate_pct=9, ct_zero_band_aed=375000, vat_return_due_days=28)
    checks = [dict(rule=k.replace("_", " "), divi_uses=v, web_says=found.get(k), agrees=str(found.get(k)).replace(",", "").split(".")[0] == str(v)) for k, v in used.items()]
    return dict(checks=checks, searches=queries, sources=found.get("sources", []) or [{"url": a} for a in ann], latency_s=j.get("_latency_s"))


def exports():
    """Xero and Zoho Books manual-journal CSVs for the October close (files only, nothing is uploaded)."""
    close = json.load(open(O / "close_oct2026.json")); coa = {r["code"]: r["name"] for r in csv.DictReader(open(D / "chart_of_accounts.csv"))}
    E = O / "exports"; E.mkdir(exist_ok=True); n = 0
    with open(E / "xero_manual_journals.csv", "w", newline="") as fx, open(E / "zoho_books_journals.csv", "w", newline="") as fz:
        x = csv.writer(fx); z = csv.writer(fz)
        x.writerow(["*Narration", "*Date", "Description", "*AccountCode", "*TaxRate", "*Amount", "TrackingName1", "TrackingOption1"])
        z.writerow(["Journal Date", "Reference Number", "Journal Notes", "Account", "Description", "Debit", "Credit", "Currency"])
        for e in close["entries"]:
            if any(l["acct"] == "OB" for l in e["lines"]): continue
            for l in e["lines"]:
                x.writerow([f"{e['id']} {e['memo']}", "31/10/2026", e["memo"], l["acct"], "No VAT", f"{l['amt']:.2f}", "", ""])
                z.writerow(["2026-10-31", e["id"], e["memo"], coa.get(l["acct"], l["acct"]), e["memo"], f"{l['amt']:.2f}" if l["amt"] > 0 else "", f"{-l['amt']:.2f}" if l["amt"] < 0 else "", "AED"])
            n += 1
    return dict(journals=n, files=["exports/xero_manual_journals.csv", "exports/zoho_books_journals.csv"],
                note="Xero manual journal import (signed amounts, debits positive) and Zoho Books journal import (debit and credit columns). Opening balances excluded. VAT lines map to the VAT accounts, so tax rate is No VAT on each line.")


def art():
    """Muse Image: video thumbnail and end card. Abstract finance art, no people, no logos."""
    A = O / "art"; A.mkdir(exist_ok=True); res = {}
    jobs = {"thumbnail": "Clean light-theme abstract illustration for a finance app video thumbnail: soft teal and white, a rising cash-flow line chart, a stack of paper invoices with a green check mark, Dubai skyline silhouette faint in the background, no people, no text, no logos, 16:9.",
            "end_card": "Minimal light background end card art: soft teal gradient, subtle geometric grid, a single elegant check mark made of light, generous empty space in the centre for a title, no people, no text, no logos, 16:9."}
    for k, prompt in jobs.items():
        f = A / f"{k}.png"
        if not f.exists():
            t0 = time.time()
            r = requests.post(f"{API}/images/generations", headers=_h(), timeout=180, json={"model": "muse-image-1.0", "prompt": prompt, "n": 1})
            r.raise_for_status(); d = r.json()["data"][0]
            f.write_bytes(base64.b64decode(d["b64_json"]) if d.get("b64_json") else requests.get(d["url"], timeout=60).content)
            _log(f"{k} art", "muse-image-1.0", calls=1, tokens_in=0, tokens_out=0, cost_aed=0, latency_s=round(time.time() - t0, 1))
        res[k] = dict(file=f"art/{k}.png", prompt=prompt)
    return res


def run():
    r = {}
    for k, fn in (("sam", sam_cutout), ("tax", tax_rules), ("exports", exports), ("art", art)):
        try: r[k] = fn()
        except Exception as ex: r[k] = dict(error=f"{type(ex).__name__}: {str(ex)[:160]}")
    json.dump(r, open(O / "extras.json", "w"), indent=1, ensure_ascii=False); return r


if __name__ == "__main__":
    r = run(); print(json.dumps({k: (v if k != "exports" else v.get("journals")) for k, v in r.items()}, indent=1, ensure_ascii=False)[:5000])
