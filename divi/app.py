"""Divi dashboard: uvicorn divi.app:app --port 8000"""
import csv, json, shutil, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from divi import live, llm, lender, byob
from fastapi import Form
from divi import voice

R = Path(__file__).resolve().parents[1]; O, D = R / "out", R / "data"
app = FastAPI(title="Divi")
def tidy(x):
    from .llm import clean
    if isinstance(x, str): return clean(x)
    if isinstance(x, list): return [tidy(v) for v in x]
    if isinstance(x, dict): return {k: tidy(v) for k, v in x.items()}
    return x


def j(n): return tidy(json.load(open(O / n)))
RULES = {"rule:accrual_audit_fee": "Audit fee AED 24,000 a year accrued one twelfth per month",
         "rule:prepayment_insurance": "Insurance AED 18,000 a year released one twelfth per month",
         "rule:bank_charge": "Bank line marked CHARGE, split net and 5% VAT", "rule:rule": "Matched by reference or amount within 5 days",
         "rule:unrecorded_receipt": "Receipt with no ledger entry, held in Unidentified Receipts", "rule:duplicate_payment": "Same payee and amount paid twice"}

@app.get("/favicon.ico")
def favicon(): return FileResponse(Path(__file__).parent / "web" / "favicon.svg", media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
def home(): return (Path(__file__).parent / "web" / "index.html").read_text()

from fastapi.staticfiles import StaticFiles
from divi import sources as _src, learning as _learn
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "web")), name="static")

@app.get("/api/live_events")
def live_events(): return j("cache/live_run.json")

@app.get("/api/insights")
def insights():
    r = j("insights.json")
    try:  # debate text goes through the Verifier's date-fact check too
        from divi import edge
        n, fixes = edge.date_claims(); p = r["proof"]
        p["total"] += n; p["verified"] += n - len(fixes); p["rejected"] += len(fixes); p["date_fixes"] = fixes
        p["rejected_items"] = p["rejected_items"] + [dict(claim=f"Debate ({f['flag'].replace('_', ' ')}): {f['original']}",
                                                          why=f"Date-fact check: {'; '.join(f['errors'])}. Shown corrected: {f['corrected']}") for f in fixes]
    except Exception:
        pass
    return tidy(r)

@app.get("/api/learning")
def learning_state(): return _learn.state()

@app.get("/api/cite/{ref:path}")
def cite(ref: str): return {"ref": ref, "text": _src.resolve(ref)}

@app.get("/api/data")
def data():
    c = j("close_oct2026.json")
    return dict(pnl=c["pnl"], bs=c["balance_sheet"], net_profit=c["net_profit"], vat=c["vat_payable"], checklist=c["checklist"],
                commentary=c["commentary"], redteam=j("redteam_oct2026.json"), meter=j("automation_meter.json"), treasury=j("treasury_13w.json"),
                entries={e["id"]: e for e in c["entries"]})

@app.get("/api/proof/{ref:path}")
def proof(ref: str):
    if ref.startswith("rule:"): return {"type": "rule", "ref": ref, "text": RULES.get(ref, ref)}
    f, _, key = ref.partition("#"); rows = list(csv.DictReader(open(D / f, encoding="utf-8")))
    k = {"invoices.csv": "invoice_no", "bank_statement.csv": "bank_id", "ledger_cash.csv": "ref", "journals.csv": "je"}.get(f)
    row = next((r for r in rows if k and r[k] == key), rows if f.startswith("opening") else None)
    img = next((t["file"] for t in json.load(open(D / "docs" / "ground_truth.json")) if t["invoice_no"] == key), None)
    return {"type": "source", "ref": ref, "row": row, "image": f"/docs/{img}" if img else None}

@app.get("/docs/{name}")
def doc(name: str): return FileResponse(D / "docs" / Path(name).name)

@app.post("/api/voice")
async def ask_voice(audio: UploadFile = File(...)):
    tmp = tempfile.mktemp(suffix=Path(audio.filename or "q.wav").suffix)
    with open(tmp, "wb") as f: shutil.copyfileobj(audio.file, f)
    q = voice.transcribe(tmp)
    return JSONResponse(dict(question=q, **voice.ask(q)), headers={"Content-Type": "application/json; charset=utf-8"})


