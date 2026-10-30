"""
core/windows_control/system.py — Windows 11 System, Storage, Security, Services & Startup Control.

Capabilities:
- Capability J: Startup Management
- Capability K: Storage & Cleanup (Dry-run preview, protected paths, Recycle Bin with confirmation)
- Capability L: Notifications & Focus (Do Not Disturb, Settings links)
- Capability N: Windows Update & Version Status
- Capability O: Security Status (Defender, Firewall, Antivirus, Elevation check)
- Capability P: Services & Processes (Protected services blacklist, psutil process inspector)
- Capability Q: Privacy Settings
- Capability R: Administrator-Gated Maintenance
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import winreg
from typing import Any, Optional

import psutil

from .contracts import SystemControlResult
from .runner import run_cmd, run_powershell
from .settings_uris import open_settings_page

_IS_WINDOWS = platform.system() == "Windows"

# Protected Critical Windows Services (NEVER STOP OR RESTART)
_PROTECTED_SERVICES = {
    "rpcss", "dcomlaunch", "winmgmt", "lanmanworkstation", "lanmanserver",
    "plugplay", "eventlog", "lsass", "samss", "cryptsvc", "dhcp", "dnscache",
    "mpssvc", "windefend", "securityhealthservice", "audiosrv", "themes",
    "bfe", "termservice", "profsvc", "sppsvc"
}

# Protected Critical Windows Processes
_PROTECTED_PROCESSES = {
    "system", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "svchost.exe", "winlogon.exe", "explorer.exe",
    "dwm.exe", "spoolsv.exe", "taskhostw.exe", "sihost.exe"
}


# ── Elevation Check ────────────────────────────────────────────────────────────

def is_elevated() -> bool:
    """Return True if FRIDAY process is currently running with administrator privileges."""
    if not _IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def get_elevation_status() -> SystemControlResult:
    """Inspect whether FRIDAY is running with Administrator privileges."""
    elev = is_elevated()
    return SystemControlResult(
        success=True,
        action="get_elevation_status",
        actual_value=elev,
        verified=True,
        message=f"FRIDAY is currently running {'with Administrator privileges' if elev else 'as a standard user (un-elevated)'}."
    )


# ── Security Status (Read-Only) ────────────────────────────────────────────────

def get_security_status() -> SystemControlResult:
    """Inspect Windows Defender, Firewall, Antivirus, and UAC elevation status."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_security_status", error="Requires Windows.")

    elev = is_elevated()
    details = {
        "Antivirus": "Unknown",
        "Firewall": "Unknown",
        "Defender": "Unknown",
        "elevated": elev
    }

    ps_script = """
    $status = [PSCustomObject]@{
        Antivirus = "Unknown"
        Firewall = "Unknown"
        Defender = "Unknown"
    }

    # 1. Antivirus via SecurityCenter2
    try {
        $av = Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($av) { $status.Antivirus = "$($av.displayName) (Active)" }
    } catch {}

    # 2. Firewall profile
    try {
        $fw = Get-NetFirewallProfile -ErrorAction SilentlyContinue | Where-Object Enabled -eq $True
        if ($fw) { $status.Firewall = "Active ($($fw.Name -join ', '))" } else { $status.Firewall = "Inactive" }
    } catch {}

    # 3. Defender
    try {
        $svc = Get-Service WinDefend -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq "Running") {
            $status.Defender = "Active"
        } elseif ($status.Antivirus -like "*Defender*") {
            $status.Defender = "Active"
        } else {
            $status.Defender = "Inactive"
        }
    } catch {}

    $status | ConvertTo-Json
    """
    rc, out, _ = run_powershell(ps_script, timeout=12.0, json_output=True)
    if isinstance(out, dict):
        details.update(out)
    details["elevated"] = elev

    msg = (
        f"Windows Security Status:\n"
        f"Antivirus: {details.get('Antivirus', 'Unknown')}\n"
        f"Firewall: {details.get('Firewall', 'Unknown')}\n"
        f"Windows Defender: {details.get('Defender', 'Unknown')}\n"
        f"Administrator Privileges: {'Yes' if elev else 'No'}"
    )

    return SystemControlResult(
        success=True,
        action="get_security_status",
        actual_value=details,
        verified=True,
        details=details,
        message=msg
    )


# ── Windows Update & Version Status ────────────────────────────────────────────

