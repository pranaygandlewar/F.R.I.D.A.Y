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
            "Say: 'Incorrect password. I don't know anything about personal details without Personal Mode.'"
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


def is_personal_contact(target: str) -> bool:
    """Check if target represents a personal contact (Divya, family, or personal numbers)."""
    if not target:
        return False
    t = str(target).lower().strip()
    digits = re.sub(r"[^0-9]", "", t)
    if any(num in digits for num in _PRIVATE_NUMBERS if num.isdigit()):
        return True
    return any(
        k in t
        for k in (
            "divya", "khushi", "wife", "biwi", "gf", "girlfriend", "partner",
            "mummy", "mom", "mother", "aai", "maa", "pappa", "papa", "dad",
            "father", "shruti", "sister", "didi", "tai", "would be", "would_be",
            "sbse pyari", "sabse pyari", "fiance", "fiancee", "jaan", "darling",
        )
    )



# ── Password Masking for Activity Log ─────────────────────────────────────────

import time as _time

_awaiting_password: bool = False
_awaiting_password_time: float = 0.0

_PW_PROMPT_PATTERNS = [
    r"\bpassword\s+please\b",
    r"\bpassword\s+bataiye\b",
    r"\bpassword\s+dijiye\b",
    r"\bpassword\s+bolo\b",
    r"\bprovide\s+(?:the\s+)?password\b",
    r"\bstate\s+(?:the\s+)?password\b",
    r"\benter\s+(?:the\s+)?password\b",
    r"\bpassword\s+required\b",
    r"\bpassword\s+kya\s+hai\b",
    r"\bplease\s+provide\s+password\b",
]

_CORRECT_PASSWORD_PATTERNS = [
    r"\b12[\s,/\.\-]+11[\s,/\.\-]+7\b",
    r"\b12117\b",
    r"\bbaa?rah?\s+gyaa?rah?\s+saa?th?\b",
    r"\bbaa?rah?\s+gyaa?ra\s+saa?th?\b",
    r"\bbaa?ra\s+akk?ra\s+saa?th?\b",
    r"\btwelve\s+eleven\s+seven\b",
    r"बारह\s+ग्यारह\s+सात",
    r"बारा\s+अकरा\s+सात",
    r"१२[\s,/\.\-]+११[\s,/\.\-]+७",
    r"१२११७",
]


def is_awaiting_password() -> bool:
    """Return whether the system is actively waiting for a password input."""
    global _awaiting_password
    with _lock:
        if _awaiting_password:
            # Expire after 60 seconds if abandoned
            if _time.monotonic() - _awaiting_password_time > 60.0:
                _awaiting_password = False
                return False
            return True
        return False


def set_awaiting_password(awaiting: bool) -> None:
    """Flag that the next user input is a password attempt."""
    global _awaiting_password, _awaiting_password_time
    with _lock:
        _awaiting_password = bool(awaiting)
        _awaiting_password_time = _time.monotonic() if awaiting else 0.0


def check_if_prompting_password(text: str) -> bool:
    """Check if assistant or system message asks for the password."""
    t = (text or "").lower()
    # If reporting verification outcome, Friday is not asking for password
    if any(w in t for w in ("verified", "correct", "incorrect", "wrong", "galat", "denied", "enabled", "activated", "sahi hai")):
        return False
    if "password" in t:
        if any(w in t for w in ("please", "bataiye", "dijiye", "bolo", "kya", "provide", "state", "enter", "required", "sir", "?")):
            return True
    return any(re.search(pat, t) for pat in _PW_PROMPT_PATTERNS)


def mask_user_text(text: str) -> str:
    """
    Mask password in user text (spoken or typed).
    1. If Friday asked for the password, the user's response in that turn is masked
       in the form of (*), even if the password is wrong.
    2. Even if Friday's prompt flag wasn't set, any correct password (12 11 7 /
       barah gyarah sat / bara akra sat / twelve eleven seven) is ALWAYS hidden in (*).
    3. Normal commands ('Friday enable private mode', etc.) are shown in full.
    """
    global _awaiting_password
    if not text:
        return text

    prefix = ""
    content = text
    m_pfx = re.match(r"^(You:\s*|User:\s*)", text, re.IGNORECASE)
    if m_pfx:
        prefix = m_pfx.group(0)
        content = text[len(prefix):]

    # 1. If Friday asked for the password, mask whatever was given (even wrong password)
    if is_awaiting_password():
        set_awaiting_password(False)
        masked = re.sub(r"\S", "*", content)
        return prefix + masked

    # 2. If the user's message is the correct password, ALWAYS hide it
    if verify_password(content) and not any(k in content.lower() for k in ("mode", "enable", "switch", "karo", "turn", "activate")):
        masked = re.sub(r"\S", "*", content)
        return prefix + masked

    # 3. If the password appears inside a command (e.g. 'enable private mode 12 11 7'), mask only the password
    res = content
    for pat in _CORRECT_PASSWORD_PATTERNS:
        res = re.sub(pat, lambda m: re.sub(r"\S", "*", m.group(0)), res, flags=re.IGNORECASE)

    return prefix + res


def mask_log_line(text: str) -> str:
    """
    Scrubber for the Activity Log widget.
    Detects when Friday asks for password, and masks the user's immediate reply.
    """
    if not text:
        return text
    tl = text.lower().strip()

    if tl.startswith("you:") or tl.startswith("user:"):
        return mask_user_text(text)

    # When assistant asks for password, prime the awaiting flag
    if check_if_prompting_password(text):
        set_awaiting_password(True)

    return text

