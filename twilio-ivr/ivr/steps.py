"""The decision tree itself.

Each Step is one turn of the phone call: something is spoken, then either a
DTMF digit or a short speech answer is collected. `next_id` inspects the
answers gathered so far to decide where to go next, which is how phase
detection, the emergency short-circuit, and the North Carolina / USAA
branches from the source skill are reproduced over the phone.

Terminal step id "REPORT" means: stop asking questions, speak the closing
guidance, email the report, hang up.
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .state import CallSession

REPORT = "REPORT"


@dataclass
class Step:
    id: str
    prompt: Callable[[CallSession], str]
    input_type: str  # "dtmf" or "speech"
    field: str
    next_id: Callable[[CallSession], str]
    num_digits: int = 1
    digit_map: Optional[Dict[str, str]] = None  # DTMF digit -> stored value
    retry_prompt: str = "Sorry, I didn't get that."
    skip_default: str = "unsure"  # value stored if retries are exhausted


def _mode_word(session: CallSession) -> str:
    return {"cycling": "cycling", "walking": "walking"}.get(
        session.answers.get("mode"), "cycling or walking"
    )


# ---------------------------------------------------------------------------
# Step definitions, in the order a call generally moves through them.
# ---------------------------------------------------------------------------

STEPS: Dict[str, Step] = {}


def _register(step: Step) -> None:
    STEPS[step.id] = step


_register(Step(
    id="phase",
    prompt=lambda s: (
        "This is David's automated crash line. "
        "What happened to you was serious, no matter how it looks right now. "
        "First, I need to know when this happened. "
        "Press 1 if you are still at the scene of the crash right now. "
        "Press 2 if this happened within the last 24 hours. "
        "Press 3 if it happened more than a day ago."
    ),
    input_type="dtmf",
    field="phase",
    digit_map={"1": "at_scene", "2": "recent", "3": "later"},
    next_id=lambda s: "emergency",
    skip_default="recent",
))

_register(Step(
    id="emergency",
    prompt=lambda s: (
        "Are you experiencing any of the following right now: loss of consciousness, "
        "confusion, vomiting, unequal pupils, a severe headache, chest pain, or dizziness? "
        "Press 1 for yes. Press 2 for no."
    ),
    input_type="dtmf",
    field="emergency_symptoms",
    digit_map={"1": "yes", "2": "no"},
    next_id=lambda s: REPORT if s.answers.get("emergency_symptoms") == "yes" else "datetime_location",
    skip_default="no",
))

_register(Step(
    id="datetime_location",
    prompt=lambda s: (
        "When and where did this happen? Please say the date or time, and the location, "
        "after the tone."
    ),
    input_type="speech",
    field="datetime_location_raw",
    next_id=lambda s: "mode",
))

_register(Step(
    id="mode",
    prompt=lambda s: (
        "Press 1 if you were cycling. Press 2 if you were walking or running. "
        "Press 3 for another situation."
    ),
    input_type="dtmf",
    field="mode",
    digit_map={"1": "cycling", "2": "walking", "3": "other"},
    next_id=lambda s: "state_location",
    skip_default="other",
))

_register(Step(
    id="state_location",
    prompt=lambda s: "What state did this happen in?",
    input_type="speech",
    field="state_raw",
    next_id=lambda s: "police",
))

_register(Step(
    id="police",
    prompt=lambda s: (
        "Have you called 911, or is there a police report for this crash? "
        "Press 1 for yes. Press 2 for no. Press 3 if you're not sure."
    ),
    input_type="dtmf",
    field="police_report",
    digit_map={"1": "yes", "2": "no", "3": "unsure"},
    next_id=lambda s: "driver_info",
    skip_default="unsure",
))

_register(Step(
    id="driver_info",
    prompt=lambda s: (
        "Did you get the driver's name, license plate, and insurance information? "
        "Press 1 for yes. Press 2 for partly. Press 3 for no."
    ),
    input_type="dtmf",
    field="driver_info",
    digit_map={"1": "yes", "2": "partial", "3": "no"},
    next_id=lambda s: "photos",
    skip_default="no",
))

_register(Step(
    id="photos",
    prompt=lambda s: (
        "Did you take photos of the scene, the vehicle, and your injuries? "
        "Press 1 for yes. Press 2 for no."
    ),
    input_type="dtmf",
    field="photos",
    digit_map={"1": "yes", "2": "no"},
    next_id=lambda s: "witnesses",
    skip_default="no",
))

_register(Step(
    id="witnesses",
    prompt=lambda s: (
        "Were there any witnesses, and did you get their contact information? "
        "Press 1 for yes. Press 2 for no. Press 3 if there were no witnesses."
    ),
    input_type="dtmf",
    field="witnesses",
    digit_map={"1": "yes", "2": "no", "3": "none"},
    next_id=lambda s: "driver_behavior",
    skip_default="unsure",
))

_register(Step(
    id="driver_behavior",
    prompt=lambda s: (
        "Did the driver stay at the scene, leave, or ask to handle things privately "
        "without police? Press 1 if they stayed. Press 2 if they fled. "
        "Press 3 if they wanted to handle it privately."
    ),
    input_type="dtmf",
    field="driver_behavior",
    digit_map={"1": "stayed", "2": "fled", "3": "private"},
    next_id=lambda s: "medical_care",
    skip_default="stayed",
))

_register(Step(
    id="medical_care",
    prompt=lambda s: (
        "Have you sought medical care, such as an ambulance, urgent care, or an emergency room? "
        "Press 1 for yes. Press 2 for no, because you feel fine. Press 3 for no, you're declining care."
    ),
    input_type="dtmf",
    field="medical_care",
    digit_map={"1": "yes", "2": "no_feels_fine", "3": "declined"},
    next_id=lambda s: "injuries",
    skip_default="no_feels_fine",
))

_register(Step(
    id="injuries",
    prompt=lambda s: (
        "Please describe, in your own words, any injuries, pain, or symptoms you're feeling "
        "right now."
    ),
    input_type="speech",
    field="injuries_raw",
    next_id=lambda s: "insurer_contacted",
))

_register(Step(
    id="insurer_contacted",
    prompt=lambda s: (
        "Has the driver's insurance company contacted you, or asked you for a recorded "
        "statement? Press 1 for yes. Press 2 for no."
    ),
    input_type="dtmf",
    field="insurer_contacted",
    digit_map={"1": "yes", "2": "no"},
    next_id=lambda s: "settlement_offered",
    skip_default="no",
))

_register(Step(
    id="settlement_offered",
    prompt=lambda s: "Has anyone offered you a settlement, of any amount? Press 1 for yes. Press 2 for no.",
    input_type="dtmf",
    field="settlement_offered",
    digit_map={"1": "yes", "2": "no"},
    next_id=lambda s: "own_insurer_notified",
    skip_default="no",
))

_register(Step(
    id="own_insurer_notified",
    prompt=lambda s: "Have you notified your own auto insurance company? Press 1 for yes. Press 2 for no.",
    input_type="dtmf",
    field="own_insurer_notified",
    digit_map={"1": "yes", "2": "no"},
    next_id=lambda s: "insurance_provider",
    skip_default="no",
))

_register(Step(
    id="insurance_provider",
    prompt=lambda s: "Who is your auto insurance company?",
    input_type="speech",
    field="insurer_name_raw",
    next_id=lambda s: "expenses",
))

_register(Step(
    id="expenses",
    prompt=lambda s: (
        "Last question. Please list any expenses so far, like medical bills, transportation, "
        "lost income, or bike or gear repair."
    ),
    input_type="speech",
    field="expenses_raw",
    next_id=lambda s: REPORT,
))
