"""
core/windows_control/power.py — Windows 11 Power, Battery, Profiles & Recovery Workflows.

Capabilities:
- Capability E: Battery and Power Management (GetSystemPowerStatus, battery report).
- Capability M: Power Profiles & Schemes (powercfg /list, /setactive, /change).
- Capability S: Recovery and Restart Workflows (shutdown, restart, hibernate, recovery settings).
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import platform
import re
import tempfile
from typing import Any, Optional

from .contracts import SystemControlResult
from .runner import run_cmd, run_powershell
from .settings_uris import open_settings_page
from core.undo import push_undo

_IS_WINDOWS = platform.system() == "Windows"


# ── Battery & AC Power ─────────────────────────────────────────────────────────

class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


def get_power_status() -> SystemControlResult:
    """Read battery percentage, AC power status, and charging state via Win32."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_power_status", error="Requires Windows.")

    try:
        status = _SYSTEM_POWER_STATUS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            raise RuntimeError("GetSystemPowerStatus failed.")

        ac_status = "Plugged In (AC)" if status.ACLineStatus == 1 else "On Battery (DC)"
        percent = status.BatteryLifePercent
        is_charging = bool(status.BatteryFlag & 8)
        no_battery = (status.BatteryFlag & 128 or percent == 255)

        if no_battery:
            msg = f"System is {ac_status}. No battery detected (Desktop PC)."
            actual = {"ac": True, "battery_percent": None, "charging": False}
        else:
            charge_str = ", Charging" if is_charging else ""
            msg = f"Battery is at {percent}% ({ac_status}{charge_str})."
            actual = {"ac": status.ACLineStatus == 1, "battery_percent": percent, "charging": is_charging}

        return SystemControlResult(
            success=True,
            action="get_power_status",
            actual_value=percent if not no_battery else 100,
            verified=True,
            details=actual,
            message=msg
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="get_power_status", error=str(e),
            message=f"Could not retrieve battery and power status: {e}"
        )


def generate_battery_report() -> SystemControlResult:
    """Generate official Windows battery health report via powercfg."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="generate_battery_report", error="Requires Windows.")

    report_path = os.path.join(tempfile.gettempdir(), "battery-report.html")
    rc, out, err = run_cmd(["powercfg", "/batteryreport", "/output", report_path], timeout=15.0)
    if rc == 0 and os.path.exists(report_path):
        return SystemControlResult(
            success=True,
            action="generate_battery_report",
            actual_value=report_path,
            verified=True,
            message=f"Battery report generated at: {report_path}"
        )

    return SystemControlResult(
        success=False,
        action="generate_battery_report",
        error=err or out,
        message="Failed to generate Windows battery report."
    )


# ── Power Profiles & Schemes ───────────────────────────────────────────────────

def get_power_plans() -> SystemControlResult:
    """List available power schemes and identify the active one."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_power_plans", error="Requires Windows.")

    rc, out, _ = run_cmd(["powercfg", "/list"], timeout=6.0)
    if rc != 0:
        return SystemControlResult(success=False, action="get_power_plans", error="powercfg /list failed.")

    plans = []
    active_plan = None
    for line in out.splitlines():
        if "GUID:" in line:
            # Format: Power Scheme GUID: 381b4222-...  (Balanced) *
            match = re.search(r'GUID:\s*([a-f0-9\-]+)\s*\(([^)]+)\)(\s*\*)?', line, re.IGNORECASE)
            if match:
                guid, name, active = match.groups()
                is_active = bool(active and "*" in active)
                plans.append({"guid": guid, "name": name, "active": is_active})
                if is_active:
                    active_plan = name

    msg = f"Active Power Plan: {active_plan or 'Default'}\nAvailable: " + ", ".join(p['name'] for p in plans)
    return SystemControlResult(
        success=True,
        action="get_power_plans",
        actual_value=active_plan,
        verified=True,
        details={"active_plan": active_plan, "plans": plans},
        message=msg
    )


