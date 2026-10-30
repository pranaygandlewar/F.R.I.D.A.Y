"""
core/windows_control — Modular Windows 11 Advanced System Control Layer for FRIDAY.
"""
from __future__ import annotations

from .contracts import SystemControlResult
from .settings_uris import open_settings_page, SETTINGS_URIS
from .audio import (
    get_volume, set_volume, change_volume, get_mute_state, set_mute, toggle_mute,
    list_audio_devices, set_default_audio_device, get_mic_level, set_mic_level
)
from .display import (
    get_brightness, set_brightness, change_brightness, enumerate_displays,
    switch_projection_mode, get_night_light_status, toggle_night_light, get_gpu_info
)
from .network import (
    get_wifi_status, list_wifi_networks, connect_wifi, disconnect_wifi, set_wifi_state,
    get_bluetooth_status, set_bluetooth_state, list_bluetooth_devices,
    get_hotspot_status, toggle_hotspot, get_airplane_mode_status,
    run_network_diagnostics, flush_dns, list_vpn_connections, is_active_session_adapter
)
from .power import (
    get_power_status, generate_battery_report, get_power_plans, set_power_plan,
    set_display_timeout, set_sleep_timeout, request_sleep, request_hibernate,
    cancel_shutdown, open_recovery_options
)
from .personalization import (
    get_theme_status, set_theme, toggle_theme, set_wallpaper, get_transparency_status
)
from .system import (
    is_elevated, get_elevation_status, get_security_status, get_windows_version,
    check_windows_updates, list_startup_apps, get_disk_usage, preview_temp_cleanup,
    empty_recycle_bin, list_running_processes, close_application_gracefully,
    service_control, get_focus_status
)

__all__ = [
    "SystemControlResult",
    "open_settings_page",
    "SETTINGS_URIS",
    # Audio
    "get_volume", "set_volume", "change_volume", "get_mute_state", "set_mute", "toggle_mute",
    "list_audio_devices", "set_default_audio_device", "get_mic_level", "set_mic_level",
    # Display
    "get_brightness", "set_brightness", "change_brightness", "enumerate_displays",
    "switch_projection_mode", "get_night_light_status", "toggle_night_light", "get_gpu_info",
    # Network
    "get_wifi_status", "list_wifi_networks", "connect_wifi", "disconnect_wifi", "set_wifi_state",
    "get_bluetooth_status", "set_bluetooth_state", "list_bluetooth_devices",
    "get_hotspot_status", "toggle_hotspot", "get_airplane_mode_status",
    "run_network_diagnostics", "flush_dns", "list_vpn_connections", "is_active_session_adapter",
    # Power
    "get_power_status", "generate_battery_report", "get_power_plans", "set_power_plan",
    "set_display_timeout", "set_sleep_timeout", "request_sleep", "request_hibernate",
    "cancel_shutdown", "open_recovery_options",
    # Personalization
    "get_theme_status", "set_theme", "toggle_theme", "set_wallpaper", "get_transparency_status",
    # System
    "is_elevated", "get_elevation_status", "get_security_status", "get_windows_version",
    "check_windows_updates", "list_startup_apps", "get_disk_usage", "preview_temp_cleanup",
    "empty_recycle_bin", "list_running_processes", "close_application_gracefully",
    "service_control", "get_focus_status",
]
