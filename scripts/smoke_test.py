"""Credit-light smoke test: 1 text call, 1 English receipt, 1 Arabic receipt. Never prints keys."""
from divi import llm
from divi.agents import capture
assert not llm.is_mock(), "Set META_API_KEY first"
print("text:", llm.complete("In one line: what is the UAE standard VAT rate?")[:200])
for f in ["data/docs/doc_02_en.png", "data/docs/doc_01_ar.png"]:
    print(f, capture.capture(f))
print("calls:", llm.CALLS["count"])