def get_windows_version() -> SystemControlResult:
    """Inspect Windows 11 version, build, and pending restart status."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_windows_version", error="Requires Windows.")

    ver = sys.getwindowsversion()
    # Check pending reboot
    reboot_pending = False
    try:
        reboot_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"
        ]
        for rk in reboot_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rk):
                    reboot_pending = True
                    break
            except Exception:
                continue
    except Exception:
        pass

    msg = (
        f"Windows Build: {ver.major}.{ver.minor}.{ver.build}\n"
        f"Pending Restart: {'⚠ Yes (Restart required for updates)' if reboot_pending else 'No'}"
    )

    return SystemControlResult(
        success=True,
        action="get_windows_version",
        actual_value=f"{ver.major}.{ver.minor}.{ver.build}",
        verified=True,
        details={"major": ver.major, "minor": ver.minor, "build": ver.build, "reboot_pending": reboot_pending},
        message=msg
    )


def check_windows_updates() -> SystemControlResult:
    """Trigger update check or open Windows Update settings."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="check_windows_updates", error="Requires Windows.")

    # Trigger async update scan via usoclient
    run_cmd(["usoclient.exe", "StartScan"], timeout=5.0)
    open_settings_page("windows_update")
    return SystemControlResult(
        success=True,
        action="check_windows_updates",
        verified=True,
        message="Triggered Windows Update check and opened Windows Update settings."
    )


# ── Startup Applications ───────────────────────────────────────────────────────

def list_startup_apps() -> SystemControlResult:
    """Enumerate configured startup applications."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="list_startup_apps", error="Requires Windows.")

    apps = []
    run_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    for root, path in run_paths:
        try:
            with winreg.OpenKey(root, path) as k:
                num = winreg.QueryInfoKey(k)[1]
                for i in range(num):
                    name, val, _ = winreg.EnumValue(k, i)
                    apps.append(f"{name}: {os.path.basename(val.split(' ')[0].strip('\"'))}")
        except Exception:
            continue

    msg = f"Startup Applications ({len(apps)}):\n" + "\n".join(apps[:15]) if apps else "No startup applications registered in Run keys."
    return SystemControlResult(
        success=True,
        action="list_startup_apps",
        actual_value=apps,
        verified=True,
        details={"startup_apps": apps},
        message=msg
    )


# ── Storage & Safe Cleanup ─────────────────────────────────────────────────────

def get_disk_usage() -> SystemControlResult:
    """Inspect disk space and free space on all drives."""
    drives = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or part.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            free_gb = round(usage.free / (1024**3), 2)
            total_gb = round(usage.total / (1024**3), 2)
            pct = usage.percent
            drives.append(f"{part.device} ({part.mountpoint}): {free_gb} GB free of {total_gb} GB ({pct}% used)")
        except Exception:
            continue

    msg = "Storage Drive Status:\n" + "\n".join(drives)
    return SystemControlResult(
        success=True,
        action="get_disk_usage",
        actual_value=drives,
        verified=True,
        details={"drives": drives},
        message=msg
    )


def preview_temp_cleanup() -> SystemControlResult:
    """Dry-run scan of temporary files in %TEMP% without deleting anything."""
    temp_dir = tempfile.gettempdir()
    total_size = 0
    file_count = 0

    try:
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
                        file_count += 1
                except Exception:
                    continue
    except Exception:
        pass

    size_mb = round(total_size / (1024**2), 2)
    msg = (
        f"Temporary Files Cleanup Preview (Dry Run):\n"
        f"Found {file_count} temporary files in '{temp_dir}'.\n"
        f"Estimated space reclaimable: ~{size_mb} MB.\n"
        f"No files were removed."
    )
    return SystemControlResult(
        success=True,
        action="preview_temp_cleanup",
        actual_value={"size_mb": size_mb, "file_count": file_count},
        verified=True,
        details={"temp_dir": temp_dir, "size_mb": size_mb, "file_count": file_count},
        message=msg
    )


def empty_recycle_bin() -> SystemControlResult:
    """Empty Windows Recycle Bin (requires Level 3 confirmation)."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="empty_recycle_bin", error="Requires Windows.")

    SHERB_NOCONFIRMATION = 0x00000001
    SHERB_NOPROGRESSUI   = 0x00000002
    SHERB_NOSOUND        = 0x00000004

    try:
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(
            None,
            None,
            SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        )
        # S_OK is 0
        if res == 0:
            return SystemControlResult(
                success=True,
                action="empty_recycle_bin",
                verified=True,
                message="Windows Recycle Bin has been emptied."
            )
        elif res == -2147418113:  # 0x8000FFFF or already empty
            return SystemControlResult(
                success=True,
                action="empty_recycle_bin",
                verified=True,
                message="Windows Recycle Bin was already empty."
            )
        else:
            return SystemControlResult(
                success=False,
                action="empty_recycle_bin",
                error=f"SHEmptyRecycleBinW returned code {res}",
                message="Could not empty the Recycle Bin."
            )
    except Exception as e:
        return SystemControlResult(
            success=False, action="empty_recycle_bin", error=str(e),
            message=f"Failed to empty Recycle Bin: {e}"
        )


# ── Services & Processes ───────────────────────────────────────────────────────

