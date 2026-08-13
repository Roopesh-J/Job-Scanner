from datetime import date, datetime, timezone
from typing import Any

DAILY_POSTING_LIMIT = 40
MAX_POSTINGS_PER_BATCH = 5
MAX_POSTING_CHARS = 12000
MAX_CANDIDATE_CHARS = 6000

# Module-level, not st.session_state: Streamlit Community Cloud runs the app as one
# long-lived process shared by every visitor, so this genuinely persists across sessions.
# session_state would reset per browser tab and defeat the point of a shared daily cap.
# Resets whenever the process restarts (redeploy, or waking from inactivity) — accepted
# limitation, this is a best-effort daily budget, not a hard guarantee. Concurrent sessions can
# also cause the counter to overshoot slightly, since incrementing it and checking the
# per-batch budget are not atomic — also accepted, not worth engineering around here.
_state: dict[str, Any] = {"date": None, "count": 0}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _reset_if_new_day() -> None:
    today = _today()
    if _state["date"] != today:
        _state["date"] = today
        _state["count"] = 0


def remaining_today() -> int:
    _reset_if_new_day()
    return max(0, DAILY_POSTING_LIMIT - _state["count"])


def record_processed(n: int = 1) -> None:
    _reset_if_new_day()
    _state["count"] += n
