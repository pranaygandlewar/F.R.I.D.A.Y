"""
core/windows_control/network.py — Windows 11 Wi-Fi, Bluetooth, Hotspot, Adapters & Diagnostics.

Covers:
- Capability C: Wi-Fi & Bluetooth
- Capability D: Windows Mobile Hotspot
- Capability G: Airplane Mode & Radio State
- Capability H: Network Diagnostics & VPN
- Capability I: Network Adapter Management
"""
from __future__ import annotations

import json
import os
import platform
import re
import socket
import time
from typing import Any, Optional

from .contracts import SystemControlResult
from .runner import run_cmd, run_powershell, sanitize_output
from .settings_uris import open_settings_page
from core.undo import push_undo

_IS_WINDOWS = platform.system() == "Windows"


# ── Active Connection Safety Guard ─────────────────────────────────────────────

def is_active_session_adapter(adapter_name: str) -> bool:
    """Checks whether the specified network adapter is carrying the active internet route.
    If so, disabling it will disconnect FRIDAY's Gemini Live WebSocket session.
    """
    if not _IS_WINDOWS:
        return False
    ps_cmd = f"""
    $route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($route) {{
        $alias = (Get-NetAdapter -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue).Name
        if ($alias -like "*{adapter_name}*") {{
            Write-Output "ACTIVE_ROUTE"
            exit 0
        }}
    }}
    Write-Output "SAFE"
    """
    rc, out, _ = run_powershell(ps_cmd, timeout=5.0)
    return "ACTIVE_ROUTE" in str(out)


# ── Wi-Fi Management ───────────────────────────────────────────────────────────

def get_wifi_status() -> SystemControlResult:
    """Inspect Wi-Fi adapter state, SSID, signal strength, and IP profile."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_wifi_status", error="Requires Windows.")

    rc, out, _ = run_cmd(["netsh", "wlan", "show", "interfaces"], timeout=6.0)
    if rc != 0 or "no wireless interface" in out.lower():
        return SystemControlResult(
            success=False,
            action="get_wifi_status",
            error="No wireless adapter found.",
            message="No Wi-Fi adapter detected on this system."
        )

    # Parse details
    state = "disconnected"
    ssid = None
    signal = None
    for line in out.splitlines():
        if ":" in line:
            k, v = [x.strip() for x in line.split(":", 1)]
            if k.lower() == "state":
                state = v
            elif k.lower() == "ssid":
                ssid = v
            elif k.lower() == "signal":
                signal = v

    connected = (state.lower() == "connected")
    msg = f"Wi-Fi is {state}."
    if connected and ssid:
        msg = f"Wi-Fi is connected to '{ssid}' (Signal: {signal or 'Good'})."

    return SystemControlResult(
        success=True,
        action="get_wifi_status",
        actual_value={"state": state, "ssid": ssid, "signal": signal},
        verified=True,
        details={"state": state, "ssid": ssid, "signal": signal, "connected": connected},
        message=msg
    )


def list_wifi_networks() -> SystemControlResult:
    """Scan and list available Wi-Fi networks in range."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="list_wifi_networks", error="Requires Windows.")

    rc, out, err = run_cmd(["netsh", "wlan", "show", "networks"], timeout=10.0)
    if rc != 0:
        return SystemControlResult(
            success=False, action="list_wifi_networks",
            error=err or "Wi-Fi scan failed.", message="Could not scan for Wi-Fi networks."
        )

    networks = []
    for line in out.splitlines():
        if line.strip().startswith("SSID "):
            parts = line.split(":", 1)
            if len(parts) > 1:
                name = parts[1].strip()
                if name and name not in networks:
                    networks.append(name)

    msg = f"Found {len(networks)} Wi-Fi networks:\n" + ", ".join(networks[:10]) if networks else "No Wi-Fi networks in range."
    return SystemControlResult(
        success=True,
        action="list_wifi_networks",
        actual_value=networks,
        verified=True,
        details={"networks": networks},
        message=msg
    )


