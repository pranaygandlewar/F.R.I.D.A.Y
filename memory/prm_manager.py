"""
Personal Relationship Memory (PRM) Manager for F.R.I.D.A.Y.

Stores structured profiles for important people in Pranay's life.
ALL access is gated by Private Mode — data is never read from disk
when Private Mode is OFF. The auth check happens before any file I/O,
not just before the final response.

Storage: memory/personal_relationships.json  (separate from long_term.json)
Auth:    core.private_mode.is_private_mode_active()  (single source of truth)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE_DIR = _get_base_dir()
_PRM_PATH = _BASE_DIR / "memory" / "personal_relationships.json"
_lock     = Lock()

# Returned whenever Private Mode is OFF — neutral, never confirms a profile exists.
_LOCKED_RESPONSE = (
    "I don't know. If you want personal information, then turn on Personal Mode."
)


# ── File I/O ──────────────────────────────────────────────────────────────────

def load_prm() -> dict:
    """Load the full PRM store from disk. No auth gate — raw I/O only.
    Callers are responsible for checking auth before calling this."""
    if not _PRM_PATH.exists():
        return {}
    with _lock:
        try:
            data = json.loads(_PRM_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"[PRM] ⚠️  Load error: {e}")
            return {}


def save_prm(data: dict) -> None:
    """Write the PRM store to disk. No auth gate — callers must gate."""
    if not isinstance(data, dict):
        return
    _PRM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        _PRM_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ── Auth helper ───────────────────────────────────────────────────────────────

def _priv() -> bool:
    """Check Private Mode state. Fails safe (locked) on import error."""
    try:
        from core.private_mode import is_private_mode_active
        return is_private_mode_active()
    except Exception:
        return False   # fail locked, never fail open


# ── Alias resolution ──────────────────────────────────────────────────────────

def _resolve_name(name_or_alias: str, data: dict) -> Optional[str]:
    """Find the canonical key for a name or alias. Case-insensitive."""
    q = (name_or_alias or "").lower().strip()
    if not q:
        return None
    # Direct key match
    if q in data:
        return q
    # Check aliases list and name field
    for key, profile in data.items():
        if not isinstance(profile, dict):
            continue
        if profile.get("name", "").lower() == q:
            return key
        aliases = profile.get("aliases", [])
        if isinstance(aliases, list) and q in [a.lower() for a in aliases]:
            return key
    return None


# ── Public API — all gated ────────────────────────────────────────────────────

def get_person(name_or_alias: str) -> Optional[dict]:
    """Return a person's FULL profile dict (private), or None.
    Returns None both when Private Mode is OFF and when person not found.
    For public info (no auth required), use get_public_info() instead.
    """
    if not _priv():
        return None     # auth check BEFORE any file I/O
    data = load_prm()
    key  = _resolve_name(name_or_alias, data)
    return data.get(key) if key else None


def get_public_info(name_or_alias: str) -> Optional[dict]:
    """Return the public (non-sensitive) profile section for a person.
    No Private Mode required — this only returns public_info, never private_info.
    Returns None if person not found.
    """
    data = load_prm()   # no auth gate — public data only
    key  = _resolve_name(name_or_alias, data)
    if not key:
        return None
    profile = data.get(key, {})
    return profile.get("public_info") if isinstance(profile, dict) else None


def format_public_prm_for_prompt() -> str:
    """Return public (non-sensitive) PRM context for the system prompt.
    No Private Mode required. Returns empty string if nothing public stored.
    """
    data = load_prm()
    if not data:
        return ""

    lines = ["[KNOWN PEOPLE — PUBLIC PROFESSIONAL INFO]"]
    found_any = False
    for key, profile in data.items():
        if not isinstance(profile, dict):
            continue
        pub = profile.get("public_info")
        if not pub or not isinstance(pub, dict):
            continue
        found_any = True
        name = profile.get("name", key)
        lines.append(f"\n{name}:")
        if pub.get("description"):
            lines.append(f"  {pub['description']}")
        if pub.get("hackathon"):
            lines.append(f"  Hackathon: {pub['hackathon']}")
        if pub.get("friendship"):
            lines.append(f"  Friendship: {pub['friendship']}")
        if pub.get("public_titles"):
            lines.append(f"  Known as: {', '.join(pub['public_titles'])}")
        if pub.get("public_note"):
            lines.append(f"  Note: {pub['public_note']}")

    if not found_any:
        return ""

    lines.append(
        "\nIMPORTANT: The above is public/professional info only. "
        "Romantic or personal details about these people are protected by Private Mode."
    )
    return "\n".join(lines)


def list_people() -> str:
    """Return names of all stored people (Private Mode required)."""
    if not _priv():
        return _LOCKED_RESPONSE
    data = load_prm()
    if not data:
        return "No personal relationship profiles stored yet."
    names = [profile.get("name", key) for key, profile in data.items()
             if isinstance(profile, dict)]
    return "Important people I know about: " + ", ".join(names) + "."


def format_prm_for_prompt() -> str:
    """Return full PRM context (private + public) for the system prompt.
    Returns empty string when Private Mode is OFF (safe default).
    Auth check happens before any file I/O.
    """
    if not _priv():
        return ""   # auth check BEFORE file I/O
    data = load_prm()
    if not data:
        return ""

    lines = ["[PERSONAL RELATIONSHIP MEMORY — PRIVATE MODE ACTIVE]"]
    for key, profile in data.items():
        if not isinstance(profile, dict):
            continue
        name    = profile.get("name", key)
        pub     = profile.get("public_info", {}) or {}
        priv    = profile.get("private_info", {}) or {}
        # Fallback to old flat structure for backwards compatibility
        sig     = priv.get("personal_significance") or profile.get("personal_significance", "")
        feelings = priv.get("user_feelings") or profile.get("user_feelings", [])
        h_feels  = priv.get("feelings_in_hindi", [])
        m_feels  = priv.get("feelings_in_marathi", [])
        shayaris = priv.get("shayari", [])
        prof    = profile.get("professional_associations", {})
        memories = profile.get("shared_memories", [])

        lines.append(f"\nPerson: {name}")
        if pub.get("description"):
            lines.append(f"  Public/Professional: {pub['description']}")
        if pub.get("public_titles"):
            lines.append(f"  Public roles: {', '.join(pub['public_titles'])}")
        if sig:
            lines.append(f"  Personal significance: {sig}")
        if feelings:
            lines.append(f"  How Sir feels (English): {'; '.join(feelings[:5])}")
        if h_feels:
            lines.append(f"  How Sir feels (Hindi): {'; '.join(h_feels[:3])}")
        if m_feels:
            lines.append(f"  How Sir feels (Marathi): {'; '.join(m_feels[:2])}")
        if shayaris:
            lines.append(f"  Shayari available: {len(shayaris)} stored (pick one naturally when asked)")
            lines.append(f"  Sample shayari:\n    {shayaris[0]}")
        if memories:
            lines.append(f"  Shared memories: {'; '.join(str(m) for m in memories[:3])}")
        if prof:
            for ctx_name, ctx_detail in prof.items():
                lines.append(f"  Professional context ({ctx_name}): {ctx_detail}")

    lines.append(
        "\nIMPORTANT: Base ALL responses on the stored profile above. "
        "Do NOT invent feelings, events, or facts not stored here. "
        "Only Sir's feelings are stored — do NOT assume the other person's feelings. "
        "When asked about Divya in Private Mode: share personal feelings + deliver one shayari naturally. "
        "Pick ONE shayari per conversation — do not recite all of them."
    )
    return "\n".join(lines)


def search_prm(query: str) -> str:
    """Search PRM for entries matching query (Private Mode required for private info).
    Auth check happens before accessing private data.
    Public info is always accessible.
    """
    data = load_prm()
    if not data:
        return f"Nothing stored in personal relationships about '{query}'."

    q        = (query or "").lower().strip()
    is_priv  = _priv()
    results: list[str] = []

    for key, profile in data.items():
        if not isinstance(profile, dict):
            continue
        name    = profile.get("name", key)
        aliases = [a.lower() for a in profile.get("aliases", [])]
        pub     = profile.get("public_info", {}) or {}
        priv    = profile.get("private_info", {}) or {}

        profile_text = (json.dumps(pub, ensure_ascii=False) + " " +
                        (json.dumps(priv, ensure_ascii=False) if is_priv else "")).lower()

        if q in key.lower() or q in name.lower() or q in aliases or (q and q in profile_text):
            block = [f"[{name}]"]

            # Public info — always shown
            if pub.get("description"):
                block.append(f"  Professional: {pub['description']}")
            if pub.get("public_titles"):
                block.append(f"  Known as: {', '.join(pub['public_titles'])}")
            if pub.get("hackathon"):
                block.append(f"  Hackathon: {pub['hackathon']}")

            # Private info — gated
            if is_priv:
                sig      = priv.get("personal_significance") or profile.get("personal_significance", "")
                feelings = priv.get("user_feelings") or profile.get("user_feelings", [])
                h_feels  = priv.get("feelings_in_hindi", [])
                shayaris = priv.get("shayari", [])
                mems     = profile.get("shared_memories", [])

                if sig:
                    block.append(f"  Personal significance: {sig}")
                if feelings:
                    block.append(f"  Sir's feelings: {'; '.join(feelings)}")
                if h_feels:
                    block.append(f"  In Hindi: {'; '.join(h_feels)}")
                if shayaris:
                    block.append(f"  Shayari ({len(shayaris)} stored):\n    {shayaris[0]}")
                if mems:
                    block.append(f"  Shared memories: {'; '.join(str(m) for m in mems)}")
            else:
                block.append(
                    "  [Private personal info hidden — activate Private Mode for more.]"
                )

            results.append("\n".join(block))

    if not results:
        return f"Nothing stored in personal relationships about '{query}'."
    return "\n\n".join(results)


def update_person(name_or_alias: str, field: str, value) -> str:
    """Update a field in a person's profile (Private Mode required)."""
    if not _priv():
        return _LOCKED_RESPONSE
    data = load_prm()
    key  = _resolve_name(name_or_alias, data)
    if not key:
        return f"No profile found for '{name_or_alias}'."
    allowed_fields = {
        "personal_significance", "relationship_category", "notes"
    }
    if field not in allowed_fields:
        return f"Cannot update field '{field}'. Allowed: {', '.join(sorted(allowed_fields))}."
    data[key][field]    = value
    data[key]["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    save_prm(data)
    return f"Updated {data[key].get('name', key)} / {field}."


def add_memory(name_or_alias: str, memory_text: str) -> str:
    """Append a shared memory to a person's profile (Private Mode required)."""
    if not _priv():
        return _LOCKED_RESPONSE
    if not memory_text or not memory_text.strip():
        return "Memory text cannot be empty."
    data = load_prm()
    key  = _resolve_name(name_or_alias, data)
    if not key:
        return f"No profile found for '{name_or_alias}'."
    entry = {
        "text":       memory_text.strip(),
        "added_at":   datetime.now().strftime("%Y-%m-%d"),
        "source":     "user_stated",
    }
    data[key].setdefault("shared_memories", []).append(entry)
    data[key]["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    save_prm(data)
    name = data[key].get("name", key)
    return f"Memory about {name} saved."


def add_feeling(name_or_alias: str, feeling: str) -> str:
    """Append a user feeling to a person's profile (Private Mode required)."""
    if not _priv():
        return _LOCKED_RESPONSE
    if not feeling or not feeling.strip():
        return "Feeling text cannot be empty."
    data = load_prm()
    key  = _resolve_name(name_or_alias, data)
    if not key:
        return f"No profile found for '{name_or_alias}'."
    feelings = data[key].setdefault("user_feelings", [])
    if feeling.strip() not in feelings:
        feelings.append(feeling.strip())
        data[key]["updated_at"] = datetime.now().strftime("%Y-%m-%d")
        save_prm(data)
    return f"Feeling about {data[key].get('name', key)} saved."


def forget_memory(name_or_alias: str, memory_index: int) -> str:
    """Remove a shared memory by index (0-based) from a person's profile (Private Mode required)."""
    if not _priv():
        return _LOCKED_RESPONSE
    data     = load_prm()
    key      = _resolve_name(name_or_alias, data)
    if not key:
        return f"No profile found for '{name_or_alias}'."
    memories = data[key].get("shared_memories", [])
    if not memories:
        return f"No shared memories stored for {data[key].get('name', key)}."
    if memory_index < 0 or memory_index >= len(memories):
        return f"Invalid memory index {memory_index}. There are {len(memories)} memories stored."
    removed  = memories.pop(memory_index)
    data[key]["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    save_prm(data)
    removed_text = removed.get("text", str(removed)) if isinstance(removed, dict) else str(removed)
    return f"Memory removed from {data[key].get('name', key)}: '{removed_text[:60]}'"


def show_profile(name_or_alias: str) -> str:
    """Return full structured profile as readable text (Private Mode required)."""
    if not _priv():
        return _LOCKED_RESPONSE
    data = load_prm()
    key  = _resolve_name(name_or_alias, data)
    if not key:
        return f"No profile found for '{name_or_alias}'."
    p    = data[key]
    name = p.get("name", key)
    pub  = p.get("public_info", {}) or {}
    priv = p.get("private_info", {}) or {}

    lines = [f"Profile: {name}"]
    if p.get("aliases"):
        lines.append(f"  Also known as: {', '.join(p['aliases'])}")

    # Public side
    if pub:
        lines.append("\n  [Public / Professional]")
        if pub.get("description"):
            lines.append(f"    {pub['description']}")
        if pub.get("public_titles"):
            lines.append(f"    Roles: {', '.join(pub['public_titles'])}")
        if pub.get("hackathon"):
            lines.append(f"    Hackathon: {pub['hackathon']}")

    # Private side
    sig      = priv.get("personal_significance") or p.get("personal_significance", "")
    feelings = priv.get("user_feelings") or p.get("user_feelings", [])
    h_feels  = priv.get("feelings_in_hindi", [])
    m_feels  = priv.get("feelings_in_marathi", [])
    shayaris = priv.get("shayari", [])

    if sig or feelings:
        lines.append("\n  [Private / Personal]")
    if sig:
        lines.append(f"    Significance: {sig}")
    if feelings:
        lines.append(f"    Sir's feelings:")
        for f in feelings:
            lines.append(f"      - {f}")
    if h_feels:
        lines.append(f"    In Hindi: {'; '.join(h_feels)}")
    if m_feels:
        lines.append(f"    In Marathi: {'; '.join(m_feels)}")
    if shayaris:
        lines.append(f"    Shayari ({len(shayaris)} stored):")
        for i, s in enumerate(shayaris):
            lines.append(f"      [{i}] {s[:80]}...")

    if p.get("shared_memories"):
        lines.append(f"\n  Shared memories ({len(p['shared_memories'])}):")
        for i, m in enumerate(p["shared_memories"]):
            text = m.get("text", str(m)) if isinstance(m, dict) else str(m)
            lines.append(f"    {i}. {text[:100]}")

    lines.append(f"\n  Created: {p.get('created_at', '?')}  |  Updated: {p.get('updated_at', '?')}")
    lines.append(f"  Confidence: {p.get('confidence', '?')}  |  Source: {p.get('source', '?')}")
    return "\n".join(lines)
