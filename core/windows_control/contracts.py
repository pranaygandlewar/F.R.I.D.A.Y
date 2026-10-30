"""
core/windows_control/contracts.py — Standard Result Contract for Windows System Control.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class SystemControlResult:
    success: bool
    action: str
    requested_value: Any = None
    actual_value: Any = None
    verified: bool = False
    requires_confirmation: bool = False
    error: Optional[str] = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def __str__(self) -> str:
        """Formatted summary string suitable for both LLM speech and console logs."""
        if self.message:
            return self.message
        if self.success:
            verif_str = " (Verified)" if self.verified else " (Unverified)"
            val_str = f": {self.actual_value}" if self.actual_value is not None else ""
            return f"Success: {self.action}{val_str}{verif_str}"
        return f"Failed: {self.action}. Error: {self.error or 'Unknown error'}"
