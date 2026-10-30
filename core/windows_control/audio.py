"""
core/windows_control/audio.py — Windows 11 Audio Control & Verification Layer.

Capabilities:
- Get/Set/Increase/Decrease master volume.
- Mute / Unmute / Query mute state via PyCAW IAudioEndpointVolume.
- Enumerate output speakers/headphones & microphones.
- Change default audio playback/recording device where supported.
- Get/Set microphone level where supported.
- Verification and undo integration.
"""
from __future__ import annotations

import math
import platform
from typing import Any, Optional

from .contracts import SystemControlResult
from .runner import run_powershell
from core.undo import push_undo

_IS_WINDOWS = platform.system() == "Windows"


def _get_master_endpoint():
    """Returns PyCAW master speaker endpoint volume interface across PyCAW versions."""
    from ctypes import POINTER, cast
    import comtypes
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    try:
        comtypes.CoInitialize()
    except Exception:
        pass

    devices = AudioUtilities.GetSpeakers()
    if hasattr(devices, "EndpointVolume"):
        return devices.EndpointVolume
    elif hasattr(devices, "_dev"):
        interface = devices._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def _get_mic_endpoint():
    """Returns PyCAW default microphone endpoint volume interface if available."""
    from ctypes import POINTER, cast
    import comtypes
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    try:
        comtypes.CoInitialize()
    except Exception:
        pass

    devices = AudioUtilities.GetMicrophone()
    if not devices:
        return None
    if hasattr(devices, "EndpointVolume"):
        return devices.EndpointVolume
    elif hasattr(devices, "_dev"):
        interface = devices._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def get_volume() -> SystemControlResult:
    """Read current master volume (0-100) and mute state."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_volume", error="Requires Windows.")
    try:
        vol = _get_master_endpoint()
        db = vol.GetMasterVolumeLevel()
        is_muted = bool(vol.GetMute())
        if db <= -65.0:
            level = 0
        else:
            level = max(0, min(100, round(10 ** (db / 20.0) * 100)))

        return SystemControlResult(
            success=True,
            action="get_volume",
            actual_value=level,
            verified=True,
            details={"muted": is_muted, "volume_db": round(db, 2)},
            message=f"Current volume is {level}%{' (Muted)' if is_muted else ''}."
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="get_volume", error=str(e),
            message=f"Could not read master volume: {e}"
        )


def set_volume(level: int) -> SystemControlResult:
    """Set master volume to an exact percentage (0-100) and verify."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_volume", error="Requires Windows.")
    try:
        level = max(0, min(100, int(level)))
        vol = _get_master_endpoint()
        
        # Read before state for undo
        prev_res = get_volume()
        prev_level = prev_res.actual_value if prev_res.success else None

        vol_db = -65.25 if level == 0 else max(-65.25, 20.0 * math.log10(level / 100.0))
        vol.SetMasterVolumeLevel(vol_db, None)

        # Post-action verification
        curr = get_volume()
        verified = (curr.success and abs(curr.actual_value - level) <= 2)

        if prev_level is not None:
            push_undo(f"volume {prev_level}% → {level}%", lambda b=prev_level: set_volume(b).message)

        return SystemControlResult(
            success=True,
            action="set_volume",
            requested_value=level,
            actual_value=curr.actual_value if curr.success else level,
            verified=verified,
            message=f"Master volume set to {curr.actual_value}%."
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="set_volume", requested_value=level,
            error=str(e), message=f"Failed to set volume to {level}%: {e}"
        )


def change_volume(delta: int) -> SystemControlResult:
    """Increase or decrease volume by a delta (e.g. +10 or -10)."""
    curr = get_volume()
    if not curr.success:
        return curr
    current_val = curr.actual_value
    target = max(0, min(100, current_val + delta))
    return set_volume(target)


def get_mute_state() -> SystemControlResult:
    """Query current master mute status."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_mute_state", error="Requires Windows.")
    try:
        vol = _get_master_endpoint()
        is_muted = bool(vol.GetMute())
        return SystemControlResult(
            success=True,
            action="get_mute_state",
            actual_value=is_muted,
            verified=True,
            message=f"Audio is currently {'muted' if is_muted else 'unmuted'}."
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="get_mute_state", error=str(e),
            message=f"Could not read mute status: {e}"
        )


def set_mute(mute: bool) -> SystemControlResult:
    """Set master mute state explicitly to True or False and verify."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_mute", error="Requires Windows.")
    try:
        vol = _get_master_endpoint()
        prev_mute = bool(vol.GetMute())
        vol.SetMute(1 if mute else 0, None)
        
        curr = get_mute_state()
        verified = (curr.success and curr.actual_value == mute)

        if prev_mute != mute:
            push_undo(f"{'mute' if mute else 'unmute'}", lambda b=prev_mute: set_mute(b).message)

        action_name = "muted" if mute else "unmuted"
        return SystemControlResult(
            success=True,
            action="set_mute",
            requested_value=mute,
            actual_value=curr.actual_value if curr.success else mute,
            verified=verified,
            message=f"Audio {action_name}."
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="set_mute", requested_value=mute,
            error=str(e), message=f"Failed to set mute={mute}: {e}"
        )


