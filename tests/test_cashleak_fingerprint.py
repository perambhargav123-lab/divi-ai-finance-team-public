import copy
from divi import cashleak, fingerprint

def test_leak_types_and_total():
    r = cashleak.find(); types = {l["type"] for l in r["leaks"]}
    assert {"duplicate payment", "unused subscription", "subscription price increase", "vendor price creep", "unmatched charge"} <= types
    assert r["total_qar"] == round(sum(l["amount_qar"] for l in r["leaks"]), 2) == 5427.0
    assert all(l["sources"] for l in r["leaks"])

def test_duplicate_is_pearl_catering():
    d = [l for l in cashleak.find()["leaks"] if l["type"] == "duplicate payment"]
    assert len(d) == 1 and d[0]["sources"] == ["Q015", "Q016"] and d[0]["amount_qar"] == 2750.0

def test_receipts_not_flagged():
    assert not any("Lusail" in l["vendor"] for l in cashleak.find()["leaks"])

def test_sign_and_verify():
    s = fingerprint.sign(fingerprint.pack_from_leaks(cashleak.find()))
    assert len(s["fingerprint"]["sha256"]) == 64 and fingerprint.verify(s)["verified"]

def test_tampered_figure_fails():
    s = fingerprint.sign(fingerprint.pack_from_leaks(cashleak.find())); t = copy.deepcopy(s)
    t["figures"][0]["value"] += 1
    assert not fingerprint.verify(t)["verified"]

def test_removed_source_fails():
    s = fingerprint.sign(fingerprint.pack_from_leaks(cashleak.find())); t = copy.deepcopy(s)
    t["figures"][0]["sources"].pop()
    assert not fingerprint.verify(t)["verified"]

def test_wrong_key_fails(monkeypatch):
    s = fingerprint.sign(fingerprint.pack_from_leaks(cashleak.find()))
    monkeypatch.setenv("DIVI_SIGNING_KEY", "another-key")
    assert fingerprint.verify(s)["reason"] == "signature does not match key"

def test_order_independent():
    p = fingerprint.pack_from_leaks(cashleak.find()); q = copy.deepcopy(p); q["figures"].reverse()
    assert fingerprint.sign(p)["fingerprint"]["sha256"] == fingerprint.sign(q)["fingerprint"]["sha256"]