def connect_wifi(ssid: str) -> SystemControlResult:
    """Connect to an authorized, saved Wi-Fi profile by SSID."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="connect_wifi", error="Requires Windows.")

    clean_ssid = ssid.strip()
    rc, out, err = run_cmd(["netsh", "wlan", "connect", f"name={clean_ssid}"], timeout=12.0)
    if rc == 0 and "connection request was completed successfully" in out.lower():
        time.sleep(2)
        curr = get_wifi_status()
        is_conn = (curr.success and curr.details.get("connected") and curr.details.get("ssid") == clean_ssid)
        return SystemControlResult(
            success=True,
            action="connect_wifi",
            requested_value=clean_ssid,
            actual_value=clean_ssid,
            verified=is_conn,
            message=f"Connected to Wi-Fi network '{clean_ssid}'."
        )

    return SystemControlResult(
        success=False,
        action="connect_wifi",
        requested_value=clean_ssid,
        error=out or err,
        message=f"Could not connect to '{clean_ssid}'. Ensure the network profile is saved with valid credentials."
    )


def disconnect_wifi() -> SystemControlResult:
    """Disconnect from the current Wi-Fi network with active connection safeguard."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="disconnect_wifi", error="Requires Windows.")

    curr = get_wifi_status()
    if not curr.success or not curr.details.get("connected"):
        return SystemControlResult(
            success=True, action="disconnect_wifi",
            verified=True, message="Wi-Fi is already disconnected."
        )

    ssid = curr.details.get("ssid")
    # Check if this Wi-Fi holds FRIDAY's primary remote route
    if is_active_session_adapter("Wi-Fi"):
        return SystemControlResult(
            success=False,
            action="disconnect_wifi",
            requires_confirmation=True,
            error="Active session safeguard: Wi-Fi carries FRIDAY's active connection.",
            message=f"Disconnecting Wi-Fi '{ssid}' will disconnect my voice session. Please confirm if you really want to disconnect."
        )

    rc, out, err = run_cmd(["netsh", "wlan", "disconnect"], timeout=6.0)
    return SystemControlResult(
        success=True,
        action="disconnect_wifi",
        verified=True,
        message=f"Disconnected from Wi-Fi '{ssid}'."
    )


def set_wifi_state(enabled: bool) -> SystemControlResult:
    """Enable or disable Wi-Fi adapter with active session safeguard."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_wifi_state", error="Requires Windows.")

    target_state = "Enabled" if enabled else "Disabled"
    if not enabled and is_active_session_adapter("Wi-Fi"):
        return SystemControlResult(
            success=False,
            action="set_wifi_state",
            requires_confirmation=True,
            error="Active connection safeguard triggered.",
            message="Turning off Wi-Fi will disconnect FRIDAY's live connection. Please confirm on screen if you wish to proceed."
        )

    ps_cmd = f"""
    $adapter = Get-NetAdapter | Where-Object {{ $_.PhysicalMediaType -eq 'Native 802.11' }} | Select-Object -First 1
    if (-not $adapter) {{ Write-Output "NO_ADAPTER"; exit 0 }}
    if ("{target_state}" -eq "Enabled") {{
        Enable-NetAdapter -Name $adapter.Name -Confirm:$false
    }} else {{
        Disable-NetAdapter -Name $adapter.Name -Confirm:$false
    }}
    Write-Output "OK"
    """
    rc, out, err = run_powershell(ps_cmd, timeout=10.0)
    if "OK" in str(out):
        push_undo(f"Wi-Fi {'On' if enabled else 'Off'}", lambda b=not enabled: set_wifi_state(b).message)
        return SystemControlResult(
            success=True,
            action="set_wifi_state",
            requested_value=enabled,
            actual_value=enabled,
            verified=True,
            message=f"Wi-Fi turned {'On' if enabled else 'Off'}."
        )

    return SystemControlResult(
        success=False, action="set_wifi_state",
        error=err or "Adapter modification failed.",
        message=f"Failed to turn Wi-Fi {'On' if enabled else 'Off'}."
    )


# ── Bluetooth ──────────────────────────────────────────────────────────────────

def get_bluetooth_status() -> SystemControlResult:
    """Inspect Bluetooth radio state and list paired devices."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_bluetooth_status", error="Requires Windows.")

    ps_script = """
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    })[0]
    $opRad = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
    $tRad = $asTaskGeneric.MakeGenericMethod([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]]).Invoke($null, @($opRad))
    $tRad.Wait()
    $bt = $tRad.Result | Where-Object { $_.Kind -eq 'Bluetooth' } | Select-Object -First 1
    if ($bt) {
        Write-Output "RADIO:$($bt.State)"
    } else {
        $svc = (Get-Service bthserv -ErrorAction SilentlyContinue).Status
        Write-Output "SVC:$svc"
    }
    """
    rc, out, _ = run_powershell(ps_script, timeout=8.0)
    out_str = str(out).strip()
    state = "Unknown"
    if "RADIO:On" in out_str:
        state = "On"
    elif "RADIO:Off" in out_str:
        state = "Off"
    elif "SVC:Running" in out_str:
        state = "Running (Service)"

    return SystemControlResult(
        success=True,
        action="get_bluetooth_status",
        actual_value=state,
        verified=True,
        message=f"Bluetooth is currently {state}."
    )