def toggle_mute() -> SystemControlResult:
    """Toggle current master mute state."""
    curr = get_mute_state()
    if not curr.success:
        return curr
    return set_mute(not curr.actual_value)


def list_audio_devices() -> SystemControlResult:
    """Enumerate available playback output devices and recording microphones."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="list_audio_devices", error="Requires Windows.")
    try:
        from core import audio_devices
        inputs = audio_devices.list_devices("input")
        outputs = audio_devices.list_devices("output")
        
        input_list = [d for d in inputs if d != "System default"]
        output_list = [d for d in outputs if d != "System default"]

        msg = (
            f"Available Audio Devices:\n"
            f"Playback (Outputs): {', '.join(output_list) if output_list else 'Default'}\n"
            f"Recording (Microphones): {', '.join(input_list) if input_list else 'Default'}"
        )
        return SystemControlResult(
            success=True,
            action="list_audio_devices",
            actual_value={"outputs": output_list, "inputs": input_list},
            verified=True,
            message=msg,
            details={"outputs": output_list, "inputs": input_list}
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="list_audio_devices", error=str(e),
            message=f"Could not list audio devices: {e}"
        )


def set_default_audio_device(device_name: str, device_type: str = "output") -> SystemControlResult:
    """Set default audio playback or recording device where supported."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_default_audio_device", error="Requires Windows.")
    
    # 1. First save to FRIDAY's internal audio_devices config
    from memory.config_manager import save_output_device, save_input_device
    clean_name = device_name.strip()
    
    if device_type.lower() in ("output", "playback", "speakers"):
        save_output_device(clean_name)
    else:
        save_input_device(clean_name)

    # 2. Attempt Windows system-wide switch via PolicyConfig COM / PowerShell
    ps_cmd = f"""
    $targetName = "{clean_name}"
    # Try using AudioDeviceCmdlets if installed
    if (Get-Module -ListAvailable -Name AudioDeviceCmdlets) {{
        Import-Module AudioDeviceCmdlets
        $dev = Get-AudioDevice -List | Where-Object {{ $_.Name -like "*$targetName*" }} | Select-Object -First 1
        if ($dev) {{
            Set-AudioDevice -Index $dev.Index | Out-Null
            Write-Output "SYSTEM_SWITCHED"
            exit 0
        }}
    }}
    Write-Output "SAVED_FOR_FRIDAY"
    """
    rc, out, _ = run_powershell(ps_cmd, timeout=8.0)
    system_switched = ("SYSTEM_SWITCHED" in str(out))

    msg = f"Default {device_type} set to '{clean_name}' for FRIDAY."
    if system_switched:
        msg += " Windows system-wide default audio device was also updated."
    else:
        msg += " To switch all Windows applications system-wide, open Sound Settings."

    return SystemControlResult(
        success=True,
        action="set_default_audio_device",
        requested_value=clean_name,
        actual_value=clean_name,
        verified=True,
        details={"system_switched": system_switched, "type": device_type},
        message=msg
    )


def get_mic_level() -> SystemControlResult:
    """Query recording microphone input volume level (0-100)."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_mic_level", error="Requires Windows.")
    try:
        mic = _get_mic_endpoint()
        if not mic:
            return SystemControlResult(
                success=False, action="get_mic_level",
                error="No default microphone endpoint found.",
                message="Microphone input level could not be read (no active microphone detected)."
            )
        db = mic.GetMasterVolumeLevel()
        level = 0 if db <= -65.0 else max(0, min(100, round(10 ** (db / 20.0) * 100)))
        return SystemControlResult(
            success=True,
            action="get_mic_level",
            actual_value=level,
            verified=True,
            message=f"Current microphone level is {level}%."
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="get_mic_level", error=str(e),
            message=f"Could not read microphone level: {e}"
        )


def set_mic_level(level: int) -> SystemControlResult:
    """Set recording microphone input volume level (0-100)."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_mic_level", error="Requires Windows.")
    try:
        mic = _get_mic_endpoint()
        if not mic:
            return SystemControlResult(
                success=False, action="set_mic_level",
                error="No default microphone endpoint found.",
                message="Microphone input level could not be set (no active microphone detected)."
            )
        level = max(0, min(100, int(level)))
        vol_db = -65.25 if level == 0 else max(-65.25, 20.0 * math.log10(level / 100.0))
        mic.SetMasterVolumeLevel(vol_db, None)

        curr = get_mic_level()
        verified = (curr.success and abs(curr.actual_value - level) <= 2)
        return SystemControlResult(
            success=True,
            action="set_mic_level",
            requested_value=level,
            actual_value=curr.actual_value if curr.success else level,
            verified=verified,
            message=f"Microphone input level set to {curr.actual_value}%."
        )
    except Exception as e:
        return SystemControlResult(
            success=False, action="set_mic_level", requested_value=level,
            error=str(e), message=f"Failed to set microphone level to {level}%: {e}"
        )
