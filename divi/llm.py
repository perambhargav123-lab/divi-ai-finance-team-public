import re
"""Model client. Meta Model API (OpenAI compatible) plus Baseten for Muse Spark Open.
Falls back to mock mode when keys are missing or DIVI_MOCK=1."""
import base64, json, os, mimetypes, threading
from pathlib import Path as _EP

def _load_env():
    """Read the private .env (gitignored) into the environment. Values are never logged."""
    f = _EP(__file__).resolve().parents[1] / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()

META_BASE_URL = "https://api.meta.ai/v1"
META_MODEL = os.getenv("DIVI_META_MODEL", "muse-spark-1.3")
BASETEN_BASE_URL = os.getenv("BASETEN_BASE_URL", "https://inference.baseten.co/v1")
OPEN_MODEL = os.getenv("DIVI_OPEN_MODEL", "meta-models/muse-spark-open-1026")  # hackathon slug from Baseten

CALLS = {"count": 0}

def _key(name):
    return os.getenv(name) or (os.getenv("MODEL_API_KEY") if name == "META_API_KEY" else None)

def is_mock(provider="meta"):
    if os.getenv("DIVI_MOCK") == "1":
        return True
    return not _key("META_API_KEY" if provider == "meta" else "BASETEN_API_KEY")

def _client(provider):
    from openai import OpenAI
    if provider == "meta":
        return OpenAI(base_url=META_BASE_URL, api_key=_key("META_API_KEY")), META_MODEL
    return OpenAI(base_url=BASETEN_BASE_URL, api_key=_key("BASETEN_API_KEY")), OPEN_MODEL

def default_provider():
    """DIVI_PROVIDER=baseten routes text agents to Muse Spark Open (open-weight) on Baseten. Mock until BASETEN_API_KEY is set."""
    return os.getenv("DIVI_PROVIDER", "meta")

def live_ready():
    """True when Muse Spark Open on Baseten can run the close live (key present, not forced mock)."""
    return os.getenv("DIVI_MOCK") != "1" and os.getenv("DIVI_LIVE", "1") != "0" and bool(_key("BASETEN_API_KEY"))

def complete(prompt, provider=None, mock_response=None):
    if LIVE["on"] and live_ready():
        return live_chat("complete", prompt, mock_response if mock_response is not None else json.dumps({"mock": True, "fallback": True}))
    provider = provider or default_provider()
    CALLS["count"] += 1
    if is_mock(provider):
        return mock_response if mock_response is not None else json.dumps({"mock": True})
    c, m = _client(provider)
    try:
        return c.responses.create(model=m, input=prompt, timeout=float(os.getenv("DIVI_TIMEOUT", "60"))).output_text
    except Exception as ex:
        FALLBACKS.append(dict(purpose="complete", error=type(ex).__name__))
        return mock_response if mock_response is not None else json.dumps({"mock": True, "fallback": True})