@app.get("/api/close/stream")
def close_stream(replay: int = 0, speed: float = 1.0):
    """Server-sent events. Live: every agent step calls Muse Spark Open on Baseten and its reasoning streams into the feed.
    Any failed or slow call falls back to the recorded answer, so the numbers never change and the demo never stops.
    Without a key (or ?replay=1) it replays a recorded real run."""
    if replay or not (llm.live_ready() or not llm.is_mock()):
        src = live.replay(speed)
        def gen0():
            yield "data: " + json.dumps(dict(agent="divi", name="Divi", color="#0f766e", kind="powered", text="",
                                             data=dict(stats=dict(calls=0, tokens=0), live=False))) + "\n\n"
            for e in src:
                yield "data: " + json.dumps(tidy(e), ensure_ascii=False) + "\n\n"
        return StreamingResponse(gen0(), media_type="text/event-stream")
    import queue, threading
    q = queue.Queue(); base = llm.live_ready()
    def think(agent, text):
        nm, col = live.AGENTS.get(agent, live.AGENTS["divi"])
        q.put(dict(agent=agent, name=nm, color=col, kind="thinking", text=text, data=dict(stats=llm.live_stats())))
    def work():
        if base: llm.live_reset(); llm.ON_THINK.append(think)
        try:
            for e in live.run():
                if base: e.setdefault("data", {})["stats"] = llm.live_stats()
                q.put(e)
        except Exception as ex:  # last resort: finish the story from the recording
            import traceback; traceback.print_exc()
            q.put(dict(agent="divi", name="Divi", color="#0f766e", kind="say", text=f"Live run interrupted ({type(ex).__name__}). Finishing from the recorded run.", data={}))
            for e in live.replay(4.0): q.put(e)
        finally:
            if base: llm.LIVE["on"] = False; llm.ON_THINK.clear()
            q.put(None)
    threading.Thread(target=work, daemon=True).start()
    def gen():
        yield "data: " + json.dumps(dict(agent="divi", name="Divi", color="#0f766e", kind="powered", text="",
                                         data=dict(stats=llm.live_stats(), live=base)), ensure_ascii=False) + "\n\n"
        while True:
            e = q.get()
            if e is None: break
            yield "data: " + json.dumps(tidy(e), ensure_ascii=False) + "\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

class Decision(BaseModel):
    flag: str
    decision: str
    note: str = ""

@app.post("/api/decision")
def decide(d: Decision):
    p = O / "decisions.json"; cur = json.load(open(p)) if p.exists() else []
    import datetime as _dt; cur.append({**d.model_dump(), 'time': _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}); json.dump(cur, open(p, "w"), indent=1); return {"ok": True, "count": len(cur)}


class Q(BaseModel):
    q: str

@app.post("/api/chat")
def chat(q: Q):
    r = voice.ask(q.q)
    if any(w in q.q.lower() for w in ("survive", "week 6", "downside", "credit", "loan", "facility", "funding", "cash")) or "نقد" in q.q:
        r["actions"] = [{"label": "Run downside case and draft AED credit line + proof pack", "js": "credit()"}]
    return tidy(r)

@app.post("/api/credit_line")
def credit_line(): return tidy(lender.pack())

@app.get("/out/lender_proof_pack.pdf")
def pdf(): return FileResponse(O / "lender_proof_pack.pdf", media_type="application/pdf")

@app.post("/api/byob")
async def bring_books(bank: UploadFile = File(...), opening_cash: float = Form(None)):
    return byob.run((await bank.read()).decode("utf-8-sig", errors="replace"), opening_cash)


@app.get("/api/max")
def max_depth(): return j("max.json")


@app.get("/vision/{name}")
def vision_img(name: str): return FileResponse(O / "vision" / Path(name).name)


@app.get("/api/sample.csv")
def sample_csv(): return FileResponse(D / "sample_byob_bank.csv", media_type="text/csv", filename="divi_sample_bank.csv")


@app.post("/api/reset")
def reset():
    """Try it: clear the visitor's decisions so the demo starts fresh. Books and recorded answers are untouched."""
    json.dump([], open(O / "decisions.json", "w")); return {"ok": True}


@app.get("/api/audit")
def audit():
    """Audit trail: every agent action, challenge and approval with time."""
    ev = j("cache/live_run.json"); ev = ev if isinstance(ev, list) else ev.get("events", [])
    rows = [dict(t=e.get("t"), agent=e.get("name", e.get("agent")), kind=e.get("kind"), text=e.get("text")) for e in ev]
    p = O / "decisions.json"; dec = json.load(open(p)) if p.exists() else []
    return tidy(dict(events=rows, decisions=dec))


