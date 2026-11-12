"""
Personal / Private Mode Security Controller for F.R.I.D.A.Y.

Protects personal data (Divya's identity, contact numbers, email, relationship status)
from unauthorized access. In normal mode, private data is locked.
When the user switches to Private Mode and speaks the password (12 11 7 / barah gyarah sat / bara akra sat),
Private Mode is activated and personal information becomes accessible.
"""
from __future__ import annotations

import re
import threading
from typing import Tuple

_lock = threading.Lock()
_private_mode_active: bool = False

# Password token map supporting English, Hindi (Latin & Devanagari), Marathi, and digits
WORD_MAP = {
    # 12
    "12": 12, "twelve": 12, "barah": 12, "bara": 12, "baarah": 12, "baraha": 12,
    "बारह": 12, "बारा": 12, "१२": 12,
    # 11
    "11": 11, "eleven": 11, "gyarah": 11, "gyara": 11, "gyaarah": 11, "gyaaraha": 11,
    "akra": 11, "akkra": 11, "akrah": 11, "ग्यारह": 11, "ग्यारा": 11, "अकरा": 11, "११": 11,
    # 7
    "7": 7, "seven": 7, "sat": 7, "saat": 7, "sath": 7, "saath": 7,
    "सात": 7, "७": 7,
}

_SENSITIVE_KEYWORDS = {
    "divya", "khushi", "wife", "biwi", "gf", "girlfriend", "partner",
    "phone", "number", "mobile", "contact", "email", "would be", "would_be",
    "proposal", "forever_proposal", "mummy", "mom", "mother", "pappa", "papa",
    "father", "shruti", "tai", "didi", "sister",
}

_SENSITIVE_KEYS = {
    "divya_status", "divya_name", "khushi_name", "wife_phone", "would_be_phone",
    "wife_aliases", "mummy_phone", "mummy_aliases", "pappa_phone", "pappa_aliases",
    "shruti_phone", "shruti_aliases", "email", "forever_proposal_status",
    "forever_proposal_path", "sister_name",
}

_PRIVATE_NUMBERS = {
    "9699645603", "7057274830", "9637286137", "8208450096",
    "pranaygandlewar06@gmail.com",
}


def is_private_mode_active() -> bool:
    """Return whether Private/Personal Mode is currently enabled."""
    with _lock:
        return _private_mode_active


def set_private_mode_active(active: bool) -> None:
    """Explicitly set Private Mode state."""
    global _private_mode_active
    with _lock:
        _private_mode_active = bool(active)


def verify_password(candidate: str) -> bool:
    """
    Verify whether the spoken or typed candidate matches the password:
    '12 11 7' / 'barah gyarah sat' / 'bara akra sat' / 'twelve eleven seven'
    """
    if not candidate:
        return False
    raw = str(candidate).lower().strip()

    # Normalize Devanagari numerals
    devanagari_digits = str.maketrans("०१२३४५६७८९", "0123456789")
    normalized = raw.translate(devanagari_digits)

    # Check for direct sequence of digits
    digits_only = re.sub(r"[^0-9]", "", normalized)
    if "12117" in digits_only:
        return True

    # Tokenize words, punctuation, slashes, dashes
    tokens = [
        re.sub(r"^[^\w\u0900-\u097F]+|[^\w\u0900-\u097F]+$", "", w)
        for w in re.split(r"[\s,/\-]+", normalized)
    ]
    tokens = [t for t in tokens if t]

    nums = [WORD_MAP[t] for t in tokens if t in WORD_MAP]
    for i in range(len(nums) - 2):
        if nums[i:i + 3] == [12, 11, 7]:
            return True

    return False


def enable_private_mode(candidate: str) -> Tuple[bool, str]:
    """Attempt to enable Private Mode with password verification."""
    global _private_mode_active
    if verify_password(candidate):
        with _lock:
            _private_mode_active = True
        return (
            True,
            (
                "SUCCESS: Personal/Private Mode is now ENABLED! Authentication verified. "
                "You are now authorized to share all personal details, Divya's information, and contacts. "
                "Divya is Pranay's future wife/partner (phone: 9699645603). "
                "Pranay's email is pranaygandlewar06@gmail.com. "
                "Family contacts: Mummy: 7057274830, Papa: 9637286137, Shruti: 8208450096. "
                "You can answer whatever the user asks!"
            ),
        )
    return (
        False,
        (
            "DENIED: Incorrect password. Personal/Private Mode remains DISABLED. "
            "You must NOT reveal any details about Divya or personal contacts. "
            "Inform the user that the password was incorrect."
        ),
    )


def disable_private_mode() -> str:
    """Disable Private Mode and lock confidential information."""
    global _private_mode_active
    with _lock:
        _private_mode_active = False
    return (
        "SUCCESS: Personal/Private Mode is now DISABLED. All personal information "
        "and Divya's details are now locked and confidential."
    )


def is_sensitive_query(query: str) -> bool:
    """Check if query is asking for private/sensitive info."""
    q = (query or "").lower()
    return any(k in q for k in _SENSITIVE_KEYWORDS)


def is_sensitive_entry(cat: str, key: str, val: str) -> bool:
    """Check if a stored memory entry is confidential."""
    cat_low = cat.lower()
    if cat_low in ("relationships", "relationship"):
        return True
    k_low = key.lower()
    if k_low in _SENSITIVE_KEYS or any(
        s in k_low for s in (
            "divya", "khushi", "wife", "biwi", "gf", "girlfriend", "partner",
            "relationship", "phone", "email", "proposal", "would_be", "would be"
        )
    ):
        return True
    v_low = str(val).lower()
    if any(
        s in v_low for s in (
            "divya", "khushi", "future wife", "wife", "girlfriend", "biwi",
            "partner", "9699645603", "7057274830", "9637286137", "8208450096",
            "pranaygandlewar06@gmail.com"
        )
    ):
        return True
    return False
