"""Capture agent: invoice or receipt image to structured JSON."""
import json, re
from divi import llm

FIELDS = ["vendor", "invoice_no", "date", "net", "vat", "total", "currency", "trn"]
PROMPT = ("Extract these fields from the UAE invoice or receipt (may be Arabic or bilingual) "
          "and return only JSON with keys: " + ", ".join(FIELDS) + ". Numbers as floats.")

def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}

def validate(d):
    issues = [f"missing {f}" for f in FIELDS if d.get(f) in (None, "")]
    try:
        if abs(round(float(d["net"]) * 0.05, 2) - float(d["vat"])) > 0.05:
            issues.append("VAT is not 5% of net")
        if abs(float(d["net"]) + float(d["vat"]) - float(d["total"])) > 0.05:
            issues.append("net + VAT does not equal total")
    except (KeyError, TypeError, ValueError):
        pass
    return issues

def normalise(d):
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", str(d.get("date", "")).strip())
    if m:
        d["date"] = f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}"  # UAE docs are day first
    return d

def capture(path, truth=None):
    mock = json.dumps(truth) if truth else None
    d = normalise(parse_json(llm.extract_image(path, PROMPT, mock_response=mock)))
    return {"file": path, "fields": d, "issues": validate(d)}
