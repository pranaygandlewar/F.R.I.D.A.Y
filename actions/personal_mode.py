"""
Personal / Private Mode Action for F.R.I.D.A.Y.

Allows the user to enable or disable Private Mode using their secret password:
'12 11 7' (or 'barah gyarah sat' / 'bara akra sat' / 'twelve eleven seven').

When enabled, FRIDAY is authorized to answer personal questions and discuss Divya.
When disabled (the default), personal information and Divya's details are strictly confidential.
"""
from __future__ import annotations

from core.private_mode import (
    enable_private_mode,
    disable_private_mode,
    is_private_mode_active,
)


def personal_mode_action(
    parameters: dict,
    player=None,
    session_memory=None,
) -> str:
    action = str(parameters.get("action", "")).strip().lower()
    password = str(parameters.get("password", "")).strip()

    if action in ("enable", "activate", "unlock", "on"):
        if not password:
            msg = (
                "PASSWORD_REQUIRED: Password is required to enable Personal/Private Mode. "
                "Ask the user: 'Password please.'"
            )
            _log(msg, player)
            return msg

        ok, result_msg = enable_private_mode(password)
        if ok:
            _log("SECURITY: 🔒 Private Mode ENABLED (Authentication Successful)", player)
        else:
            _log("SECURITY: ⚠️ Private Mode Authentication FAILED (Incorrect Password)", player)
        return result_msg

    elif action in ("disable", "deactivate", "lock", "off"):
        result_msg = disable_private_mode()
        _log("SECURITY: 🔓 Private Mode DISABLED (Confidential data locked)", player)
        return result_msg

    elif action in ("status", "check"):
        active = is_private_mode_active()
        status_str = "ENABLED" if active else "DISABLED (Locked)"
        msg = f"Personal/Private Mode is currently {status_str}."
        _log(f"SECURITY: Status check: {msg}", player)
        return msg

    else:
        # Default fallback: if password is provided, attempt enable
        if password:
            ok, result_msg = enable_private_mode(password)
            if ok:
                _log("SECURITY: 🔒 Private Mode ENABLED", player)
            else:
                _log("SECURITY: ⚠️ Private Mode FAILED", player)
            return result_msg
        return f"Unknown action '{action}'. Supported actions: 'enable', 'disable', 'status'."


def _log(message: str, player=None) -> None:
    print(f"[PersonalMode] {message}")
    if player:
        try:
            player.write_log(message)
        except Exception:
            pass


TOOL = {
    "name": "personal_mode",
    "description": (
        "Manages Personal Mode (also called Private Mode) to secure or unlock personal "
        "information, Divya's details, and private contacts. "
        "When the user asks to switch to or enable private/personal mode and says the password "
        "('12 11 7', 'barah gyarah sat', 'bara akra sat', 'twelve eleven seven'), call this tool "
        "with action='enable' and password=<user_password>. "
        "To exit private mode, call with action='disable'. To check status, call with action='status'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'enable', 'disable', or 'status'",
            },
            "password": {
                "type": "STRING",
                "description": (
                    "The password spoken or typed by the user (e.g. '12 11 7', 'barah gyarah sat', "
                    "'bara akra sat', 'twelve eleven seven'). Required when action is 'enable'."
                ),
            },
        },
        "required": ["action"],
    },
    "handler": personal_mode_action,
}

