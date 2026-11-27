"""
ASUS TUF Aura & Keyboard Backlit Controller for F.R.I.D.A.Y.

Handles Fn + F4 (Aura) keyboard backlight cycling, RGB color setting,
brightness adjustment (0-3), and lighting modes (Static, Breathing,
Color Cycle, Strobing) for ASUS TUF Gaming laptops (e.g. ASUS TUF Gaming F16).

Hardware Communication:
1. Direct ACPI hardware communication via \\\\.\\ATKACPI:
   - Device 0x00050021: Keyboard Backlight Brightness (Levels 0, 1, 2, 3)
   - Device 0x00100056 / 0x0010005A: Keyboard RGB Lighting & Modes
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import re
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
_DSTS = 0x53545344
_TUF_KB_BRIGHTNESS = 0x00050021
_TUF_KB_RGB = 0x00100056
_TUF_KB_RGB2 = 0x0010005A

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

# Standard CSS / Named Colors mapped to RGB (0-255)
_EXTENDED_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    # Reds & Pinks
    "red": (255, 0, 0), "crimson": (220, 20, 60), "darkred": (139, 0, 0),
    "pink": (255, 105, 180), "lightpink": (255, 182, 193), "hotpink": (255, 20, 147),
    "deeppink": (255, 20, 147), "rose": (255, 0, 128), "coral": (255, 127, 80),
    "salmon": (250, 128, 114), "lightcoral": (240, 128, 128),
    # Oranges & Browns
    "orange": (255, 140, 0), "darkorange": (255, 120, 0), "amber": (255, 191, 0),
    "gold": (255, 215, 0), "brown": (165, 42, 42), "maroon": (128, 0, 0),
    # Yellows
    "yellow": (255, 220, 0), "lightyellow": (255, 255, 150), "lemon": (255, 247, 0),
    # Greens
    "green": (0, 255, 0), "lime": (50, 255, 50), "limegreen": (50, 205, 50),
    "darkgreen": (0, 100, 0), "forestgreen": (34, 139, 34), "emerald": (80, 200, 120),
    "mint": (152, 255, 152), "olive": (128, 128, 0), "chartreuse": (127, 255, 0),
    "springgreen": (0, 255, 127), "seagreen": (46, 139, 87),
    # Cyans & Teals
    "cyan": (0, 255, 255), "aqua": (0, 255, 255), "teal": (0, 128, 128),
    "turquoise": (64, 224, 208), "darkturquoise": (0, 206, 209), "aquamarine": (127, 255, 212),
    "ice": (200, 240, 255), "iceblue": (180, 230, 255),
    # Blues
    "blue": (0, 100, 255), "darkblue": (0, 0, 180), "navy": (0, 0, 128),
    "skyblue": (135, 206, 235), "deepskyblue": (0, 191, 255), "dodgerblue": (30, 144, 255),
    "royalblue": (65, 105, 225), "midnightblue": (25, 25, 112), "steel": (70, 130, 180),
    "indigo": (75, 0, 130),
    # Purples & Violets
    "purple": (180, 0, 255), "violet": (238, 130, 238), "magenta": (255, 0, 255),
    "fuchsia": (255, 0, 255), "plum": (221, 160, 221), "orchid": (218, 112, 214),
    "lavender": (230, 230, 250),
    # Whites, Grays & Off
    "white": (255, 255, 255), "warmwhite": (255, 240, 210), "coolwhite": (230, 245, 255),
    "silver": (192, 192, 192), "gray": (128, 128, 128), "grey": (128, 128, 128),
    "off": (0, 0, 0), "black": (0, 0, 0),
}


def _load_current_state() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"preset_index": 0, "brightness": 3, "color": "Color Cycle", "mode": 2}


def _save_current_state(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def _send_acpi_call(dev_id: int, payload: bytes) -> tuple[bool, int]:
    """Execute raw ACPI DEVS call via \\\\.\\ATKACPI."""
    if platform.system() != "Windows":
        return False, 0
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
            None,
        )
        if handle == -1 or handle == 0:
            return False, 0

        args = struct.pack("<I", dev_id) + payload
        acpi_buf = struct.pack("<II", _DEVS, len(args)) + args
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
            None,
        )
        ret_val = (
            struct.unpack("<i", out_buf.raw[:4])[0]
            if bytes_ret.value >= 4
            else 0
        )
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(res), ret_val
    except Exception as e:
        print(f"[Aura] ACPI communication error: {e}")
        return False, 0


def _query_acpi_dsts(dev_id: int) -> int | None:
    """Query ACPI DSTS for device status (e.g. current brightness)."""
    if platform.system() != "Windows":
        return None
    try:
        handle = ctypes.windll.kernel32.CreateFileW(
            _FILE_NAME, 0xC0000000, 0, None, 3, 0x80, None
        )
        if handle == -1 or handle == 0:
            return None

        args_dsts = struct.pack("<I", dev_id)
        buf_dsts = struct.pack("<II", _DSTS, len(args_dsts)) + args_dsts
        out_buf = ctypes.create_string_buffer(16)
        bytes_ret = ctypes.c_ulong(0)

        res = ctypes.windll.kernel32.DeviceIoControl(
            handle,
            _CONTROL_CODE,
            buf_dsts,
            len(buf_dsts),
            out_buf,
            len(out_buf),
            ctypes.byref(bytes_ret),
            None,
        )
        val = None
        if res and bytes_ret.value >= 4:
            val = struct.unpack("<I", out_buf.raw[:4])[0]
        ctypes.windll.kernel32.CloseHandle(handle)
        return val
    except Exception:
        return None


def get_keyboard_brightness() -> int:
    """Return the current keyboard backlight brightness level (0, 1, 2, 3)."""
    val = _query_acpi_dsts(_TUF_KB_BRIGHTNESS)
    if val is not None and val != 0:
        return val & 0xFF
    state = _load_current_state()
    return int(state.get("brightness", 3))


def set_keyboard_brightness(level: int) -> tuple[bool, int]:
    """
    Set keyboard backlight brightness directly via ACPI.
    Level: 0 (Off), 1 (Low), 2 (Medium), 3 (High).
    Clamped strictly between 0 and 3.
    """
    lvl = max(0, min(3, int(level)))
    payload = struct.pack("<I", lvl)
    ok, ret = _send_acpi_call(_TUF_KB_BRIGHTNESS, payload)
    state = _load_current_state()
    state["brightness"] = lvl
    _save_current_state(state)
    return ok, lvl


def set_keyboard_color_rgb(
    r: int, g: int, b: int, mode: int = 0, speed: int = 1
) -> bool:
    """
    Set RGB color and mode directly to keyboard hardware.
    Modes: 0=Static, 1=Breathing, 2=Color Cycle, 3=Strobe.
    """
    r_c = max(0, min(255, int(r)))
    g_c = max(0, min(255, int(g)))
    b_c = max(0, min(255, int(b)))
    spd = max(1, min(3, int(speed)))

    setting1 = bytes([0xB4, mode & 0xFF, r_c, g_c, b_c, spd])
    ok1, ret1 = _send_acpi_call(_TUF_KB_RGB, setting1)

    if not ok1 or ret1 != 1:
        setting2 = bytes([0xB3, mode & 0xFF, r_c, g_c, b_c, spd])
        ok2, _ = _send_acpi_call(_TUF_KB_RGB2, setting2)
        return ok2
    return True


def parse_color_and_mode(
    input_str: str,
) -> tuple[tuple[int, int, int] | None, int | None, str | None]:
    """
    Parse hex codes, rgb(r,g,b), named colors, or special modes from input string.
    Returns: ((r, g, b) or None, mode or None, display_name or None)
    """
    s = (input_str or "").strip().lower()

    # 1. Hex codes (#FF00AA or FF00AA)
    hex_match = re.search(r"#?([0-9a-f]{6})\b", s)
    if hex_match:
        h = hex_match.group(1)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r, g, b), 0, f"Hex #{h.upper()}"

    # 2. rgb(r, g, b)
    rgb_match = re.search(r"rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)", s)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))), 0, f"RGB({r},{g},{b})"

    # 3. Special dynamic modes
    if any(k in s for k in ("rainbow", "color cycle", "color_cycle", "spectrum", "cycle")):
        return (255, 0, 0), 2, "Color Cycle (Rainbow)"
    if "breathing" in s or "breathe" in s:
        # Check if breathing specifies a color (e.g. "breathing blue")
        for name, rgb in _EXTENDED_NAMED_COLORS.items():
            if name != "off" and name != "black" and name in s:
                return rgb, 1, f"Breathing {name.title()}"
        return (0, 255, 255), 1, "Breathing"
    if "strobe" in s or "strobing" in s or "flashing" in s:
        return (255, 255, 255), 3, "Strobe"

    # 4. Standard and extended named colors
    clean_words = re.sub(r"[^a-z0-9]", " ", s).split()
    # Try exact match or phrase match
    combined = "".join(clean_words)
    if combined in _EXTENDED_NAMED_COLORS:
        return _EXTENDED_NAMED_COLORS[combined], 0, combined.title()

    for word in clean_words:
        if word in _EXTENDED_NAMED_COLORS:
            return _EXTENDED_NAMED_COLORS[word], 0, word.title()

    # Substring check for two-word colors like "deep pink", "sky blue", "dark green"
    for name, rgb in _EXTENDED_NAMED_COLORS.items():
        if name in s:
            return rgb, 0, name.title()

    return None, None, None


def cycle_keyboard_backlight(
    target: str | None = None,
    brightness: int | str | None = None,
    mode: int | None = None,
    speed: int = 1,
) -> str:
    """
    Main dispatch function for controlling keyboard backlight lighting and brightness.
    Accepts natural language targets, specific colors, modes, or brightness actions.
    """
    t_clean = (str(target or "")).lower().strip()
    state = _load_current_state()

    # ── 1. Handle Brightness Commands ─────────────────────────────────────────
    # Detect brightness keywords: "low", "dim", "high", "max", "up", "down", "off", "on"
    cur_bright = get_keyboard_brightness()

    if brightness is not None:
        b_str = str(brightness).lower().strip()
        if b_str in ("max", "high", "full", "maximum"):
            set_keyboard_brightness(3)
            return "Keyboard backlight brightness set to Maximum (Level 3)."
        elif b_str in ("medium", "mid", "half"):
            set_keyboard_brightness(2)
            return "Keyboard backlight brightness set to Medium (Level 2)."
        elif b_str in ("low", "dim", "minimum", "min"):
            set_keyboard_brightness(1)
            return "Keyboard backlight brightness set to Low (Level 1)."
        elif b_str in ("off", "zero", "0"):
            set_keyboard_brightness(0)
            return "Keyboard backlight turned Off (Level 0)."
        elif b_str in ("up", "increase", "higher"):
            new_b = min(3, cur_bright + 1)
            set_keyboard_brightness(new_b)
            return f"Keyboard backlight brightness increased to Level {new_b}."
        elif b_str in ("down", "decrease", "lower"):
            new_b = max(0, cur_bright - 1)
            set_keyboard_brightness(new_b)
            return f"Keyboard backlight brightness decreased to Level {new_b}."
        else:
            try:
                lvl = int(b_str)
                set_keyboard_brightness(lvl)
                return f"Keyboard backlight brightness set to Level {lvl}."
            except ValueError:
                pass

    # Check if target itself is a brightness command
    if any(k in t_clean for k in ("low the backlit", "lower the backlit", "dim the backlit", "low brightness", "lower brightness", "dim brightness", "decrease brightness")):
        new_b = max(0, cur_bright - 1) if ("decrease" in t_clean or "lower" in t_clean or "down" in t_clean) else 1
        set_keyboard_brightness(new_b)
        return f"Keyboard backlight brightness lowered to Level {new_b}."

    if any(k in t_clean for k in ("increase brightness", "raise brightness", "brightness up", "brighter", "higher brightness")):
        new_b = min(3, cur_bright + 1)
        set_keyboard_brightness(new_b)
        return f"Keyboard backlight brightness increased to Level {new_b}."

    if any(k in t_clean for k in ("max brightness", "full brightness", "highest brightness")):
        set_keyboard_brightness(3)
        return "Keyboard backlight brightness set to Maximum (Level 3)."

    if t_clean in ("off", "turn off", "turn off backlit", "turn off backlight", "disable backlight"):
        set_keyboard_brightness(0)
        return "Keyboard backlight turned Off."

    if t_clean in ("turn on", "turn on backlit", "turn on backlight", "enable backlight"):
        set_keyboard_brightness(3)
        return "Keyboard backlight turned On (Level 3)."

    # ── 2. Handle Color / Mode Parsing ────────────────────────────────────────
    rgb, detected_mode, name = parse_color_and_mode(t_clean)

    if rgb is not None:
        target_mode = mode if mode is not None else (detected_mode if detected_mode is not None else 0)
        # Ensure backlight is on when changing color
        if cur_bright == 0:
            set_keyboard_brightness(3)

        ok = set_keyboard_color_rgb(rgb[0], rgb[1], rgb[2], mode=target_mode, speed=speed)
        state["color"] = name
        state["mode"] = target_mode
        state["r"] = rgb[0]
        state["g"] = rgb[1]
        state["b"] = rgb[2]
        _save_current_state(state)
        return f"Keyboard backlight color changed to {name} via Fn + F4 (RGB: {rgb[0]}, {rgb[1]}, {rgb[2]})."

    # ── 3. If no specific color or brightness, cycle through presets ───────────
    idx = state.get("preset_index", 0)
    next_idx = (idx + 1) % len(_PRESETS)
    selected_preset = _PRESETS[next_idx]
    state["preset_index"] = next_idx
    state["color"] = selected_preset["name"]
    state["mode"] = selected_preset["mode"]
    _save_current_state(state)

    if cur_bright == 0:
        set_keyboard_brightness(3)

    set_keyboard_color_rgb(
        selected_preset["r"],
        selected_preset["g"],
        selected_preset["b"],
        mode=selected_preset["mode"],
        speed=selected_preset.get("speed", 1),
    )
    return f"Keyboard backlit changed via Fn + F4 (Aura preset: {selected_preset['name']})."
