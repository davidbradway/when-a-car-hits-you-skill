"""The two questions asked by the crash line.

1. "nc_check" — was the crash in North Carolina? Answering this decides
   which advice gets read (ivr/advice.py) and whether the caller is later
   offered a transfer.
2. "transfer" — only reached when the caller said North Carolina — offers a
   live transfer to the Law Office of Johnson & Groninger, PLLC.
"""
from dataclasses import dataclass
from typing import Callable, Dict

from .state import CallSession


@dataclass
class Step:
    id: str
    prompt: Callable[[CallSession], str]
    field: str
    digit_map: Dict[str, str]
    num_digits: int = 1
    retry_prompt: str = "Sorry, I didn't get that."
    skip_default: str = "no"


STEPS: Dict[str, Step] = {}


def _register(step: Step) -> None:
    STEPS[step.id] = step


_register(Step(
    id="nc_check",
    prompt=lambda s: (
        "Thank you for calling. This line has guidance for anyone who has been hit by a car "
        "while biking, walking, or running. "
        "Press 1 if the crash happened in North Carolina. Press 2 if it happened somewhere else."
    ),
    field="in_nc",
    digit_map={"1": "yes", "2": "no"},
    skip_default="no",
))

_register(Step(
    id="transfer",
    prompt=lambda s: (
        "Press 1 to be connected now to the Law Office of Johnson and Groninger. "
        "Otherwise, stay on the line and this call will end."
    ),
    field="transfer_choice",
    digit_map={"1": "transfer", "2": "end"},
    skip_default="end",
))
