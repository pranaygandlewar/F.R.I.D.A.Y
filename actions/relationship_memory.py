"""
relationship_memory — Personal Relationship Memory management tool for F.R.I.D.A.Y.

Auto-discovered via TOOL dict (core.action_loader). All actions are gated by
Private Mode — the auth check happens before any data is read or written.

Supported actions:
  recall      — Retrieve stored memories about a person
  update      — Update a profile field
  add_memory  — Append a shared memory
  forget      — Remove a shared memory by index
  show_people — List all stored people
  show_profile — Full structured profile
"""
from __future__ import annotations


def relationship_memory_action(parameters: dict, **_) -> str:
    """Handler for the relationship_memory tool."""
    action = str(parameters.get("action", "")).lower().strip()
    person = str(parameters.get("person", "")).strip()
    text   = str(parameters.get("text", "")).strip()
    field  = str(parameters.get("field", "")).strip()
    value  = str(parameters.get("value", "")).strip()
    index  = parameters.get("index", 0)

    # Auth check is inside each prm_manager function.
    # We import here (not at module level) to keep discovery lightweight.
    try:
        from memory.prm_manager import (
            search_prm, update_person, add_memory, forget_memory,
            list_people, show_profile,
        )
    except Exception as e:
        return f"Personal relationship memory unavailable: {e}"

    if action == "recall":
        if not person:
            return "Please specify a person to recall memories about."
        return search_prm(person)

    elif action == "add_memory":
        if not person:
            return "Please specify the person this memory is about."
        if not text:
            return "Please provide the memory text to store."
        return add_memory(person, text)

    elif action == "update":
        if not person:
            return "Please specify the person to update."
        if not field:
            return "Please specify the field to update (personal_significance, relationship_category, notes)."
        if not value:
            return "Please provide the new value."
        return update_person(person, field, value)

    elif action == "forget":
        if not person:
            return "Please specify the person whose memory to forget."
        try:
            idx = int(index)
        except (TypeError, ValueError):
            idx = 0
        return forget_memory(person, idx)

    elif action == "show_people":
        return list_people()

    elif action == "show_profile":
        if not person:
            return "Please specify a person to show the profile for."
        return show_profile(person)

    else:
        return (
            f"Unknown action '{action}'. "
            "Supported: recall, add_memory, update, forget, show_people, show_profile."
        )


TOOL = {
    "name": "relationship_memory",
    "description": (
        "Manage personal relationship memories about important people in Sir's life "
        "(e.g. Divya). "
        "CRITICAL: ALL actions require Private Mode to be active. "
        "If Private Mode is OFF, this tool returns a locked message — do NOT repeat it. "
        "Actions: "
        "recall = retrieve stored memories about a person; "
        "add_memory = save a new shared memory or feeling; "
        "update = update a profile field (personal_significance, relationship_category, notes); "
        "forget = remove a specific memory by index; "
        "show_people = list all important people stored; "
        "show_profile = show the full structured profile for a person."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "Action to perform: recall | add_memory | update | forget | "
                    "show_people | show_profile"
                ),
            },
            "person": {
                "type": "STRING",
                "description": (
                    "Name or alias of the person (e.g. 'divya', 'khushi'). "
                    "Required for: recall, add_memory, update, forget, show_profile."
                ),
            },
            "text": {
                "type": "STRING",
                "description": "Memory text to store. Required for: add_memory.",
            },
            "field": {
                "type": "STRING",
                "description": (
                    "Profile field to update. Required for: update. "
                    "Allowed: personal_significance, relationship_category, notes."
                ),
            },
            "value": {
                "type": "STRING",
                "description": "New value for the field. Required for: update.",
            },
            "index": {
                "type": "NUMBER",
                "description": (
                    "0-based index of the memory to forget. Required for: forget. "
                    "Use show_profile first to see the index."
                ),
            },
        },
        "required": ["action"],
    },
    "handler": relationship_memory_action,
}
