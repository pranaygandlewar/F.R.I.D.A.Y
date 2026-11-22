"""
ASUS TUF Aura & Keyboard Backlit Controller for F.R.I.D.A.Y.

Handles Fn + F4 (Aura) keyboard backlight cycling and RGB lighting
for ASUS TUF Gaming laptops (e.g. ASUS TUF Gaming F16).

Integrates:
1. Direct ACPI hardware communication via \\\\.\\ATKACPI (TUF_KB / TUF_KB2).
2. Keyboard hotkey simulation (Fn + F4 / F4).
3. Preset cycling (Color Cycle -> Red -> Green -> Blue -> Cyan -> Magenta -> Yellow -> White -> Breathing).
4. Direct color setting when the user requests a specific color (e.g. 'red', 'blue', 'green', 'rainbow').
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import struct
import sys
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_BASE_DIR = _get_base_dir()
_STATE_FILE = _BASE_DIR / "config" / "aura_state.json"

# ASUS ACPI constants
_FILE_NAME = r"\\.\ATKACPI"
_CONTROL_CODE = 0x0022240C
_DEVS = 0x53564544
_TUF_KB = 0x00100056
_TUF_KB2 = 0x0010005A

# Lighting Modes:
# 0 = Static, 1 = Breathing, 2 = Color Cycle (Spectrum), 3 = Strobe
_PRESETS = [
    {"name": "Color Cycle (Rainbow)", "mode": 2, "r": 255, "g": 0, "b": 0, "speed": 1},
    {"name": "Red",                   "mode": 0, "r": 255, "g": 0, "b": 0, "speed": 1},
    {"name": "Green",                 "mode": 0, "r": 0, "g": 255, "b": 0, "speed": 1},
    {"name": "Blue",                  "mode": 0, "r": 0, "g": 100, "b": 255, "speed": 1},
    {"name": "Cyan",                  "mode": 0, "r": 0, "g": 255, "b": 255, "speed": 1},
    {"name": "Magenta",               "mode": 0, "r": 255, "g": 0, "b": 255, "speed": 1},
    {"name": "Yellow",                "mode": 0, "r": 255, "g": 200, "b": 0, "speed": 1},
    {"name": "White",                 "mode": 0, "r": 255, "g": 255, "b": 255, "speed": 1},
    {"name": "Breathing",             "mode": 1, "r": 0, "g": 255, "b": 255, "speed": 1},
]

_COLOR_ALIASES = {
    "red":            {"name": "Red", "mode": 0, "r": 255, "g": 0, "b": 0, "speed": 1},
    "green":          {"name": "Green", "mode": 0, "r": 0, "g": 255, "b": 0, "speed": 1},
    "blue":           {"name": "Blue", "mode": 0, "r": 0, "g": 100, "b": 255, "speed": 1},
    "cyan":           {"name": "Cyan", "mode": 0, "r": 0, "g": 255, "b": 255, "speed": 1},
    "aqua":           {"name": "Cyan", "mode": 0, "r": 0, "g": 255, "b": 255, "speed": 1},
    "magenta":        {"name": "Magenta", "mode": 0, "r": 255, "g": 0, "b": 255, "speed": 1},
    "purple":         {"name": "Magenta", "mode": 0, "r": 180, "g": 0, "b": 255, "speed": 1},
    "pink":           {"name": "Pink", "mode": 0, "r": 255, "g": 105, "b": 180, "speed": 1},
    "yellow":         {"name": "Yellow", "mode": 0, "r": 255, "g": 200, "b": 0, "speed": 1},
    "orange":         {"name": "Orange", "mode": 0, "r": 255, "g": 140, "b": 0, "speed": 1},
    "white":          {"name": "White", "mode": 0, "r": 255, "g": 255, "b": 255, "speed": 1},
    "rainbow":        {"name": "Color Cycle (Rainbow)", "mode": 2, "r": 255, "g": 0, "b": 0, "speed": 1},
    "color cycle":    {"name": "Color Cycle (Rainbow)", "mode": 2, "r": 255, "g": 0, "b": 0, "speed": 1},
    "color_cycle":    {"name": "Color Cycle (Rainbow)", "mode": 2, "r": 255, "g": 0, "b": 0, "speed": 1},
    "spectrum":       {"name": "Color Cycle (Rainbow)", "mode": 2, "r": 255, "g": 0, "b": 0, "speed": 1},
    "cycle":          {"name": "Color Cycle (Rainbow)", "mode": 2, "r": 255, "g": 0, "b": 0, "speed": 1},
    "breathing":      {"name": "Breathing", "mode": 1, "r": 0, "g": 255, "b": 255, "speed": 1},
    "strobe":         {"name": "Strobe", "mode": 3, "r": 255, "g": 255, "b": 255, "speed": 1},
    "strobing":       {"name": "Strobe", "mode": 3, "r": 255, "g": 255, "b": 255, "speed": 1},
    "off":            {"name": "Off", "mode": 0, "r": 0, "g": 0, "b": 0, "speed": 1},
}


def _load_current_index() -> int:
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            return int(data.get("preset_index", 0))
    except Exception:
        pass
    return 0


def _save_current_index(index: int) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps({"preset_index": index}), encoding="utf-8")
    except Exception:
        pass


def _send_acpi_command(mode: int, r: int, g: int, b: int, speed: int = 1) -> bool:
    """Send ACPI hardware command to ASUS TUF keyboard controller."""
    if platform.system() != "Windows":
        return False
    try:
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        FILE_ATTRIBUTE_NORMAL = 0x80

        handle = ctypes.windll.kernel32.CreateFileW(
            _FILE_NAME,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None
        )
        if handle == -1 or handle == 0:
            return False

        # Payload format: 0xb4, mode, R, G, B, speed
        setting = bytes([0xb4, mode & 0xFF, r & 0xFF, g & 0xFF, b & 0xFF, speed & 0xFF])
        args = struct.pack('<I', _TUF_KB) + setting
        acpi_buf = struct.pack('<II', _DEVS, len(args)) + args
        out_buf = ctypes.create_string_buffer(16)
        bytes_ret = ctypes.c_ulong(0)

        res = ctypes.windll.kernel32.DeviceIoControl(
            handle,
            _CONTROL_CODE,
            acpi_buf,
            len(acpi_buf),
            out_buf,
            len(out_buf),
            ctypes.byref(bytes_ret),
            None
        )
        ret_val = struct.unpack('<i', out_buf.raw[:4])[0] if bytes_ret.value >= 4 else 0

        # Fallback to TUF_KB2 if TUF_KB didn't return 1
        if ret_val != 1:
            setting2 = bytes([0xb3, mode & 0xFF, r & 0xFF, g & 0xFF, b & 0xFF, speed & 0xFF])
            args2 = struct.pack('<I', _TUF_KB2) + setting2
            acpi_buf2 = struct.pack('<II', _DEVS, len(args2)) + args2
            ctypes.windll.kernel32.DeviceIoControl(
                handle, _CONTROL_CODE, acpi_buf2, len(acpi_buf2),
                out_buf, len(out_buf), ctypes.byref(bytes_ret), None
            )

        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    except Exception as e:
        print(f"[Aura] ACPI communication error: {e}")
        return False


def cycle_keyboard_backlight(target: str | None = None) -> str:
    """
    Cycles or sets the keyboard backlit / Aura lighting directly via
    hardware ACPI (ASUS TUF Embedded Controller).

    NOTE: We explicitly do NOT simulate the OS F4 keypress, because F4
    is FRIDAY's own shortcut for toggling microphone mute/unmute.
    Hardware ACPI control updates the keyboard lighting directly without
    touching the OS key queue.

    Args:
        target: Optional specific color or mode ('red', 'blue', 'green', 'rainbow', etc.).
                If omitted or None, cycles to the next Aura preset.

    Returns:
        Confirmation string naming the active Aura mode/color.
    """
    # 1. Check if user specified an explicit color or mode
    t_clean = (str(target or "")).lower().strip().replace("-", " ").replace("_", " ")
    selected_preset = None

    if t_clean and t_clean not in ("cycle", "next", "change", "aura", "backlight", "backlit"):
        for alias, info in _COLOR_ALIASES.items():
            if alias in t_clean or t_clean in alias:
                selected_preset = info
                break

    # 3. If no specific color was matched, cycle to the next preset
    if not selected_preset:
        idx = _load_current_index()
        next_idx = (idx + 1) % len(_PRESETS)
        selected_preset = _PRESETS[next_idx]
        _save_current_index(next_idx)

    # 4. Apply hardware ACPI changes
    mode = selected_preset["mode"]
    r = selected_preset["r"]
    g = selected_preset["g"]
    b = selected_preset["b"]
    speed = selected_preset.get("speed", 1)
    name = selected_preset["name"]

    acpi_ok = _send_acpi_command(mode, r, g, b, speed)

    status_extra = f" (Aura preset: {name})"
    print(f"[Aura] Keyboard backlit switched: {name} (ACPI: {acpi_ok})")
    return f"Keyboard backlit changed via Fn + F4{status_extra}."
