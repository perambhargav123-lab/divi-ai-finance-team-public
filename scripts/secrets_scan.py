"""Secrets scan: checks the working tree and every commit in git history for key-like strings.
Prints only file, commit and pattern name, never the matched value. Exit code 1 if anything is found."""
import re, subprocess, sys
PAT = {"openai/meta style key": r"\b(sk|LLM|mk)[-_][A-Za-z0-9_\-]{20,}", "bearer token": r"Bearer\s+[A-Za-z0-9\-_\.]{20,}",
       "aws key": r"AKIA[0-9A-Z]{16}", "github token": r"gh[pousr]_[A-Za-z0-9]{30,}", "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
       "key assignment": r"(META_API_KEY|BASETEN_API_KEY|MODEL_API_KEY)\s*=\s*['\"]?[A-Za-z0-9_\-|]{16,}"}
def scan(text, where, hits):
    for name, p in PAT.items():
        if re.search(p, text): hits.append(f"{where}: {name}")
hits = []
files = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
for f in files:
    if f.endswith((".png", ".pdf", ".wav", ".mp3", ".ogg")): continue
    try: scan(open(f, encoding="utf-8", errors="ignore").read(), f, hits)
    except OSError: pass
for c in subprocess.run(["git", "rev-list", "--all"], capture_output=True, text=True).stdout.split():
    scan(subprocess.run(["git", "show", c, "--format=", "--no-color", "--text"], capture_output=True, text=True, errors="ignore").stdout, f"commit {c[:7]}", hits)
env_hist = subprocess.run(["git", "log", "--all", "--format=%h", "--", ".env"], capture_output=True, text=True).stdout.split()
if env_hist: hits.append(f".env appears in commits {env_hist}")
print(f"Scanned {len(files)} tracked files and full history.")
print("\n".join(hits) if hits else "No secrets found. .env never committed.")
sys.exit(1 if hits else 0)
