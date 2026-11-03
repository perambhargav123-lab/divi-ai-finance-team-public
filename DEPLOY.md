# Deploy

The public demo runs in replay mode only (`DIVI_MOCK=1`). It plays back answers recorded from real Muse calls, so it needs no model key and costs nothing to run. Never add model keys to the host.

## Checks before deploying
- `python scripts/secrets_scan.py` reports no secrets in the tree or history.
- `DIVI_MOCK=1 python -m pytest -q tests` passes.

## Option A: Render
1. Copy `deploy/render.yaml` to the repo root.
2. New Blueprint in Render, pick the repo, confirm.
3. Health check `/api/scoreboard`. Open the URL, press Run the close, then Reset demo.

## Option B: Fly.io
1. `fly launch --copy-config --config deploy/fly.toml --no-deploy`
2. Do not set any model key secrets: the public demo is replay only.
3. `fly deploy --config deploy/fly.toml`

## Local Docker
`docker build -t divi . && docker run -p 8000:8000 divi`

## Live mode (local only)
Copy `.env.example` to `.env`, set your key, and start without `DIVI_MOCK=1`.
