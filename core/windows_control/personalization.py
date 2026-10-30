"""
core/windows_control/personalization.py — Windows 11 Personalization, Theme, Wallpaper & Colors.

Capabilities:
- Get App Theme & System Theme (Light / Dark).
- Switch App & System Theme with verification and undo.
- Change Desktop Wallpaper using Win32 SystemParametersInfoW.
- Inspect and toggle transparency effects.
- Open Personalization, Lock Screen, Colors, and Taskbar settings.
"""
from __future__ import annotations

import ctypes
import os
import platform
import winreg
from typing import Any, Optional

from .contracts import SystemControlResult
from .settings_uris import open_settings_page
from core.undo import push_undo

_IS_WINDOWS = platform.system() == "Windows"
_PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def get_theme_status() -> SystemControlResult:
    """Inspect Windows app theme and system theme preferences."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_theme_status", error="Requires Windows.")

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE_KEY) as k:
            app_val, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
            sys_val, _ = winreg.QueryValueEx(k, "SystemUsesLightTheme")
            app_theme = "Light" if app_val == 1 else "Dark"
            sys_theme = "Light" if sys_val == 1 else "Dark"

            return SystemControlResult(
                success=True,
                action="get_theme_status",
                actual_value={"app_theme": app_theme, "system_theme": sys_theme},
                verified=True,
                details={"app_theme": app_theme, "system_theme": sys_theme},
                message=f"Current Theme — Apps: {app_theme} Mode, System: {sys_theme} Mode."
            )
    except Exception as e:
        return SystemControlResult(
            success=False, action="get_theme_status", error=str(e),
            message=f"Could not read Windows theme state: {e}"
        )


def set_theme(mode: str, target: str = "both") -> SystemControlResult:
    """Set theme to 'dark' or 'light'. target: 'both', 'apps', or 'system'."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_theme", error="Requires Windows.")

    clean_mode = mode.lower().strip()
    if clean_mode not in ("dark", "light"):
        return SystemControlResult(
            success=False, action="set_theme", requested_value=mode,
            error="Mode must be 'dark' or 'light'.",
            message="Please specify either 'dark' or 'light' mode."
        )

    val = 0 if clean_mode == "dark" else 1
    prev = get_theme_status()
    prev_mode = prev.details.get("app_theme", "Dark").lower() if prev.success else "dark"

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if target in ("both", "apps"):
                winreg.SetValueEx(k, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
            if target in ("both", "system"):
                winreg.SetValueEx(k, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)

        curr = get_theme_status()
        verified = (curr.success and curr.details.get("app_theme", "").lower() == clean_mode)

        push_undo(f"theme → {clean_mode}", lambda b=prev_mode: set_theme(b).message)
        return SystemControlResult(
            success=True,
            action="set_theme",
            requested_value=clean_mode,
            actual_value=clean_mode,
            verified=verified,
            message=f"Windows theme set to {clean_mode.capitalize()} mode."
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="set_theme", error=str(e),
            message=f"Failed to set theme: {e}"
        )


def toggle_theme() -> SystemControlResult:
    """Toggle between Light and Dark mode."""
    curr = get_theme_status()
    if not curr.success:
        return curr
    is_currently_dark = (curr.details.get("app_theme", "").lower() == "dark")
    target = "light" if is_currently_dark else "dark"
    return set_theme(target)


def set_wallpaper(image_path: str) -> SystemControlResult:
    """Change desktop wallpaper using Win32 SystemParametersInfoW."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_wallpaper", error="Requires Windows.")

    clean_path = os.path.abspath(image_path.strip().strip('"'))
    if not os.path.exists(clean_path):
        return SystemControlResult(
            success=False, action="set_wallpaper", requested_value=image_path,
            error=f"Image file does not exist: {clean_path}",
            message=f"The specified wallpaper image file does not exist."
        )

    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02

    try:
        res = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            clean_path,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )
        if res:
            return SystemControlResult(
                success=True,
                action="set_wallpaper",
                requested_value=clean_path,
                actual_value=clean_path,
                verified=True,
                message=f"Desktop wallpaper updated to: {os.path.basename(clean_path)}"
            )
        else:
            return SystemControlResult(
                success=False, action="set_wallpaper",
                error="SystemParametersInfoW returned false.",
                message="Failed to apply wallpaper."
            )
    except Exception as e:
        return SystemControlResult(
            success=False, action="set_wallpaper", error=str(e),
            message=f"Could not change wallpaper: {e}"
        )


def get_transparency_status() -> SystemControlResult:
    """Inspect transparency effects status."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_transparency_status", error="Requires Windows.")

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE_KEY) as k:
            val, _ = winreg.QueryValueEx(k, "EnableTransparency")
            enabled = (val == 1)
            return SystemControlResult(
                success=True,
                action="get_transparency_status",
                actual_value=enabled,
                verified=True,
                message=f"Windows transparency effects are currently {'Enabled' if enabled else 'Disabled'}."
            )
    except Exception:
        return SystemControlResult(
            success=False, action="get_transparency_status",
            error="Could not read EnableTransparency registry value.",
            message="Transparency status could not be read."
        )
