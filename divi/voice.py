"""Voice CFO: audio question (English or Arabic) to transcript (muse-voice-transcribe-1.0) to answer from the books."""
import json, os, subprocess, tempfile
from pathlib import Path
from divi import llm

O = Path(__file__).resolve().parents[1] / "out"
ASR_URL = llm.META_BASE_URL + "/asr/transcribe"

def to_wav(path):
    if str(path).lower().endswith(".wav"): return str(path)
    out = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-ar", "16000", "-ac", "1", out], check=True)
    return out

def transcribe(path, mock_text="What is our net profit for October?"):
    llm.CALLS["count"] += 1
    if llm.is_mock(): return mock_text
    import requests
    with open(to_wav(path), "rb") as a:
        r = requests.post(ASR_URL, headers={"Authorization": f"Bearer {llm._key('META_API_KEY')}", "Accept": "text/plain"},
                          files={"request": (None, json.dumps({"model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV",
                                                                "mode": "PUSH_TO_TALK"}), "application/json"),
                                 "audio": ("q.wav", a, "audio/wav")}, timeout=120)
    r.raise_for_status(); return r.content.decode("utf-8").strip()

def facts():
    c = json.load(open(O / "close_oct2026.json")); t = json.load(open(O / "treasury_13w.json"))
    f = {"net_profit_oct": [c["net_profit"], "close_oct2026.json#net_profit"], "vat_payable_oct": [c["vat_payable"], "rule:vat_control 2100+1300"],
         "cash_31_oct": [c["trial_balance"]["1000"]["amount"], "tb#1000"]}
    for k, v in c["pnl"].items(): f[f"pnl_{v['name']}"] = [v["amount"], f"tb#{k}"]
    for k in ("base", "downside", "base_with_levers", "downside_with_levers"):
        f[f"lowest_cash_{k}"] = [t[k]["lowest_cash"], f"treasury#{k}:week{t[k]['lowest_week']}"]
    for k in ("downside", "downside_with_levers"):
        f[f"weekly_cash_{k}"] = [t[k]["closing"], f"treasury#{k}"]
    f["levers"] = [[dict(name=L["name"], aed=L["amount"], owner=L["owner"], weeks=f"{L['first_week']}-{L['last_week']}") for L in t["levers"]], "treasury#levers"]
    f["credit_line_needed"] = [credit_need(t), "treasury#downside lowest week + 1% buffer"]
    f["red_team_findings"] = [[x["rule"] for x in json.load(open(O / "redteam_oct2026.json"))], "redteam_oct2026.json"]
    return f

def credit_need(t):
    import math
    low = t["downside"]["lowest_cash"]
    return 0 if low >= 0 else int(math.ceil(-low * 1.01 / 5000) * 5000)

def ask(question):
    mock = json.dumps({"answer": "Net profit for October is AED %s." % facts()["net_profit_oct"][0], "proof": ["close_oct2026.json#net_profit"]})
    txt = llm.complete("You are the CFO of Falcon Trading LLC. Answer the question in the same language it was asked, in 1 to 3 "
                       "plain sentences with amounts in AED and thousands separators; "
                       "using only these facts (value, proof id). Return JSON {\"answer\": str, \"proof\": [proof ids used]}. "
                       f"Facts: {json.dumps(facts(), ensure_ascii=False)}\nQuestion: {question}", mock_response=mock)
    try: return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    except ValueError: return {"answer": txt, "proof": []}


DEMO = O / "cache" / "voice_week4.json"
DEMO_AUDIO = Path(__file__).resolve().parents[1] / "data" / "audio" / "q_week4.wav"

def week4_facts():
    t = json.load(open(O / "treasury_13w.json")); m = json.load(open(O / "insights.json"))["cash"]["with_actions"]
    return {"base_week4": [t["base"]["closing"][3], "treasury#base:week4"],
            "downside_week4": [t["downside"]["closing"][3], "treasury#downside:week4"],
            "downside_with_levers_week4": [t["downside_with_levers"]["closing"][3], "treasury#downside_with_levers:week4"],
            "median_week4_with_drafts": [m["p50"][3], "cash#with_actions:p50:week4"],
            "chance_negative_week4_with_drafts": [m["p_negative_by_week"][3], "cash#with_actions:p_negative:week4"],
            "chance_negative_any_week_with_drafts": [m["p_negative_any"], "cash#with_actions:p_negative_any"],
            "credit_line_needed": [credit_need(t), "treasury#downside lowest week + 1% buffer"]}

def week4(live=False):
    """The main-path voice question. Replays a recorded real answer (Muse Spark Open on Baseten) unless live=True."""
    if DEMO.exists() and not live: return json.load(open(DEMO, encoding="utf-8"))
    f = week4_facts()
    mock = json.dumps({"answer": f"Yes in the base case: week 4 closes at AED {f['base_week4'][0]:,.0f}. With the six drafts the chance of going below zero that week is {f['chance_negative_week4_with_drafts'][0]:.1%}.", "proof": ["treasury#base:week4", "cash#with_actions:p_negative:week4"]})
    prompt = ("You are the CFO of Falcon Trading LLC, talking to the owner. Answer in 2 or 3 plain sentences with AED amounts and thousands separators. "
              "Lead with a clear yes or no for the expected case, then the risk and what keeps it safe. Use only these facts (value, proof id); "
              "chances are fractions, say them as percentages. Return JSON {\"answer\": str, \"proof\": [proof ids used]}. "
              f"Facts: {json.dumps(f)}\nQuestion: Are we safe in week 4?")
    txt = llm.live_chat("voice week 4", prompt, mock, max_tokens=3000, budget_s=60) if llm.live_ready() else mock
    try: r = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    except ValueError: r = json.loads(mock)
    return dict(question="Are we safe in week 4?", answer=r.get("answer"), proof=r.get("proof", []), model=llm.OPEN_MODEL if txt != mock else "rule based")