def set_bluetooth_state(enabled: bool) -> SystemControlResult:
    """Turn Bluetooth On or Off using native WinRT Radio API."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="set_bluetooth_state", error="Requires Windows.")

    target = "On" if enabled else "Off"
    ps_script = f"""
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ 
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    }})[0]
    $opReq = [Windows.Devices.Radios.Radio]::RequestAccessAsync()
    $tReq = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Radios.RadioAccessStatus]).Invoke($null, @($opReq))
    $tReq.Wait()
    $opRad = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
    $tRad = $asTaskGeneric.MakeGenericMethod([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]]).Invoke($null, @($opRad))
    $tRad.Wait()
    $bt = $tRad.Result | Where-Object {{ $_.Kind -eq 'Bluetooth' }} | Select-Object -First 1
    if (-not $bt) {{ Write-Output "NO_RADIO"; exit 0 }}
    $opSet = $bt.SetStateAsync([Windows.Devices.Radios.RadioState]::{target})
    $tSet = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Radios.RadioAccessStatus]).Invoke($null, @($opSet))
    $tSet.Wait()
    Write-Output "OK"
    """
    rc, out, _ = run_powershell(ps_script, timeout=10.0)
    if "OK" in str(out):
        push_undo(f"Bluetooth {'On' if enabled else 'Off'}", lambda b=not enabled: set_bluetooth_state(b).message)
        return SystemControlResult(
            success=True,
            action="set_bluetooth_state",
            requested_value=target,
            actual_value=target,
            verified=True,
            message=f"Bluetooth turned {target}."
        )

    open_settings_page("bluetooth")
    return SystemControlResult(
        success=False,
        action="set_bluetooth_state",
        verified=False,
        error="Bluetooth Radio API not accessible.",
        message=f"Could not change Bluetooth state directly. Opened Bluetooth settings for you."
    )


def list_bluetooth_devices() -> SystemControlResult:
    """Enumerate paired Bluetooth devices and their connection status."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="list_bluetooth_devices", error="Requires Windows.")

    ps_cmd = """
    Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue | 
    Where-Object { $_.FriendlyName -notlike "*Adapter*" -and $_.FriendlyName -notlike "*Enumerator*" } |
    Select-Object -Property FriendlyName, Status | ConvertTo-Json
    """
    rc, out, _ = run_powershell(ps_cmd, timeout=8.0, json_output=True)
    dev_names = []
    if rc == 0 and out:
        if isinstance(out, dict):
            out = [out]
        for d in out:
            fn = d.get("FriendlyName")
            if fn:
                dev_names.append(fn)

    msg = f"Paired Bluetooth Devices ({len(dev_names)}):\n" + ", ".join(dev_names) if dev_names else "No paired Bluetooth devices detected."
    return SystemControlResult(
        success=True,
        action="list_bluetooth_devices",
        actual_value=dev_names,
        verified=True,
        details={"devices": dev_names},
        message=msg
    )


# ── Windows Mobile Hotspot ─────────────────────────────────────────────────────

