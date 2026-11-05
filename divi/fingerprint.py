"""Signed evidence fingerprint.
Each close / evidence pack gets a SHA-256 hash over every figure plus its source references
(canonical JSON, sorted keys), then an HMAC-SHA256 signature. verify() recomputes both, so any
edited figure, removed source or changed signature shows as NOT VERIFIED.
Key: DIVI_SIGNING_KEY env var. Without it a public demo key is used and the result says so
(demo signatures prove integrity of the pack, not who signed it)."""
import hashlib, hmac, json, os, sys
DEMO_KEY = b"divi-public-demo-key-not-secret"

def _key():
    k = os.environ.get("DIVI_SIGNING_KEY")
    return (k.encode(), "env") if k else (DEMO_KEY, "demo")

def canonical(figures):
    rows = [{"id": str(f["id"]), "value": round(float(f["value"]), 2), "sources": sorted(map(str, f.get("sources", [])))} for f in figures]
    return json.dumps(sorted(rows, key=lambda r: r["id"]), sort_keys=True, separators=(",", ":"))

def sign(pack):
    key, mode = _key(); body = canonical(pack["figures"])
    digest = hashlib.sha256(body.encode()).hexdigest()
    sig = hmac.new(key, digest.encode(), hashlib.sha256).hexdigest()
    return {**pack, "fingerprint": {"algo": "sha256+hmac-sha256", "sha256": digest, "signature": sig, "key_mode": mode, "figures": len(pack["figures"])}}

def verify(signed):
    fp = signed.get("fingerprint") or {}
    key, mode = _key(); digest = hashlib.sha256(canonical(signed["figures"]).encode()).hexdigest()
    if digest != fp.get("sha256"): return {"verified": False, "reason": "figures or sources changed since signing", "key_mode": mode}
    if not hmac.compare_digest(hmac.new(key, digest.encode(), hashlib.sha256).hexdigest(), fp.get("signature", "")):
        return {"verified": False, "reason": "signature does not match key", "key_mode": mode}
    return {"verified": True, "reason": f"{fp['figures']} figures and their sources match the signed hash", "sha256": digest, "key_mode": mode}

def pack_from_leaks(report):
    figs = [{"id": f"LEAK-{i+1:02d}", "value": l["amount_qar"], "sources": l["sources"]} for i, l in enumerate(report["leaks"])]
    figs.append({"id": "TOTAL", "value": report["total_qar"], "sources": [s for l in report["leaks"] for s in l["sources"]]})
    return {"name": "Cash leak evidence pack (sample data)", "currency": "QAR", "figures": figs}

if __name__ == "__main__":  # python -m divi.fingerprint sign|verify <file.json>
    cmd, path = sys.argv[1], sys.argv[2]; d = json.load(open(path))
    if cmd == "sign":
        out = sign(d); json.dump(out, open(path, "w"), indent=1); print("signed", out["fingerprint"]["sha256"])
    else:
        r = verify(d); print("VERIFIED" if r["verified"] else "NOT VERIFIED", "-", r["reason"], f"(key: {r['key_mode']})"); sys.exit(0 if r["verified"] else 1)
