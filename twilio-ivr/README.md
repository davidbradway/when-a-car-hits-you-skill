# Crash Line — Twilio IVR

A phone-based version of the [`when-a-car-hits-you`](../skills/when-a-car-hits-you/SKILL.md)
Claude skill. Call a Twilio number, get walked through the same decision
tree by voice — phase detection, an emergency check, phase-specific
guidance, the core intake questions, North Carolina/Durham add-ons, and a
lawyer recommendation when warranted — and a crash summary report is
emailed at the end of the call, whether the caller finishes or hangs up
partway through.

## How a call flows

1. **Phase check** (DTMF) — at the scene, within 24 hours, or later.
2. **Emergency check** (DTMF) — loss of consciousness, confusion, vomiting,
   severe headache, chest pain, dizziness. A "yes" here immediately tells
   the caller to hang up and call 911, emails an urgent report to the
   configured recipient, and ends the call — none of the remaining
   questions are asked.
3. **Phase guidance**, spoken aloud right after the emergency check: the
   phase-appropriate next steps from the skill's Step 4, with the option to
   hear them again or continue on to the intake questions.
4. **Intake questions** (mix of DTMF menus and speech-to-text) — when/where,
   mode of travel, state, police report, driver info, photos, witnesses,
   driver behavior, medical care, injuries (free speech), whether the
   driver's insurer has been in touch, any settlement offer, whether the
   caller's own insurer has been notified, and expenses (free speech).
5. **Closing guidance**, spoken aloud: the single most urgent flag if any,
   and — automatically, based on the answers — added guidance for North
   Carolina/Durham, and a lawyer recommendation when the situation warrants
   one (this mirrors the skill's Step 5b/5d branches).
6. **Report emailed** to `REPORT_TO_EMAIL`, formatted like the skill's
   crash summary report: crash details, scene checklist, injuries, urgent
   flags, next steps, completed steps, expenses, and word-for-word scripts.

If the caller hangs up before finishing, `/status` (Twilio's call-status
webhook) emails whatever was collected so far, marked "[Abandoned call]".

## Project layout

```
twilio-ivr/
  app.py            Flask routes: /voice, /gather/<step_id>, /status
  ivr/
    config.py       Env-var configuration
    state.py        In-memory per-call session store (keyed by CallSid)
    steps.py        The decision tree: prompts, DTMF maps, transitions
    guidance.py     Phase labels and phase-specific guidance text
    report.py       Report text, closing speech, urgent-flag/lawyer logic
    mailer.py       SMTP email sending
  tests/
    test_engine.py  End-to-end tests against the Flask app (no real Twilio)
```

## Local setup

```bash
cd twilio-ivr
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in SMTP_USER / SMTP_PASSWORD etc.
python app.py          # runs on http://localhost:5000
```

`.env.example` sets `VALIDATE_TWILIO_SIGNATURE=false`. Without a Twilio account
there is no signature to check, and with validation on and no token every
request is refused with a 500. Production leaves the setting out entirely,
where the code default of `true` applies.

Leaving `SMTP_USER`/`SMTP_PASSWORD` blank is fine: the report is logged instead
of emailed. Set `LOG_REPORT_BODY=true` to see the whole report in the log.

Run the tests:

```bash
pip install pytest
VALIDATE_TWILIO_SIGNATURE=false pytest tests/ -v
```

### Driving the IVR without Twilio

The webhooks are ordinary form POSTs, so `curl` can walk the tree. Keep the
same `CallSid` across requests — it is the session key. DTMF steps take
`Digits`, speech steps take `SpeechResult`; each response's `action="..."`
tells you the next step to post to.

```bash
curl -X POST localhost:5000/voice -d 'CallSid=dev1&From=%2B15551234567'
curl -X POST localhost:5000/gather/phase          -d 'CallSid=dev1&Digits=2'
curl -X POST localhost:5000/gather/emergency      -d 'CallSid=dev1&Digits=2'
curl -X POST localhost:5000/gather/phase_guidance -d 'CallSid=dev1&Digits=2'
curl -X POST localhost:5000/gather/datetime_location \
     -d 'CallSid=dev1&SpeechResult=yesterday on Main Street'
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

### Email delivery

The report is sent over SMTP. For Gmail: enable 2-Step Verification on
`david.bradway@gmail.com`, create an **App Password**, and set:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=david.bradway@gmail.com
SMTP_PASSWORD=<the 16-character app password>
REPORT_TO_EMAIL=david.bradway@gmail.com
```

If `SMTP_USER`/`SMTP_PASSWORD` are left blank, the app logs the report
instead of emailing it — useful for local testing without credentials.

### Exposing it to Twilio locally

```bash
ngrok http 5000
```

Point your Twilio number's **Voice → A call comes in** webhook at
`https://<ngrok-id>.ngrok.io/voice` (HTTP POST), and its
**Call status changes** webhook at `https://<ngrok-id>.ngrok.io/status`
(HTTP POST) so abandoned calls still get reported.

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
restart the decision tree mid-call. Concurrency comes from threads, which
are safe because the store is lock-guarded:

```bash
gunicorn --workers 1 --threads 4 -b 0.0.0.0:8000 app:app
```

Running multiple workers or instances would first need a shared session
store (e.g. Redis) in place of `ivr/state.py`.

Set `TWILIO_AUTH_TOKEN` (from the Twilio Console) so incoming webhook
requests are verified — `VALIDATE_TWILIO_SIGNATURE` defaults to `true`, and
the app now refuses requests if validation is on but the token is missing,
rather than silently serving them unverified.

**Behind a proxy, the app relies on `ProxyFix`** (already wired up in
`app.py`) plus the proxy forwarding `X-Forwarded-Proto` and
`X-Forwarded-Host`. Twilio signs the public HTTPS URL; without those the
app sees `http://127.0.0.1:8000/...`, every signature check fails, and all
webhooks return 403.

`GET /healthz` returns `{"status": "ok", "commit": "<GIT_SHA>"}` for
health checks and for confirming which build is live.

## Extending the tree

Add or edit questions in `ivr/steps.py` — each `Step` has a spoken prompt,
an input type (`"dtmf"` or `"speech"`), a DTMF digit map (if applicable),
and a `next_id` function that can branch on any answer collected so far.
Update `ivr/report.py` if a new answer should show up in the emailed
report or the closing guidance.

This is not legal, medical, or financial advice. Laws vary by state;
always consult qualified professionals.
