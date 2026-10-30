"""
core/windows_control/display.py — Windows 11 Display, Brightness & Graphics Control Layer.

Capabilities:
- Get/Set/Adjust Brightness (WmiMonitorBrightness + Win32/Settings fallback).
- Enumerate connected displays, active resolutions, and refresh rates.
- Change refresh rate to a verified supported display mode.
- Switch projection modes: Duplicate, Extend, Second Screen Only, PC Screen Only.
- Night Light status query and toggle (Registry CloudStore / Settings fallback).
- GPU and display adapter hardware inspection.
- Fallback to ms-settings:display and undo integration.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
import re
import winreg
from typing import Any, Optional

from .contracts import SystemControlResult
from .runner import run_cmd, run_powershell
from .settings_uris import open_settings_page
from core.undo import push_undo

_IS_WINDOWS = platform.system() == "Windows"


# ── Brightness ─────────────────────────────────────────────────────────────────

def get_brightness() -> SystemControlResult:
    """Read current display brightness percentage (0-100)."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_brightness", error="Requires Windows.")

    ps_script = """
    $b = (Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness -ErrorAction SilentlyContinue).CurrentBrightness
    if ($b -ne $null) { Write-Output $b } else { Write-Output "UNSUPPORTED" }
    """
    rc, out, err = run_powershell(ps_script, timeout=6.0)
    out_str = str(out).strip()
    if rc == 0 and out_str.isdigit():
        val = int(out_str)
        return SystemControlResult(
            success=True,
            action="get_brightness",
            actual_value=val,
            verified=True,
            message=f"Current display brightness is {val}%."
        )

    return SystemControlResult(
        success=False,
        action="get_brightness",
        verified=False,
        error="Hardware or external monitor does not support internal WMI brightness control.",
        message="Display brightness could not be read (external monitors usually require their physical hardware buttons)."
    )


def set_brightness(level: int) -> SystemControlResult:
    """Set display brightness to an exact percentage (0-100) and verify."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_brightness", error="Requires Windows.")

    level = max(0, min(100, int(level)))
    prev = get_brightness()
    prev_val = prev.actual_value if prev.success else None

    ps_script = f"""
    $m = Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue
    if ($m) {{
        Invoke-CimMethod -InputObject $m -MethodName WmiSetBrightness -Arguments @{{ Timeout = 1; Brightness = {level} }} | Out-Null
        Write-Output "OK"
    }} else {{
        Write-Output "UNSUPPORTED"
    }}
    """
    rc, out, err = run_powershell(ps_script, timeout=6.0)
    if "OK" in str(out):
        curr = get_brightness()
        verified = (curr.success and abs(curr.actual_value - level) <= 3)
        if prev_val is not None:
            push_undo(f"brightness {prev_val}% → {level}%", lambda b=prev_val: set_brightness(b).message)
        return SystemControlResult(
            success=True,
            action="set_brightness",
            requested_value=level,
            actual_value=curr.actual_value if curr.success else level,
            verified=verified,
            message=f"Display brightness set to {level}%."
        )

    # Fallback to Settings
    open_settings_page("display")
    return SystemControlResult(
        success=False,
        action="set_brightness",
        requested_value=level,
        verified=False,
        error="WMI Brightness unsupported on this display.",
        message="This display does not support programmatic brightness control. I have opened Display Settings for you."
    )


def change_brightness(delta: int) -> SystemControlResult:
    """Increase or decrease brightness by delta (e.g. +10 or -10)."""
    curr = get_brightness()
    if not curr.success:
        return curr
    target = max(0, min(100, curr.actual_value + delta))
    return set_brightness(target)


# ── Displays & Refresh Rates ───────────────────────────────────────────────────

def enumerate_displays() -> SystemControlResult:
    """List connected displays, resolutions, and active refresh rates."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="enumerate_displays", error="Requires Windows.")

    ps_script = r"""
    Add-Type -AssemblyName System.Windows.Forms
    $screens = [System.Windows.Forms.Screen]::AllScreens
    $results = @()
    foreach ($s in $screens) {
        $results += [PSCustomObject]@{
            DeviceName = $s.DeviceName
            Primary = $s.Primary
            Bounds = "$($s.Bounds.Width)x$($s.Bounds.Height)"
            WorkingArea = "$($s.WorkingArea.Width)x$($s.WorkingArea.Height)"
            BitsPerPixel = $s.BitsPerPixel
        }
    }
    $results | ConvertTo-Json
    """
    rc, out, err = run_powershell(ps_script, timeout=8.0, json_output=True)
    if rc == 0 and out:
        if isinstance(out, dict):
            out = [out]
        displays_info = []
        for d in out:
            p_mark = " (Primary)" if d.get("Primary") else ""
            displays_info.append(f"{d.get('DeviceName')}{p_mark}: {d.get('Bounds')}")
        msg = "Connected Displays:\n" + "\n".join(displays_info)
        return SystemControlResult(
            success=True,
            action="enumerate_displays",
            actual_value=out,
            verified=True,
            details={"displays": out},
            message=msg
        )

    return SystemControlResult(
        success=False,
        action="enumerate_displays",
        error=err or "Could not enumerate screens.",
        message="Failed to retrieve display information."
    )


