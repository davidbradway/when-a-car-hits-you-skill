# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Two implementations of the same crash-response decision tree for cyclists/pedestrians hit by a car, kept in sync with each other:

1. **`skills/when-a-car-hits-you/`** — an Anthropic Agent Skill. `SKILL.md` *is* the product: a single markdown file of instructions (phase detection, emergency check, phase-specific guidance, NC/Durham add-ons, lawyer recommendation logic, report format) that Claude follows directly in conversation. There is no code to build or run here — editing behavior means editing the prose/instructions in `SKILL.md`. To distribute it to Claude.ai (Settings → Features → Skills), zip the `skills/when-a-car-hits-you/` folder fresh — no packaged zip is kept in the repo, since it would go stale the moment `SKILL.md` changes.
2. **`twilio-ivr/`** — a Flask app that reproduces the same decision tree as a phone IVR (DTMF + speech-to-text) via Twilio, emailing a matching crash summary report at the end of the call (or on hangup).

**Keep them in sync**: `twilio-ivr/ivr/steps.py` (question order/branching), `guidance.py` (phase guidance text), and `report.py` (report format, urgent flags, lawyer logic) are a code reproduction of `SKILL.md`'s Step 3–5c and Step 7. If you change the decision tree, emergency criteria, NC/Durham guidance, or report format in one, update the other to match.

## Commands (twilio-ivr/)

All commands run from the `twilio-ivr/` directory.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in SMTP_USER / SMTP_PASSWORD, etc.

python app.py             # run the dev server on http://localhost:5000

pip install pytest
VALIDATE_TWILIO_SIGNATURE=false pytest tests/ -v      # run all tests
VALIDATE_TWILIO_SIGNATURE=false pytest tests/test_engine.py::test_emergency_symptoms_short_circuits_to_report -v  # single test
```

Tests drive the Flask app end-to-end via `client.post("/voice", ...)` / `client.post("/gather/<step_id>", ...)` — no real Twilio account needed. `sent_emails` fixture monkeypatches `mailer.send_email` to capture output instead of sending.

There is no build/lint step configured for either part of the repo.

## Architecture: twilio-ivr

The call is a state machine driven entirely by `ivr/steps.py`:

- **`ivr/steps.py`** — the decision tree. Each `Step` has a spoken `prompt`, an `input_type` (`"dtmf"` or `"speech"`), an optional `digit_map` (DTMF digit → stored answer value), and a `next_id(session)` function that inspects `session.answers` so far to pick the next step. This is how phase detection, the emergency short-circuit, and conditional branches are implemented — there is no separate branching layer. Terminal `next_id` value `REPORT` means: stop, speak closing guidance, email the report, hang up.
- **`ivr/state.py`** — `CallSession` dataclass (answers, retries, current step) held in a process-global dict keyed by Twilio `CallSid`, guarded by a lock. This only works for a single-process deployment; scaling to multiple gunicorn workers would need a shared store (e.g. Redis) since a call's webhooks must all land on the worker holding its session.
- **`app.py`** — three routes: `POST /voice` (start a call, render the `phase` step), `POST /gather/<step_id>` (receive the caller's DTMF/speech answer, validate/retry, store it, advance via `step.next_id`), `POST /status` (Twilio call-status webhook — emails whatever was collected so far, marked "[Abandoned call]", if the call ended before reaching `REPORT`). Twilio webhook signatures are verified via `validate_twilio_request` unless `VALIDATE_TWILIO_SIGNATURE=false`.
- **`ivr/guidance.py`** — phase-specific spoken guidance text (mirrors `SKILL.md` Step 4).
- **`ivr/report.py`** — builds the emailed report text, closing speech, and the urgent-flag/lawyer-recommendation logic (mirrors `SKILL.md` Step 5b/5c/7).
- **`ivr/mailer.py`** — SMTP send. If `SMTP_USER`/`SMTP_PASSWORD` are blank, the report is logged instead of emailed (useful for local testing without credentials).

To extend the tree: add/edit `Step`s in `ivr/steps.py`, then update `ivr/report.py` if the new answer should appear in the emailed report or closing guidance.

Local Twilio testing: `ngrok http 5000`, then point the Twilio number's Voice webhook at `https://<id>.ngrok.io/voice` and status webhook at `.../status`. Production: `gunicorn -w 4 -b 0.0.0.0:8000 app:app` behind HTTPS, with `TWILIO_AUTH_TOKEN` set.

## Key domain facts baked into both implementations

These are the load-bearing pieces of guidance encoded in the decision tree — get them right if editing either implementation:

- Emergency symptoms (loss of consciousness, confusion, vomiting, unequal pupils, severe headache, chest pain, dizziness) short-circuit everything else: stop and tell the user to call 911 immediately.
- Say "crash," never "accident." Say "I'm not sure yet, I need to be evaluated," never "I'm fine."
- North Carolina is a pure contributory negligence state (1% fault can bar recovery) — this triggers extra legal-guidance branches and the Ann Groninger/Bike Law attorney recommendation, with a further Durham-specific layer (local police non-emergency line, CrimeStoppers, Bike Durham, Durham One Call) on top of the statewide NC guidance.
- This is not legal/medical/financial advice — every report and both READMEs say so; preserve that disclaimer in any output format changes.