def extract_image(path, instruction, mock_response=None):
    if LIVE["on"] and live_ready():
        return live_chat("receipt vision", instruction, mock_response if mock_response is not None else "{}", image=path)
    CALLS["count"] += 1
    if is_mock("meta"):
        return mock_response if mock_response is not None else "{}"
    mime = mimetypes.guess_type(path)[0] or "image/png"
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    c, m = _client("meta")
    r = c.responses.create(model=m, input=[{"role": "user", "content": [
        {"type": "input_text", "text": instruction},
        {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"}]}])
    return r.output_text

# ---- tracing and cache (day 5) ----
import hashlib, time as _time
from pathlib import Path as _P
PRICE_USD = {"in": 1.25 / 1e6, "out": 4.25 / 1e6}  # muse-spark-1.3 standard mode, dev.meta.ai pricing page, 27 Oct 2026
USD_AED = 3.6725
TRACE = []
FALLBACKS = []
CACHE_FILE = _P(__file__).resolve().parents[1] / "out" / "cache" / "llm_cache.json"
_cache = None

def _load():
    global _cache
    if _cache is None:
        _cache = json.load(open(CACHE_FILE, encoding="utf-8")) if CACHE_FILE.exists() else {}
    return _cache

def _cost(i, o): return round((i * PRICE_USD["in"] + o * PRICE_USD["out"]) * USD_AED, 4)

def _mode(p): return "structured JSON output" if "JSON" in p else "text"

def ask(purpose, prompt, mock_response="{}", image=None):
    """Cached, traced Muse call. Replays a recorded real answer when one exists so demos never fail.
    During a live close (LIVE['on']) it calls Muse Spark Open on Baseten first and falls back to the recording."""
    key = hashlib.sha256((prompt + (image or "")).encode()).hexdigest()[:20]; c = _load()
    if LIVE["on"] and live_ready():
        fb = c[key]["text"] if key in c else mock_response
        return live_chat(purpose, prompt, fb, image=image)
    if key in c:
        e = c[key]; TRACE.append(dict(purpose=purpose, model=e["model"], tokens_in=e["tokens_in"], tokens_out=e["tokens_out"],
                                      latency_s=e["latency_s"], cost_aed=_cost(e["tokens_in"], e["tokens_out"]), source="replay of real call", mode=_mode(prompt)))
        return e["text"]
    if is_mock():
        TRACE.append(dict(purpose=purpose, model="mock", tokens_in=0, tokens_out=0, latency_s=0, cost_aed=0, source="mock")); return mock_response
    cl, m = _client("meta"); t0 = _time.time(); CALLS["count"] += 1
    if image:
        mime = mimetypes.guess_type(image)[0] or "image/png"; b64 = base64.b64encode(open(image, "rb").read()).decode()
        inp = [{"role": "user", "content": [{"type": "input_text", "text": prompt}, {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"}]}]
    else:
        inp = prompt
    r = None
    for attempt in range(2):  # one retry, then a graceful fallback so the close never stops
        try:
            r = cl.responses.create(model=m, input=inp, timeout=float(os.getenv("DIVI_TIMEOUT", "60"))); break
        except Exception as ex:  # network, rate limit, 5xx, bad key
            err = f"{type(ex).__name__}"; _time.sleep(1.5 * (attempt + 1))
    if r is None:
        TRACE.append(dict(purpose=purpose, model=m, tokens_in=0, tokens_out=0, latency_s=round(_time.time() - t0, 1), cost_aed=0,
                          source=f"fallback after {err}: rule based answer used, flagged for review"))
        FALLBACKS.append(dict(purpose=purpose, error=err)); return mock_response
    e = dict(text=r.output_text, model=m, tokens_in=r.usage.input_tokens, tokens_out=r.usage.output_tokens, latency_s=round(_time.time() - t0, 1), purpose=purpose)
    c[key] = e; CACHE_FILE.parent.mkdir(parents=True, exist_ok=True); json.dump(c, open(CACHE_FILE, "w"), indent=1, ensure_ascii=False)
    TRACE.append(dict(purpose=purpose, model=m, tokens_in=e["tokens_in"], tokens_out=e["tokens_out"], latency_s=e["latency_s"],
                      cost_aed=_cost(e["tokens_in"], e["tokens_out"]), source="live call", mode=_mode(prompt)))
    return e["text"]

def parse(txt, default):
    a, b = ("[", "]") if isinstance(default, list) else ("{", "}")
    try: return json.loads(txt[txt.find(a): txt.rfind(b) + 1])
    except ValueError: return default


def _num(m):
    v = float(m.group(2).replace(",", ""))
    return f"{m.group(1)}{'-' if v < 0 else ''}{abs(v):,.0f}"


def clean(t):
    """House style: no em dashes, AED amounts with separators and no long decimals."""
    if not isinstance(t, str): return t
    t = re.sub(r"\s*\u2014\s*", ", ", t)
    t = re.sub(r"(\d)\s*\u2013\s*(\d)", r"\1 to \2", t).replace("\u2013", "-")
    return re.sub(r"(AED\s?)(-?\d{4,}(?:\.\d+)?)", _num, t)


def ask_tools(purpose, prompt, tools, mock_calls):
    """Native tool calling via the Responses API tools parameter. Cached and traced like ask().
    Returns a list of {name, arguments}. Falls back to the mock plan if the call fails."""
    key = "tools:" + hashlib.sha256((prompt + json.dumps(tools, sort_keys=True)).encode()).hexdigest()[:20]; c = _load()
    if key in c:
        e = c[key]; TRACE.append(dict(purpose=purpose, model=e["model"], tokens_in=e["tokens_in"], tokens_out=e["tokens_out"], latency_s=e["latency_s"],
                                      cost_aed=_cost(e["tokens_in"], e["tokens_out"]), source="replay of real call", mode="tool calling"))
        return e["calls"]
    if is_mock():
        TRACE.append(dict(purpose=purpose, model="mock", tokens_in=0, tokens_out=0, latency_s=0, cost_aed=0, source="mock", mode="tool calling")); return mock_calls
    cl, m = _client("meta"); t0 = _time.time(); CALLS["count"] += 1
    try:
        r = cl.responses.create(model=m, input=prompt, tools=tools, timeout=float(os.getenv("DIVI_TIMEOUT", "60")))
    except Exception as ex:
        FALLBACKS.append(dict(purpose=purpose, error=type(ex).__name__))
        TRACE.append(dict(purpose=purpose, model=m, tokens_in=0, tokens_out=0, latency_s=0, cost_aed=0, source=f"fallback after {type(ex).__name__}", mode="tool calling"))
        return mock_calls
    calls = [dict(name=o.name, arguments=json.loads(o.arguments or "{}")) for o in r.output if getattr(o, "type", "") == "function_call"]
    e = dict(calls=calls, model=m, tokens_in=r.usage.input_tokens, tokens_out=r.usage.output_tokens, latency_s=round(_time.time() - t0, 1), purpose=purpose)
    c[key] = e; json.dump(c, open(CACHE_FILE, "w"), indent=1, ensure_ascii=False)
    TRACE.append(dict(purpose=purpose, model=m, tokens_in=e["tokens_in"], tokens_out=e["tokens_out"], latency_s=e["latency_s"],
                      cost_aed=_cost(e["tokens_in"], e["tokens_out"]), source="live call", mode="tool calling"))
    return calls


# ---- live mode on Baseten (30 Oct): streamed reasoning, call and token counter, safe fallback ----
LIVE = dict(on=False, agent="divi", calls=0, tokens=0, reasoning_tokens=0, fallbacks=0, model=OPEN_MODEL, provider="Baseten")
ON_THINK = []          # callbacks(agent, text) fed with streamed reasoning
_lk = threading.Lock()

def live_reset():
    LIVE.update(on=True, calls=0, tokens=0, reasoning_tokens=0, fallbacks=0)

def live_stats():
    return {k: LIVE[k] for k in ("calls", "tokens", "reasoning_tokens", "fallbacks", "model", "provider")}

def _think(text):
    for cb in ON_THINK:
        try: cb(LIVE["agent"], text)
        except Exception: pass

def live_chat(purpose, prompt, fallback, image=None, max_tokens=None, budget_s=None):
    """One streamed call to Muse Spark Open on Baseten. Streams reasoning to ON_THINK.
    Any error, or no answer inside the time budget, returns `fallback` so the close never stops."""
    from openai import OpenAI
    budget = budget_s or float(os.getenv("DIVI_LIVE_BUDGET_S", "25")); t0 = _time.time()
    content = [{"type": "text", "text": prompt}]
    if image:
        mime = mimetypes.guess_type(image)[0] or "image/png"
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(open(image, "rb").read()).decode()}})
    out, think, last, usage, err = [], [], 0.0, None, None
    try:
        cl = OpenAI(base_url=BASETEN_BASE_URL, api_key=_key("BASETEN_API_KEY"), timeout=budget, max_retries=0)
        st = cl.chat.completions.create(model=OPEN_MODEL, messages=[{"role": "user", "content": content if image else prompt}],
                                        max_tokens=max_tokens or int(os.getenv("DIVI_LIVE_MAX_TOKENS", "2500")),
                                        stream=True, stream_options={"include_usage": True})
        for ch in st:
            if ch.usage: usage = ch.usage
            if ch.choices:
                d = ch.choices[0].delta
                r = getattr(d, "reasoning_content", None) or getattr(d, "reasoning", None)
                if r: think.append(r)
                if d.content: out.append(d.content)
                if think and _time.time() - last > 0.35:
                    last = _time.time(); _think("".join(think)[-600:])
            if _time.time() - t0 > budget:
                err = "slow"; st.close(); break
    except Exception as ex:
        err = type(ex).__name__
    txt = "".join(out).strip()
    with _lk:
        LIVE["calls"] += 1; CALLS["count"] += 1
        if usage:
            LIVE["tokens"] += usage.total_tokens or 0
            LIVE["reasoning_tokens"] += getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", 0) or 0
        if err or not txt: LIVE["fallbacks"] += 1
    ok = not err and txt
    TRACE.append(dict(purpose=purpose, model=OPEN_MODEL, tokens_in=getattr(usage, "prompt_tokens", 0) if usage else 0,
                      tokens_out=getattr(usage, "completion_tokens", 0) if usage else 0, latency_s=round(_time.time() - t0, 1), cost_aed=0,
                      source="live call on Baseten" if ok else f"fallback after {err or 'empty answer'}: recorded answer used", mode=_mode(prompt)))
    if not ok: FALLBACKS.append(dict(purpose=purpose, error=err or "empty")); return fallback
    return txt


def ask_open(purpose, prompt, mock_response, record=True):
    """Call Muse Spark Open on Baseten (a different model from the preparer) and record the answer, so replays work offline.
    Used by the Auditor for independence. Replays the recording when one exists unless DIVI_AUDITOR_LIVE=1."""
    key = "open:" + hashlib.sha256(prompt.encode()).hexdigest()[:20]; c = _load()
    if key in c and os.getenv("DIVI_AUDITOR_LIVE") != "1":
        e = c[key]; TRACE.append(dict(purpose=purpose, model=e["model"], tokens_in=e["tokens_in"], tokens_out=e["tokens_out"],
                                      latency_s=e["latency_s"], cost_aed=0, source="replay of real call on Baseten", mode=_mode(prompt)))
        return e["text"], e["model"]
    if os.getenv("DIVI_MOCK") == "1" or not _key("BASETEN_API_KEY"):
        TRACE.append(dict(purpose=purpose, model="mock", tokens_in=0, tokens_out=0, latency_s=0, cost_aed=0, source="mock")); return mock_response, "rule based"
    n = len(TRACE); txt = live_chat(purpose, prompt, None, max_tokens=3000, budget_s=90)
    if not txt: return mock_response, "rule based (fallback)"
    t = TRACE[n] if len(TRACE) > n else {}
    if record:
        c[key] = dict(text=txt, model=OPEN_MODEL, tokens_in=t.get("tokens_in", 0), tokens_out=t.get("tokens_out", 0), latency_s=t.get("latency_s", 0), purpose=purpose)
        json.dump(c, open(CACHE_FILE, "w"), indent=1, ensure_ascii=False)
    return txt, OPEN_MODEL
