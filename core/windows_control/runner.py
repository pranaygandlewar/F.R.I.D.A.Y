"""
core/windows_control/runner.py — Safe subprocess and PowerShell execution runner.

Rules:
- Uses argument lists, NEVER raw shell string concatenation.
- Applies timeouts and catches exceptions.
- Employs CREATE_NO_WINDOW on Windows.
- Masks sensitive credentials/tokens from output and diagnostics.
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from typing import Any, Optional

_IS_WINDOWS = platform.system() == "Windows"
_WIN_FLAGS = subprocess.CREATE_NO_WINDOW if _IS_WINDOWS else 0

def sanitize_output(text: str) -> str:
    """Mask potential passwords, wifi keys, or secrets from diagnostic output."""
    if not text:
        return ""
    sanitized = text
    # Mask Wi-Fi key content (e.g., Key Content : password123)
    sanitized = re.sub(r'(?i)(Key\s*Content\s*:\s*)(.+)$', r'\1[PROTECTED]', sanitized, flags=re.MULTILINE)
    # Mask key-value secrets (e.g., password=secret, token: secret)
    sanitized = re.sub(r'(?i)(password|secret|key|token|auth)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1: [PROTECTED]', sanitized)
    return sanitized


def run_cmd(
    args: list[str],
    timeout: float = 15.0,
    check: bool = False,
    cwd: Optional[str] = None
) -> tuple[int, str, str]:
    """Execute a command via subprocess using an argument array.
    Returns (returncode, stdout, stderr).
    """
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_WIN_FLAGS,
            cwd=cwd,
            check=check,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds: {' '.join(args[:2])}"
    except Exception as e:
        return -1, "", str(e)


def run_powershell(
    script: str,
    timeout: float = 15.0,
    json_output: bool = False
) -> tuple[int, Any, str]:
    """Execute a PowerShell script block safely via -Command.
    Returns (returncode, parsed_output_or_string, stderr).
    """
    if not _IS_WINDOWS:
        return -1, None, "PowerShell is only supported on Windows."

    # Using -NoProfile and -NonInteractive for isolation and speed
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-Command", f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {script}",
    ]

    rc, stdout, stderr = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        return rc, stdout, stderr

    if json_output:
        try:
            parsed = json.loads(stdout)
            return rc, parsed, stderr
        except Exception:
            return rc, stdout, stderr

    return rc, stdout, stderr