def get_hotspot_status() -> SystemControlResult:
    """Query Mobile Hotspot capability, state, and client count."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_hotspot_status", error="Requires Windows.")

    # Hotspot query using NetAdapter tethering interface
    ps_cmd = """
    $hs = Get-NetAdapter | Where-Object { $_.InterfaceDescription -like "*Direct Virtual*" -or $_.Name -like "*Hotspot*" }
    if ($hs) {
        Write-Output "STATUS:$($hs.Status)"
    } else {
        Write-Output "INACTIVE"
    }
    """
    rc, out, _ = run_powershell(ps_cmd, timeout=6.0)
    is_active = ("Up" in str(out))
    return SystemControlResult(
        success=True,
        action="get_hotspot_status",
        actual_value="Active" if is_active else "Inactive",
        verified=True,
        message=f"Windows Mobile Hotspot is currently {'Active' if is_active else 'Inactive'}."
    )


def toggle_hotspot() -> SystemControlResult:
    """Open Mobile Hotspot settings since WinRT Tethering requires COM activation tokens."""
    open_settings_page("mobilehotspot")
    return SystemControlResult(
        success=True,
        action="toggle_hotspot",
        verified=True,
        message="Opened Mobile Hotspot settings."
    )


# ── Airplane Mode & Radio State ────────────────────────────────────────────────

def get_airplane_mode_status() -> SystemControlResult:
    """Inspect Airplane Mode state."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="get_airplane_mode_status", error="Requires Windows.")

    # In Windows 11, Airplane mode state lives under RadioManagement SystemRadioState
    ps_cmd = """
    $val = (Get-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\RadioManagement" -Name "SystemRadioState" -ErrorAction SilentlyContinue).SystemRadioState
    if ($val -ne $null) { Write-Output $val } else { Write-Output "UNAVAILABLE" }
    """
    rc, out, _ = run_powershell(ps_cmd, timeout=5.0)
    out_str = str(out).strip()
    is_on = (out_str == "0")  # 0 indicates Radios Off (Airplane Mode Active)
    
    wifi = get_wifi_status()
    bt = get_bluetooth_status()
    summary = f"Airplane Mode: {'On' if is_on else 'Off'} (Wi-Fi: {wifi.details.get('state', 'Unknown')}, Bluetooth: {bt.actual_value})"

    return SystemControlResult(
        success=True,
        action="get_airplane_mode_status",
        actual_value="On" if is_on else "Off",
        verified=True,
        details={"airplane_mode": is_on, "wifi": wifi.actual_value, "bluetooth": bt.actual_value},
        message=summary
    )


# ── Network Diagnostics & VPN ──────────────────────────────────────────────────

def run_network_diagnostics() -> SystemControlResult:
    """Comprehensive test: Local Gateway, DNS Resolution, Internet Reachability."""
    results = {
        "dns": False,
        "internet": False,
        "gateway": False,
        "local_ip": "Unknown"
    }
    
    # 1. Local IP & Gateway
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.0)
        s.connect(("8.8.8.8", 53))
        results["local_ip"] = s.getsockname()[0]
        results["gateway"] = True
        s.close()
    except Exception:
        results["gateway"] = False

    # 2. DNS Resolution
    try:
        ip = socket.gethostbyname("google.com")
        results["dns"] = bool(ip)
    except Exception:
        results["dns"] = False

    # 3. Internet Reachability
    try:
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.settimeout(3.0)
        s2.connect(("1.1.1.1", 53))
        results["internet"] = True
        s2.close()
    except Exception:
        results["internet"] = False

    all_ok = all([results["dns"], results["internet"], results["gateway"]])
    msg = (
        f"Network Diagnostics ({'Healthy' if all_ok else 'Issues Detected'}):\n"
        f"Local IP: {results['local_ip']}\n"
        f"Gateway Reachability: {'✔ Connected' if results['gateway'] else '❌ Failed'}\n"
        f"DNS Resolution: {'✔ Working' if results['dns'] else '❌ Failed'}\n"
        f"Internet Connectivity: {'✔ Online' if results['internet'] else '❌ Offline'}"
    )

    return SystemControlResult(
        success=all_ok,
        action="run_network_diagnostics",
        actual_value=results,
        verified=True,
        details=results,
        message=msg
    )


def flush_dns() -> SystemControlResult:
    """Flush and clear Windows DNS resolver cache."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="flush_dns", error="Requires Windows.")

    rc, out, err = run_cmd(["ipconfig", "/flushdns"], timeout=6.0)
    success = (rc == 0 and "successfully flushed" in out.lower())
    return SystemControlResult(
        success=success,
        action="flush_dns",
        verified=success,
        message="DNS resolver cache successfully flushed." if success else "Failed to flush DNS cache."
    )


def list_vpn_connections() -> SystemControlResult:
    """Inspect configured VPN profiles and connection status."""
    if not _IS_WINDOWS:
        return SystemControlResult(success=False, action="list_vpn_connections", error="Requires Windows.")

    ps_cmd = "Get-VpnConnection -ErrorAction SilentlyContinue | Select-Object -Property Name, ConnectionStatus | ConvertTo-Json"
    rc, out, _ = run_powershell(ps_cmd, timeout=8.0, json_output=True)
    vpns = []
    if rc == 0 and out:
        if isinstance(out, dict):
            out = [out]
        for v in out:
            vpns.append(f"{v.get('Name')}: {v.get('ConnectionStatus')}")

    msg = f"Configured VPNs ({len(vpns)}):\n" + "\n".join(vpns) if vpns else "No configured VPN profiles found."
    return SystemControlResult(
        success=True,
        action="list_vpn_connections",
        actual_value=vpns,
        verified=True,
        details={"vpns": vpns},
        message=msg
    )
