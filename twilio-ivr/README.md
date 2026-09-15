# Crash Line — Twilio IVR

A phone-based crash line, based on Ann Groninger's guidance for what to do
after being hit by a car while biking, walking, or running. Call a Twilio
number, answer one question, and hear the matching advice — with a live
transfer offered to North Carolina callers.

## How a call flows

1. **North Carolina check** (DTMF) — "Press 1 if the crash happened in
   North Carolina. Press 2 if it happened somewhere else."
2. **Advice**, spoken aloud:
   - North Carolina callers hear the North Carolina–specific guidance
     (pure contributory negligence, and the insurance/med-pay rules that
     follow from it) plus the general guidance.
   - Everyone else hears the general guidance only.
3. **Transfer offer** (North Carolina callers only) — "Press 1 to be
   connected now to the Law Office of Johnson & Groninger, PLLC. Otherwise,
   stay on the line and this call will end." Pressing 1 dials
   (919) 899-4078 live; anything else ends the call.

Nothing about the call is recorded, reported, or emailed — it's advice
read aloud and, optionally, a transfer.

## Project layout

```
twilio-ivr/
  app.py            Flask routes: /voice, /gather/nc_check, /gather/transfer
  ivr/
    config.py       Env-var configuration
    state.py        In-memory per-call session store (keyed by CallSid)
    steps.py        The two DTMF questions: prompts and digit maps
    advice.py        Spoken guidance text (North Carolina and general)
  tests/
    test_engine.py  End-to-end tests against the Flask app (no real Twilio)
```

## Local setup

```bash
cd twilio-ivr
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py          # runs on http://localhost:5000
```

`.env.example` sets `VALIDATE_TWILIO_SIGNATURE=false`. Without a Twilio account
there is no signature to check, and with validation on and no token every
request is refused with a 500. Production leaves the setting out entirely,
where the code default of `true` applies.

Run the tests:

```bash
pip install pytest
VALIDATE_TWILIO_SIGNATURE=false pytest tests/ -v
```

### Driving the IVR without Twilio

The webhooks are ordinary form POSTs, so `curl` can walk the tree. Keep the
same `CallSid` across requests — it is the session key.

```bash
curl -X POST localhost:5000/voice -d 'CallSid=dev1&From=%2B15551234567'
curl -X POST localhost:5000/gather/nc_check -d 'CallSid=dev1&Digits=1'
curl -X POST localhost:5000/gather/transfer -d 'CallSid=dev1&Digits=2'
```

`GET /healthz` returns `{"status": "ok", "commit": "..."}` and needs no session.

### Running the container locally

To reproduce exactly what the server runs, including the single-worker gunicorn
setup:

```bash
docker build -t crashline --build-arg GIT_SHA=$(git rev-parse --short HEAD) .
docker run --rm -p 8000:8000 --env-file .env crashline
```

Podman works too, but needs `--format docker` on the build or the healthcheck
is silently dropped.

### Exposing it to Twilio locally

```bash
ngrok http 5000
```

Point your Twilio number's **Voice → A call comes in** webhook at
`https://<ngrok-id>.ngrok.io/voice` (HTTP POST). No other webhooks are needed.

### Production deployment

Twilio requires HTTPS in production, so run behind a TLS-terminating
reverse proxy. The supplied `Dockerfile` is the reference deployment:

```bash
docker build -t crashline --build-arg GIT_SHA=$(git rev-parse --short HEAD) .
docker run -d -p 127.0.0.1:8000:8000 --env-file .env crashline
```

**Use exactly one gunicorn worker.** Call state lives in an in-memory dict
keyed by `CallSid` (`ivr/state.py`), so a second worker would receive a
caller's later webhooks in a process that has never seen their session and
restart the call mid-flow. Concurrency comes from threads, which are safe
because the store is lock-guarded:

```bash
gunicorn --workers 1 --threads 4 -b 0.0.0.0:8000 app:app
```

Set `TWILIO_AUTH_TOKEN` (from the Twilio Console) so incoming webhook
requests are verified — `VALIDATE_TWILIO_SIGNATURE` defaults to `true`, and
the app refuses requests if validation is on but the token is missing,
rather than silently serving them unverified.

**Behind a proxy, the app relies on `ProxyFix`** (already wired up in
`app.py`) plus the proxy forwarding `X-Forwarded-Proto` and
`X-Forwarded-Host`. Twilio signs the public HTTPS URL; without those the
app sees `http://127.0.0.1:8000/...`, every signature check fails, and all
webhooks return 403.

`GET /healthz` returns `{"status": "ok", "commit": "<GIT_SHA>"}` for
health checks and for confirming which build is live.

## Editing the advice or the transfer number

Advice text lives in `ivr/advice.py` (`NC_ADVICE`, `GENERAL_ADVICE`).
`TRANSFER_NUMBER` there is the live-transfer destination
((919) 899-4078, the Law Office of Johnson & Groninger, PLLC). The two
prompts themselves — the North Carolina question and the transfer offer —
live in `ivr/steps.py`.

This is not legal, medical, or financial advice. Laws vary by state;
always consult a qualified attorney.