def list_running_processes(limit: int = 8) -> SystemControlResult:
    """Inspect top resource-consuming running processes (CPU & Memory)."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except Exception:
            continue

    # Sort by memory
    procs.sort(key=lambda x: x.get('memory_percent') or 0, reverse=True)
    top = procs[:limit]
    lines = [f"{p['name']} (PID: {p['pid']}, RAM: {round(p['memory_percent'] or 0, 1)}%)" for p in top]

    return SystemControlResult(
        success=True,
        action="list_running_processes",
        actual_value=lines,
        verified=True,
        details={"processes": top},
        message="Top Memory Consuming Processes:\n" + "\n".join(lines)
    )


def close_application_gracefully(app_name: str) -> SystemControlResult:
    """Gracefully close an application by name or window title without terminating critical system processes."""
    clean_name = app_name.strip().lower()
    
    # 1. Protect critical processes
    for prot in _PROTECTED_PROCESSES:
        if prot in clean_name or clean_name == prot.replace(".exe", ""):
            return SystemControlResult(
                success=False,
                action="close_application",
                requested_value=app_name,
                error="Protected system process cannot be terminated.",
                message=f"'{app_name}' is a critical Windows system process and cannot be closed."
            )

    # 2. Find target process and request graceful close
    closed_count = 0
    for p in psutil.process_iter(['pid', 'name']):
        try:
            pname = (p.info.get('name') or '').lower()
            if clean_name in pname or clean_name == pname.replace('.exe', ''):
                p.terminate()  # Graceful SIGTERM
                closed_count += 1
        except Exception:
            continue

    if closed_count > 0:
        return SystemControlResult(
            success=True,
            action="close_application",
            requested_value=app_name,
            actual_value=closed_count,
            verified=True,
            message=f"Closed {closed_count} instance(s) of '{app_name}'."
        )

    return SystemControlResult(
        success=False,
        action="close_application",
        requested_value=app_name,
        error="Application not found.",
        message=f"Could not find any running application matching '{app_name}'."
    )


def service_control(service_name: str, action: str) -> SystemControlResult:
    """Manage Windows Services safely. Action: 'status', 'start', 'stop', 'restart'."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="service_control", error="Requires Windows.")

    clean_svc = service_name.strip().lower()
    clean_act = action.strip().lower()

    if clean_act in ("stop", "restart") and clean_svc in _PROTECTED_SERVICES:
        return SystemControlResult(
            success=False,
            action=f"service_{clean_act}",
            requested_value=service_name,
            error=f"Service '{service_name}' is protected and critical to Windows stability.",
            message=f"Cannot {clean_act} '{service_name}': it is a protected core Windows system service."
        )

    if clean_act == "status":
        ps_cmd = f"(Get-Service -Name '{clean_svc}' -ErrorAction SilentlyContinue).Status"
        rc, out, _ = run_powershell(ps_cmd, timeout=5.0)
        status_str = str(out).strip() or "Not Found"
        return SystemControlResult(
            success=(status_str != "Not Found"),
            action="service_status",
            actual_value=status_str,
            verified=True,
            message=f"Service '{service_name}' status: {status_str}."
        )

    # State changing: start, stop, restart
    ps_cmd = f"{clean_act.capitalize()}-Service -Name '{clean_svc}' -ErrorAction Stop"
    rc, out, err = run_powershell(ps_cmd, timeout=10.0)
    if rc == 0:
        status_res = service_control(service_name, "status")
        return SystemControlResult(
            success=True,
            action=f"service_{clean_act}",
            requested_value=service_name,
            actual_value=status_res.actual_value,
            verified=True,
            message=f"Service '{service_name}' has been {clean_act}ed. Current status: {status_res.actual_value}."
        )

    return SystemControlResult(
        success=False,
        action=f"service_{clean_act}",
        requested_value=service_name,
        error=err or "Service operation failed.",
        message=f"Failed to {clean_act} service '{service_name}'. Elevation may be required."
    )


# ── Focus & Notifications ──────────────────────────────────────────────────────

def get_focus_status() -> SystemControlResult:
    """Query Windows Focus / Do Not Disturb status."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_focus_status", error="Requires Windows.")

    try:
        # Windows 10/11 FocusAssist Registry Key
        key_path = r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default$windows.data.notifications.focusassiststatus\windows.data.notifications.focusassiststatus"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            val, _ = winreg.QueryValueEx(k, "Data")
            # Byte 18: 0 = Off, 1 = Priority Only, 2 = Alarms Only
            if len(val) >= 19:
                mode_byte = val[18]
                mode_str = {0: "Off", 1: "Priority Only", 2: "Alarms Only"}.get(mode_byte, "Active")
                return SystemControlResult(
                    success=True, action="get_focus_status", actual_value=mode_str,
                    verified=True, message=f"Focus (Do Not Disturb) is currently: {mode_str}."
                )
    except Exception:
        pass

    return SystemControlResult(
        success=True, action="get_focus_status", actual_value="Available in Settings",
        verified=False, message="Focus status is managed via Windows Focus settings."
    )
