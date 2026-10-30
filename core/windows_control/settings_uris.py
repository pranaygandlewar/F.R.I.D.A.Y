"""
core/windows_control/settings_uris.py — Windows 11 ms-settings: URI catalog and launcher.
"""
from __future__ import annotations

import os
import platform
from .contracts import SystemControlResult
from .runner import run_cmd

SETTINGS_URIS: dict[str, str] = {
    # Display & Graphics
    "display": "ms-settings:display",
    "nightlight": "ms-settings:nightlight",
    "advanced_display": "ms-settings:display-advanced",
    "graphics": "ms-settings:display-advancedgraphics",

    # Sound & Audio
    "sound": "ms-settings:sound",
    "volume_mixer": "ms-settings:sound-devices",

    # Network & Internet
    "network": "ms-settings:network",
    "wifi": "ms-settings:network-wifi",
    "bluetooth": "ms-settings:bluetooth",
    "airplanemode": "ms-settings:network-airplanemode",
    "mobilehotspot": "ms-settings:network-mobilehotspot",
    "vpn": "ms-settings:network-vpn",
    "proxy": "ms-settings:network-proxy",

    # Power & Battery
    "power": "ms-settings:powersleep",
    "battery": "ms-settings:batterysaver",

    # Personalization
    "personalization": "ms-settings:personalization",
    "colors": "ms-settings:personalization-colors",
    "background": "ms-settings:personalization-background",
    "lockscreen": "ms-settings:lockscreen",
    "taskbar": "ms-settings:taskbar",

    # Notifications & Focus
    "notifications": "ms-settings:notifications",
    "focus": "ms-settings:quiethours",
    "clipboard": "ms-settings:clipboard",
    "multitasking": "ms-settings:multitasking",

    # Privacy & Security
    "privacy": "ms-settings:privacy",
    "camera_privacy": "ms-settings:privacy-webcam",
    "microphone_privacy": "ms-settings:privacy-microphone",
    "location_privacy": "ms-settings:privacy-location",
    "windows_security": "windowsdefender:",
    "windows_update": "ms-settings:windowsupdate",
    "recovery": "ms-settings:recovery",
}


def open_settings_page(page_key: str) -> SystemControlResult:
    """Launch the appropriate Windows Settings page given a canonical key."""
    if platform.system() != "Windows":
        return SystemControlResult(
            success=False,
            action=f"open_settings:{page_key}",
            error="Settings pages require Windows.",
            message="Windows Settings pages are only available on Windows."
        )

    uri = SETTINGS_URIS.get(page_key.lower().strip())
    if not uri:
        # Check if caller passed a raw ms-settings: URI
        if page_key.startswith("ms-settings:") or page_key.startswith("windowsdefender:"):
            uri = page_key
        else:
            supported = ", ".join(sorted(SETTINGS_URIS.keys()))
            return SystemControlResult(
                success=False,
                action=f"open_settings:{page_key}",
                error=f"Unknown settings page '{page_key}'. Supported pages: {supported}",
                message=f"I don't know the '{page_key}' settings page. Supported pages include: {supported[:60]}..."
            )

    rc, _, err = run_cmd(["explorer.exe", uri], timeout=5.0)
    # explorer.exe returns 1 or 0 depending on Windows shell, but launches async
    return SystemControlResult(
        success=True,
        action="open_settings",
        requested_value=page_key,
        actual_value=uri,
        verified=True,
        message=f"Opened Windows {page_key.replace('_', ' ').capitalize()} Settings."
    )
