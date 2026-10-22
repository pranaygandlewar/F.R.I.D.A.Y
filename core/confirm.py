"""
core/confirm.py — a confirmation the model cannot forge.

THE PROBLEM WITH THE OLD GATE
    computer_settings guarded shutdown and restart like this:

        confirmed = str(params.get("confirmed", "")).lower()
        if confirmed not in ("yes", "true", "1", "confirm"):
            return "Please confirm by calling again with confirmed=yes."

    `confirmed` is a tool parameter, which means the *model* writes it. Nothing
    stops it from sending confirmed=yes on the first call, and nothing checks
    that a human was ever involved. It is a convention, not a gate — and its
    coverage was two actions, so deleting files and switching off the WiFi the
    assistant is talking over went through with no gate at all.

THE DESIGN HERE
    The confirmation token is issued by the *interface*, never by the model:

      1. An action calls `request(...)` with a callable that does the real work.
      2. This module posts a yes/no question directly into the chat log and
         returns IMMEDIATELY with a sentence for the model to say out loud.
      3. If — and only if — the user types a confirmation word (yes/y/yeah/ok/
         sure/confirm/proceed) the UI calls `resolve(True)`. Any negative word
         (no/n/nope/cancel/stop/deny) calls `resolve(False)`.

    Nothing blocks. The model keeps talking while waiting for the answer,
    so this costs no latency — unlike the old gate, which burned two tool
    round trips (reject, then re-call) on every shutdown.

WHAT BELONGS HERE AND WHAT DOES NOT
    Only genuinely irreversible things. Anything that can be reversed should be
    done at once and pushed onto core/undo.py instead — undo is faster than a
    question, and an assistant that asks before every action is one nobody uses.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

# A pending confirmation is abandoned after this long. Chosen to outlast a
# normal "hang on, let me look at the screen" pause without leaving a live
# shutdown button sitting in the chat for the rest of the day.
TIMEOUT_SECONDS = 90.0

# Words the user can type to accept or reject a pending confirmation.
_YES_WORDS = {"yes", "y", "yeah", "yep", "yup", "ok", "okay", "sure",
              "confirm", "confirmed", "proceed", "go", "do it", "do", "approve"}
_NO_WORDS  = {"no", "n", "nope", "nah", "cancel", "stop", "deny",
              "reject", "abort", "quit", "negative", "dont", "don't"}


@dataclass
class _Pending:
    key:     str
    title:   str
    detail:  str
    run:     Callable[[], str]
    at:      float


_pending: Optional[_Pending] = None
_lock = threading.Lock()

# Set once at startup by main.py.
# _ask_cb(title, detail)   — post the yes/no question to the chat log
# _cancel_cb()             — optionally note that the question is gone
# _log_cb(text)            — write a system log line
_ask_cb:    Optional[Callable[[str, str], None]] = None
_cancel_cb: Optional[Callable[[], None]]         = None
_log_cb:    Optional[Callable[[str], None]]      = None


def bind(show, hide, log=None) -> None:
    """Wire this module to the chat log. Called once from main.py at startup.

    `show`  — callable(title, detail) that posts the question into the chat.
    `hide`  — optional callable() called when the pending question is dismissed
              early (e.g. timeout); pass None if unused.
    `log`   — optional callable(text) for system-log lines.
    """
    global _ask_cb, _cancel_cb, _log_cb
    _ask_cb    = show
    _cancel_cb = hide
    _log_cb    = log


def _log(msg: str) -> None:
    if _log_cb:
        try:
            _log_cb(msg)
        except Exception:
            pass


def request(key: str, title: str, detail: str, run: Callable[[], str]) -> str:
    """Park an irreversible action behind a conversational yes/no question.

    Returns the sentence the tool should hand back to the model — phrased as an
    instruction so the assistant asks the user out loud in their own language,
    rather than reading an English string verbatim."""
    global _pending

    if _ask_cb is None:
        # No interface bound (headless, or a very early call). Refuse rather
        # than silently performing something irreversible.
        return (f"I cannot confirm '{title}' right now because the interface is "
                f"not available, so I have not done it.")

    with _lock:
        _pending = _Pending(key=key, title=title, detail=detail,
                            run=run, at=time.monotonic())

    try:
        _ask_cb(title, detail)
    except Exception as e:
        with _lock:
            _pending = None
        return f"Could not ask for confirmation: {e}. Nothing was done."

    _log(f"SYS: Awaiting confirmation — {title}")
    return (
        f"[CONFIRMATION_PENDING] I have asked the user in chat: '{title}'. "
        f"Say ONE short sentence in the user's own language telling them you need "
        f"them to reply yes or no in the chat before you do it. Do not claim it is done."
    )


def check_reply(text: str) -> bool | None:
    """Check if `text` is a yes/no reply to a pending confirmation.

    Returns True  → accepted
            False → rejected
            None  → not a yes/no reply (or nothing pending)

    Called by the UI's text-send handler before routing to the AI.
    """
    with _lock:
        if _pending is None:
            return None
        if time.monotonic() - _pending.at > TIMEOUT_SECONDS:
            return None

    normalised = text.strip().lower().rstrip("!.")
    if normalised in _YES_WORDS:
        return True
    if normalised in _NO_WORDS:
        return False
    return None


def resolve(accepted: bool) -> None:
    """Run (or discard) the stored callable.

    Runs the stored callable on a worker thread — this is invoked from the Qt
    thread, and shutting the machine down from inside a button handler would
    freeze the interface on its way out."""
    global _pending

    with _lock:
        p, _pending = _pending, None

    if _cancel_cb:
        try:
            _cancel_cb()
        except Exception:
            pass

    if p is None:
        return

    if time.monotonic() - p.at > TIMEOUT_SECONDS:
        _log(f"SYS: Confirmation expired — {p.title}")
        return

    if not accepted:
        _log(f"SYS: Cancelled — {p.title}")
        return

    def _worker():
        try:
            result = p.run() or "Done."
            _log(f"SYS: Confirmed — {p.title}. {result}")
        except Exception as e:
            _log(f"ERR: {p.title} failed — {e}")

    threading.Thread(target=_worker, daemon=True,
                     name=f"confirm-{p.key}").start()


def pending_title() -> str:
    """'' when nothing is waiting. Lets an action avoid stacking two questions."""
    with _lock:
        if _pending is None:
            return ""
        if time.monotonic() - _pending.at > TIMEOUT_SECONDS:
            return ""
        return _pending.title
