"""In-memory session store for in-progress calls, keyed by Twilio CallSid.

A single process is assumed (see README for scaling notes). Sessions are
dropped once a report has been sent or the call ends.
"""
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class CallSession:
    call_sid: str
    from_number: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_step: str = "phase"
    answers: Dict[str, Any] = field(default_factory=dict)
    retries: Dict[str, int] = field(default_factory=dict)
    reported: bool = False


_lock = threading.Lock()
_sessions: Dict[str, CallSession] = {}


def get_or_create(call_sid: str, from_number: str = "") -> CallSession:
    with _lock:
        session = _sessions.get(call_sid)
        if session is None:
            session = CallSession(call_sid=call_sid, from_number=from_number)
            _sessions[call_sid] = session
        return session


def get(call_sid: str):
    with _lock:
        return _sessions.get(call_sid)


def drop(call_sid: str):
    with _lock:
        _sessions.pop(call_sid, None)