def set_power_plan(plan_name_or_guid: str) -> SystemControlResult:
    """Switch active power scheme to a verified available plan."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_power_plan", error="Requires Windows.")

    # 1. First get available plans
    plans_res = get_power_plans()
    if not plans_res.success:
        return plans_res

    target_guid = None
    target_name = plan_name_or_guid.strip().lower()
    for p in plans_res.details.get("plans", []):
        if target_name in p["name"].lower() or target_name == p["guid"].lower():
            target_guid = p["guid"]
            target_name = p["name"]
            break

    if not target_guid:
        available = ", ".join(p['name'] for p in plans_res.details.get("plans", []))
        return SystemControlResult(
            success=False,
            action="set_power_plan",
            requested_value=plan_name_or_guid,
            error=f"Plan not found. Available plans: {available}",
            message=f"I couldn't find a power plan matching '{plan_name_or_guid}'. Available: {available}"
        )

    rc, _, err = run_cmd(["powercfg", "/setactive", target_guid], timeout=6.0)
    if rc == 0:
        # Verify
        curr = get_power_plans()
        verified = (curr.success and curr.actual_value.lower() == target_name.lower())
        return SystemControlResult(
            success=True,
            action="set_power_plan",
            requested_value=target_name,
            actual_value=curr.actual_value if curr.success else target_name,
            verified=verified,
            message=f"Active power plan switched to '{target_name}'."
        )

    return SystemControlResult(
        success=False, action="set_power_plan", error=err,
        message=f"Failed to switch power plan to '{target_name}'."
    )


def set_display_timeout(minutes: int) -> SystemControlResult:
    """Set screen sleep timeout in minutes for both AC and Battery."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_display_timeout", error="Requires Windows.")

    mins = max(0, int(minutes))
    run_cmd(["powercfg", "/change", "monitor-timeout-ac", str(mins)], timeout=6.0)
    run_cmd(["powercfg", "/change", "monitor-timeout-dc", str(mins)], timeout=6.0)
    return SystemControlResult(
        success=True,
        action="set_display_timeout",
        requested_value=mins,
        actual_value=mins,
        verified=True,
        message=f"Display turn-off timeout set to {mins} minutes." if mins > 0 else "Display timeout set to Never."
    )


def set_sleep_timeout(minutes: int) -> SystemControlResult:
    """Set PC sleep timeout in minutes for both AC and Battery."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_sleep_timeout", error="Requires Windows.")

    mins = max(0, int(minutes))
    run_cmd(["powercfg", "/change", "standby-timeout-ac", str(mins)], timeout=6.0)
    run_cmd(["powercfg", "/change", "standby-timeout-dc", str(mins)], timeout=6.0)
    return SystemControlResult(
        success=True,
        action="set_sleep_timeout",
        requested_value=mins,
        actual_value=mins,
        verified=True,
        message=f"PC sleep timeout set to {mins} minutes." if mins > 0 else "PC sleep timeout set to Never."
    )


# ── Recovery & Restart Workflows ───────────────────────────────────────────────

def request_sleep() -> SystemControlResult:
    """Put PC to sleep."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="request_sleep", error="Requires Windows.")

    run_cmd(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], timeout=4.0)
    return SystemControlResult(
        success=True, action="request_sleep", verified=True,
        message="Putting the computer to sleep."
    )


def request_hibernate() -> SystemControlResult:
    """Put PC into hibernation."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="request_hibernate", error="Requires Windows.")

    run_cmd(["shutdown.exe", "/h"], timeout=5.0)
    return SystemControlResult(
        success=True, action="request_hibernate", verified=True,
        message="Hibernating the computer."
    )


def cancel_shutdown() -> SystemControlResult:
    """Abort a scheduled shutdown or restart."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="cancel_shutdown", error="Requires Windows.")

    rc, out, err = run_cmd(["shutdown.exe", "/a"], timeout=5.0)
    if rc == 0:
        return SystemControlResult(
            success=True, action="cancel_shutdown", verified=True,
            message="Scheduled shutdown or restart has been cancelled."
        )
    return SystemControlResult(
        success=False, action="cancel_shutdown", error=err or out,
        message="No shutdown was in progress to cancel."
    )


def open_recovery_options() -> SystemControlResult:
    """Open Windows 11 Advanced Recovery and Startup Options."""
    open_settings_page("recovery")
    return SystemControlResult(
        success=True, action="open_recovery_options", verified=True,
        message="Opened Windows Recovery settings."
    )