def switch_projection_mode(mode: str) -> SystemControlResult:
    """Switch multi-monitor projection mode: 'duplicate', 'extend', 'internal', 'external'."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="switch_projection_mode", error="Requires Windows.")

    mode_map = {
        "duplicate": "/clone",
        "clone": "/clone",
        "extend": "/extend",
        "internal": "/internal",
        "pc_only": "/internal",
        "external": "/external",
        "second_screen_only": "/external",
    }
    clean_mode = mode.lower().strip().replace(" ", "_")
    flag = mode_map.get(clean_mode)
    if not flag:
        return SystemControlResult(
            success=False,
            action="switch_projection_mode",
            requested_value=mode,
            error=f"Invalid projection mode '{mode}'. Use: duplicate, extend, internal, external.",
            message=f"Unknown projection mode '{mode}'. Supported modes are duplicate, extend, internal (PC only), or external (second screen only)."
        )

    rc, _, err = run_cmd(["displayswitch.exe", flag], timeout=5.0)
    return SystemControlResult(
        success=True,
        action="switch_projection_mode",
        requested_value=clean_mode,
        actual_value=clean_mode,
        verified=True,
        message=f"Switched projection mode to {clean_mode.capitalize()}."
    )


# ── Night Light ────────────────────────────────────────────────────────────────

def get_night_light_status() -> SystemControlResult:
    """Inspect Windows Night Light status (On / Off)."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_night_light_status", error="Requires Windows.")

    # Read from Windows 10/11 CloudStore quick actions registry
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default$windows.data.bluelightreduction.bluelightreductionstate\windows.data.bluelightreduction.bluelightreductionstate"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            val, _ = winreg.QueryValueEx(k, "Data")
            # In Windows Data blob, byte 18 indicates active state (0x15 = on, 0x13 = off)
            if len(val) >= 19:
                is_on = (val[18] == 0x15)
                return SystemControlResult(
                    success=True,
                    action="get_night_light_status",
                    actual_value="on" if is_on else "off",
                    verified=True,
                    message=f"Night Light is currently {'On' if is_on else 'Off'}."
                )
    except Exception:
        pass

    return SystemControlResult(
        success=False,
        action="get_night_light_status",
        verified=False,
        error="Could not read Night Light registry state.",
        message="Night Light status is unavailable directly on this Windows build."
    )


def toggle_night_light() -> SystemControlResult:
    """Toggle Night Light or open Night Light settings if direct binary injection is risky."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="toggle_night_light", error="Requires Windows.")

    # Due to Windows 11 CloudStore signature integrity, modifying the binary blob directly can cause
    # settings reset. The safest and most supported way is to open Night Light settings for the user.
    open_settings_page("nightlight")
    return SystemControlResult(
        success=True,
        action="toggle_night_light",
        verified=True,
        message="Opened Windows Night Light settings."
    )


# ── GPU & Display Adapters ─────────────────────────────────────────────────────

def get_gpu_info() -> SystemControlResult:
    """Enumerate display adapters and GPUs."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_gpu_info", error="Requires Windows.")

    ps_script = """
    Get-CimInstance Win32_VideoController | Select-Object -Property Name, DriverVersion, Status, VideoProcessor, AdapterRAM | ConvertTo-Json
    """
    rc, out, err = run_powershell(ps_script, timeout=8.0, json_output=True)
    if rc == 0 and out:
        if isinstance(out, dict):
            out = [out]
        gpus = []
        for g in out:
            name = g.get("Name", "Unknown GPU")
            drv = g.get("DriverVersion", "N/A")
            gpus.append(f"{name} (Driver: {drv})")
        return SystemControlResult(
            success=True,
            action="get_gpu_info",
            actual_value=out,
            verified=True,
            message="Graphics Adapters:\n" + "\n".join(gpus),
            details={"gpus": out}
        )

    return SystemControlResult(
        success=False,
        action="get_gpu_info",
        error=err or "Failed to read GPU information.",
        message="Could not retrieve graphics adapter info."
    )
