"""In-memory session store for in-progress calls, keyed by Twilio CallSid.

A single process is assumed (see README for scaling notes). Sessions are
dropped once a report has been sent or the call ends.
"""
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

# A session is normally removed when its call reaches the report, or when
# Twilio's /status webhook fires for an abandoned call. Neither is guaranteed:
# if the status webhook is not configured, is rejected, or simply never
# arrives, that session stays in the dict forever. In a long-running single
# process that is an unbounded memory leak — which matters on a small box that
# is expected to run unattended for months. Six hours is far longer than any
# real call and far shorter than anything that would discard live state.
SESSION_TTL_SECONDS = 6 * 60 * 60


@dataclass
class CallSession:
    call_sid: str
    from_number: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Monotonic, so expiry is unaffected by wall-clock or NTP adjustments.
    started_monotonic: float = field(default_factory=time.monotonic)
    current_step: str = "phase"
    answers: Dict[str, Any] = field(default_factory=dict)
    retries: Dict[str, int] = field(default_factory=dict)
    reported: bool = False


_lock = threading.Lock()
_sessions: Dict[str, CallSession] = {}


def _sweep_expired_locked() -> None:
    """Drop abandoned sessions. The caller must already hold _lock."""
    cutoff = time.monotonic() - SESSION_TTL_SECONDS
    for call_sid in [sid for sid, s in _sessions.items() if s.started_monotonic < cutoff]:
        del _sessions[call_sid]


def get_or_create(call_sid: str, from_number: str = "") -> CallSession:
    with _lock:
        # Swept here rather than on a timer: a new call is the only moment the
        # dict can grow, so this bounds it without a background thread.
        _sweep_expired_locked()
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
