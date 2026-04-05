from __future__ import annotations


TERMINAL_STATES = {"succeeded", "failed", "cancelled"}

ALLOWED_TRANSITIONS = {
    "accepted": {"queued", "failed", "cancelling"},
    "queued": {"preprocessing", "running", "retrying", "failed", "cancelling"},
    "preprocessing": {"embedding", "running", "retrying", "failed", "cancelling"},
    "embedding": {"persisting", "running", "retrying", "failed", "cancelling"},
    "persisting": {"succeeded", "running", "retrying", "failed", "cancelling"},
    "running": {"preprocessing", "embedding", "persisting", "retrying", "failed", "cancelling", "succeeded"},
    "retrying": {"queued", "failed"},
    "cancelling": {"cancelled"},
}


def can_transition(current_status: str, next_status: str) -> bool:
    return next_status in ALLOWED_TRANSITIONS.get(current_status, set())


def public_status(status: str) -> str:
    if status in {"preprocessing", "embedding", "persisting", "retrying"}:
        return "running"
    return status

