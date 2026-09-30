# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Two separate implementations of crash-response guidance for cyclists/pedestrians hit by a car — they are **not** kept in sync with each other; each has its own scope:

1. **`skills/when-a-car-hits-you/`** — an Anthropic Agent Skill. `SKILL.md` *is* the product: a single markdown file of instructions (phase detection, emergency check, phase-specific guidance, NC/Durham add-ons, lawyer recommendation logic, report format) that Claude follows directly in conversation. There is no code to build or run here — editing behavior means editing the prose/instructions in `SKILL.md`. To distribute it to Claude.ai (Settings → Features → Skills), zip the `skills/when-a-car-hits-you/` folder fresh — no packaged zip is kept in the repo, since it would go stale the moment `SKILL.md` changes.
2. **`twilio-ivr/`** — a small Flask app that runs a phone line as a Twilio IVR, based on Ann Groninger's guidance for what to do after being hit by a car. It asks one question (was the crash in North Carolina?), reads back the matching spoken advice one section at a time (press 1 to repeat, 2 to continue), and offers North Carolina callers a live transfer to the Law Office of Johnson & Groninger, PLLC. It does not reproduce the full skill decision tree, and it does not collect, report, or email anything about the call.

## Commands (twilio-ivr/)

All commands run from the `twilio-ivr/` directory.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python app.py             # run the dev server on http://localhost:5000

pip install pytest
VALIDATE_TWILIO_SIGNATURE=false pytest tests/ -v      # run all tests
VALIDATE_TWILIO_SIGNATURE=false pytest tests/test_engine.py::test_nc_caller_hears_nc_advice_and_transfer_offer -v  # single test
```

Tests drive the Flask app end-to-end via `client.post("/voice", ...)` / `client.post("/gather/<step_id>", ...)` — no real Twilio account needed.

There is no build/lint step configured for either part of the repo.

## Architecture: twilio-ivr

The call's menus are all driven by `ivr/steps.py`:

- **`ivr/steps.py`** — the DTMF menus (`Step` dataclass: spoken `prompt`, `digit_map` of DTMF digit → stored answer, `retry_prompt`, `skip_default`). `nc_check` ("was this in North Carolina?"), `section` (asked after every advice section: 1 repeat, 2 continue; silence defaults to continue), and `transfer` (offered only to North Carolina callers). There is no `next_id`/branching machinery — `app.py` wires each transition directly.
- **`ivr/advice.py`** — the spoken guidance, as lists of `Section(title, text)`: `NC_SECTIONS` (pure contributory negligence; the insurance/med-pay rules that follow from it), `GENERAL_SECTIONS` (applies to any state), plus `PREAMBLE` (disclaimer, read once before part 1), `GOODBYE`, and the transfer destination `TRANSFER_NUMBER` ((919) 899-4078) / `TRANSFER_SAY`. `sections_for(in_nc)` picks NC+general vs. general-only; `section_say()` adds the "Part N of M. Title." heading.
- **`ivr/state.py`** — `CallSession` dataclass (answers, retries, current step, `section_index`) held in a process-global dict keyed by Twilio `CallSid`, guarded by a lock, swept on a TTL. This only works for a single-process deployment; scaling to multiple gunicorn workers would need a shared store (e.g. Redis) since a call's webhooks must all land on the worker holding its session.
- **`app.py`** — four routes: `POST /voice` (start a call, render `nc_check`), `POST /gather/nc_check` (store the NC answer, speak the preamble and section 1), `POST /gather/section` (repeat the current section, or advance; after the last section, render the `transfer` step (NC) or say goodbye and hang up (non-NC)), `POST /gather/transfer` (dial `TRANSFER_NUMBER` via `<Dial>` if accepted, else say goodbye and hang up). Twilio webhook signatures are verified via `validate_twilio_request` unless `VALIDATE_TWILIO_SIGNATURE=false`. There is no `/status` webhook and nothing is emailed or logged about a call.

To extend the tree: add/edit `Step`s in `ivr/steps.py` and wire any new transition explicitly in `app.py`; add/edit spoken text in `ivr/advice.py`.

Local Twilio testing: `ngrok http 5000`, then point the Twilio number's Voice webhook at `https://<id>.ngrok.io/voice`. No status webhook is needed. Production: `gunicorn --workers 1 --threads 4 -b 0.0.0.0:8000 app:app` behind HTTPS, with `TWILIO_AUTH_TOKEN` set (exactly one worker — see `ivr/state.py` note above).

## Key domain facts baked into both implementations

- North Carolina is a pure contributory negligence state (1% fault can bar recovery) — this is the reason both implementations treat "was this in North Carolina?" as the first branch point.
- Say "crash," never "accident." Say "I'm not sure yet, I need to be evaluated," never "I'm fine."
- This is not legal/medical/financial advice — both `SKILL.md` and the IVR's advice/README say so; preserve that disclaimer in any output format changes.