@app.get("/api/scoreboard")
def scoreboard():
    I = j("insights.json"); b = I["benchmark"]; t = I["trace"]; drafts = I["cash"]["drafts"]
    m = json.load(open(O / "close_oct2026.json")).get("meter", {})
    return dict(hours_saved=40, automation=0.991, fraud_caught=f"{b['detected']}/{b['injected']}", aed_found=round(sum(d["impact"]["p50_delta"] for d in drafts)),
                cost_per_close=t["cost_aed"], note="Hours saved is an estimate: 40 manual hours for a 150-invoice month.")


# ---- edge: owner controls, Beat the Controller, router, covenant check, debate scorecard, alerts, receipts ----
from divi import edge as _edge


@app.get("/api/edge")
def edge_all():
    r = j("edge.json"); r["rules"] = _edge.load_rules(); r["leaderboard"] = _edge.leaderboard(); r["alerts"] = _edge.alerts(); r["router"] = _edge.router()
    return tidy(r)


class RuleIn(BaseModel):
    text: str


@app.post("/api/rules")
def add_rule(r: RuleIn):
    if not r.text.strip(): return {"error": "Type a rule first."}
    return tidy(_edge.add_rule(r.text.strip()[:300]))


@app.post("/api/rules/clear")
def clear_rules():
    if _edge.RULES.exists(): _edge.RULES.unlink()
    return {"ok": True}


class Sneak(BaseModel):
    name: str = "anonymous"
    bank: list = []
    vendors: list = []
    invoices: list = []
    journals: list = []


@app.post("/api/challenge")
def sneak(s: Sneak):
    try:
        return tidy(_edge.challenge(s.name, s.bank[:5], s.vendors[:3], s.invoices[:5], s.journals[:5]))
    except Exception as ex:
        return {"error": f"Could not read your rows: {type(ex).__name__}. Check dates are YYYY-MM-DD and amounts are numbers."}


@app.get("/challenge")
def challenge_page(): return FileResponse(Path(__file__).parent / "web" / "challenge.html")


@app.get("/loan/facility_agreement.pdf")
def loan_pdf(): return FileResponse(D / "loan" / "facility_agreement.pdf", media_type="application/pdf")


@app.get("/api/extras")
def extras_all(): return j("extras.json")


@app.get("/media/{kind}/{name}")
def media(kind: str, name: str):
    if kind not in ("sam", "art", "exports"): return {"error": "not found"}
    p = O / kind / Path(name).name
    return FileResponse(p, filename=p.name if kind == "exports" else None)


@app.post("/api/challenge/learn")
def learn():
    """Owner approves the rule the learning loop proposed; the last sneak is re-run against it."""
    try:
        return tidy(_edge.learn_approve())
    except FileNotFoundError:
        return {"error": "Run a challenge first."}


@app.post("/api/challenge/forget")
def forget():
    """Remove the learned rule so the challenge can be demoed again."""
    cur = [r for r in _edge.load_rules() if r["name"] != _edge.LEARN["name"]]; json.dump(cur, open(_edge.RULES, "w"), indent=1); return {"ok": True}


# ---- auditor loop and cash counter (29 to 30 Oct) ----
from divi import auditor as _auditor, cashcounter as _cash


@app.get("/api/cycle")
def cycle_all():
    from divi import cycle
    return tidy(cycle.run())

@app.get("/api/auditor")
def auditor_loop(): return tidy(_auditor.run())


@app.get("/api/cash_counter")
def cash_counter(): return tidy(_cash.run())

# ---- voice 'ask Divi' on the main path (1 Nov) ----
@app.get("/api/voice_week4")
def voice_week4(live: int = 0):
    """Plays the recorded question and answer. With META_API_KEY the audio is transcribed live by Muse Voice Transcribe;
    with ?live=1 and a Baseten key the answer is regenerated live. Any failure falls back to the recording."""
    try:
        r = voice.week4(live=bool(live))
        if not llm.is_mock():
            try: r = {**r, "transcript": voice.transcribe(voice.DEMO_AUDIO, r["question"]), "transcript_source": "live, muse-voice-transcribe-1.0"}
            except Exception: pass
    except Exception as ex:
        r = json.load(open(voice.DEMO, encoding="utf-8")); r["fallback"] = type(ex).__name__
    return tidy(r)

@app.get("/audio/q_week4.mp3")
def week4_audio():
    from fastapi.responses import FileResponse
    return FileResponse(D / "audio" / "q_week4.mp3", media_type="audio/mpeg")

# ---- close policy and decision log (2 Nov) ----
from divi import decision_log as _dlog
@app.get("/api/policy")
def close_policy(): return tidy(_dlog.policy())

@app.get("/api/decision_log")
def decision_log(): return tidy(_dlog.run())
