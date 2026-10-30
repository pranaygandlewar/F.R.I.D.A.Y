import subprocess
import platform
import json
import re
import time
import ctypes
if platform.system() == "Windows":
    from ctypes import wintypes
from core.undo import push_undo

def _run_ps(cmd: str) -> str:
    """Run a PowerShell command and return its output."""
    try:
        if platform.system() != "Windows":
            return "This command requires Windows."
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_battery() -> str:
    out = _run_ps("(Get-WmiObject -Class Win32_Battery).EstimatedChargeRemaining")
    if out:
        return f"Battery is at {out}%."
    return "Battery information not available."

def get_wifi_status() -> str:
    out = _run_ps("Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'} | Select-Object -Property Name, Status, InterfaceDescription | ConvertTo-Json")
    if not out:
        return "No Wi-Fi adapters found."
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        res = []
        for adapter in data:
            res.append(f"{adapter['Name']} ({adapter['InterfaceDescription']}): {adapter['Status']}")
        return "\n".join(res)
    except:
        return out

def get_bluetooth_status() -> str:
    ps_script = """
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null

    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
        $_.Name -eq 'AsTask' -and 
        $_.GetParameters().Count -eq 1 -and 
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    })[0]

    $opRad = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
    $tRad = $asTaskGeneric.MakeGenericMethod([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]]).Invoke($null, @($opRad))
    $tRad.Wait()

    $bt = $tRad.Result | Where-Object { $_.Kind -eq 'Bluetooth' } | Select-Object -First 1
    if ($bt) {
        Write-Output "Bluetooth Radio Status: $($bt.State)"
    } else {
        Write-Output "NO_RADIO"
    }
    """
    out = _run_ps(ps_script)
    if out and "NO_RADIO" not in out and "Error" not in out:
        return out
    # Uses bthserv status as fallback proxy for bluetooth availability
    out_svc = _run_ps("Get-Service bthserv | Select-Object -Property Status | ConvertTo-Json")
    try:
        data = json.loads(out_svc)
        return f"Bluetooth Service Status: {data['Status']}"
    except:
        return "Bluetooth status unavailable."

def set_bluetooth_state(target_state: str) -> str:
    """Sets Bluetooth radio state to 'On' or 'Off' using Windows native WinRT Radio API."""
    ps_script = f"""
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null
    [Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null

    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ 
        $_.Name -eq 'AsTask' -and 
        $_.GetParameters().Count -eq 1 -and 
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    }})[0]

    $opReq = [Windows.Devices.Radios.Radio]::RequestAccessAsync()
    $tReq = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Radios.RadioAccessStatus]).Invoke($null, @($opReq))
    $tReq.Wait()

    $opRad = [Windows.Devices.Radios.Radio]::GetRadiosAsync()
    $tRad = $asTaskGeneric.MakeGenericMethod([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]]).Invoke($null, @($opRad))
    $tRad.Wait()

    $bt = $tRad.Result | Where-Object {{ $_.Kind -eq 'Bluetooth' }} | Select-Object -First 1
    if (-not $bt) {{
        Write-Output "ERROR: No Bluetooth radio adapter found."
        exit 0
    }}

    $target = [Windows.Devices.Radios.RadioState]::{target_state}
    $opSet = $bt.SetStateAsync($target)
    $tSet = $asTaskGeneric.MakeGenericMethod([Windows.Devices.Radios.RadioAccessStatus]).Invoke($null, @($opSet))
    $tSet.Wait()

    Write-Output "Bluetooth state set to {target_state}. Current Radio State: $($bt.State)"
    """
    out = _run_ps(ps_script)
    if out:
        return out
    return f"Failed to set Bluetooth to {target_state}."

def get_audio_devices() -> str:
    # A bit hard to get exact active without pycaw, but we can list generic info or just rely on core.audio_devices
    from core import audio_devices
    audio_devices.prefetch()
    ins = [d['name'] for d in audio_devices._devices.get("input", [])]
    outs = [d['name'] for d in audio_devices._devices.get("output", [])]
    return f"Input Devices:\n" + "\n".join(ins) + "\n\nOutput Devices:\n" + "\n".join(outs)

def service_control(action: str, name: str) -> str:
    if action == "status":
        out = _run_ps(f"Get-Service -Name '{name}' -ErrorAction SilentlyContinue | Select-Object Status | ConvertTo-Json")
        try:
            return f"Service {name} status: {json.loads(out)['Status']}"
        except:
            return f"Service {name} not found or inaccessible."
    elif action in ("start", "stop", "restart"):
        _run_ps(f"{action.capitalize()}-Service -Name '{name}' -Force")
        time.sleep(1)
        return service_control("status", name)
    return "Unknown service action."

def list_windows() -> str:
    if platform.system() != "Windows":
        return "Requires Windows."
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    windows = []
    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value.strip()
                if title and title not in ("Program Manager", "Settings"):
                    windows.append(title)
        return True
    
    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return "Visible Windows:\n" + "\n".join(windows)

def window_manage(action: str, title: str, x: int = 0, y: int = 0, w: int = 800, h: int = 600) -> str:
    if platform.system() != "Windows":
        return "Requires Windows."
    
    FindWindow = ctypes.windll.user32.FindWindowW
    SetWindowPos = ctypes.windll.user32.SetWindowPos
    ShowWindow = ctypes.windll.user32.ShowWindow
    SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    target_hwnd = None
    clean_title = (title or "").strip()
    
    if not clean_title or clean_title.lower() in ("active", "current", "this", "active window", "current window", "focused window"):
        target_hwnd = ctypes.windll.user32.GetForegroundWindow()
    else:
        # Search for a partial match
        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        
        def foreach_window(hwnd, lParam):
            nonlocal target_hwnd
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    t = buff.value
                    if clean_title.lower() in t.lower():
                        target_hwnd = hwnd
                        return False
            return True
        
        EnumWindows(EnumWindowsProc(foreach_window), 0)

    if not target_hwnd:
        return f"Window containing '{clean_title}' not found." if clean_title else "No active window found."

    if action == "focus" or action == "bring_to_front":
        ShowWindow(target_hwnd, 9) # SW_RESTORE
        SetForegroundWindow(target_hwnd)
        return f"Focused window."
    elif action == "minimize":
        ShowWindow(target_hwnd, 6) # SW_MINIMIZE
        return "Minimized window."
    elif action == "maximize":
        # Get current state for undo
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(target_hwnd, ctypes.byref(rect))
        def _undo_max():
            SetWindowPos(target_hwnd, 0, rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top, 0x0004 | 0x0020)
            return "Restored window size."
        push_undo(f"Maximize {title or 'active window'}", _undo_max)
        
        ShowWindow(target_hwnd, 3) # SW_MAXIMIZE
        return "Maximized window."
    elif action == "restore":
        ShowWindow(target_hwnd, 9) # SW_RESTORE
        return "Restored window."
    elif action == "move":
        # Get current size
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(target_hwnd, ctypes.byref(rect))
        cw = rect.right - rect.left
        ch = rect.bottom - rect.top
        
        def _undo_move():
            SetWindowPos(target_hwnd, 0, rect.left, rect.top, cw, ch, 0x0004 | 0x0020)
            return "Undid window move."
        push_undo(f"Move {title or 'active window'}", _undo_move)
        
        SetWindowPos(target_hwnd, 0, x, y, cw, ch, 0x0004 | 0x0020) # SWP_NOZORDER | SWP_FRAMECHANGED
        return f"Moved window to {x}, {y}."
    elif action == "resize":
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(target_hwnd, ctypes.byref(rect))
        cw = rect.right - rect.left
        ch = rect.bottom - rect.top
        
        def _undo_resize():
            SetWindowPos(target_hwnd, 0, rect.left, rect.top, cw, ch, 0x0004 | 0x0020)
            return "Undid window resize."
        push_undo(f"Resize {title or 'active window'}", _undo_resize)
        
        SetWindowPos(target_hwnd, 0, rect.left, rect.top, w, h, 0x0004 | 0x0020)
        return f"Resized window to {w}x{h}."
    elif action == "center":
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(target_hwnd, ctypes.byref(rect))
        cw = rect.right - rect.left
        ch = rect.bottom - rect.top
        
        def _undo_center():
            SetWindowPos(target_hwnd, 0, rect.left, rect.top, cw, ch, 0x0004 | 0x0020)
            return "Undid window center."
        push_undo(f"Center {title or 'active window'}", _undo_center)
        
        nx = (sw - cw) // 2
        ny = (sh - ch) // 2
        SetWindowPos(target_hwnd, 0, nx, ny, cw, ch, 0x0004 | 0x0020)
        return f"Centered window."
    
    return f"Unknown window action: {action}"

def system_info() -> str:
    out = _run_ps(r'''
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor
    $ram = [math]::Round($os.TotalVisibleMemorySize / 1024 / 1024, 2)
    $free_ram = [math]::Round($os.FreePhysicalMemory / 1024 / 1024, 2)
    $disk = Get-CimInstance Win32_LogicalDisk | Where-Object DeviceID -eq "C:"
    $free_disk = [math]::Round($disk.FreeSpace / 1GB, 2)
    $tot_disk = [math]::Round($disk.Size / 1GB, 2)
    
    [PSCustomObject]@{
        OS = $os.Caption
        Uptime = (Get-Date) - $os.LastBootUpTime
        CPU = $cpu.Name
        RAM_GB = "$free_ram free of $ram"
        C_Drive_GB = "$free_disk free of $tot_disk"
    } | ConvertTo-Json
    ''')
    try:
        d = json.loads(out)
        return f"OS: {d['OS']}\nCPU: {d['CPU']}\nRAM: {d['RAM_GB']}\nC: Drive: {d['C_Drive_GB']}\nUptime: {d['Uptime']}"
    except:
        return "Could not retrieve system info."

def laptop_control(parameters: dict, **kwargs) -> str:
    from core import windows_control as wc
    action = str(parameters.get("action", "")).lower().strip()
    value = parameters.get("value")
    
    # Audio
    if action == "get_volume":
        return str(wc.get_volume())
    elif action == "set_volume":
        return str(wc.set_volume(int(value if value is not None else 50)))
    elif action in ("volume_up", "volume_down"):
        delta = 10 if action == "volume_up" else -10
        return str(wc.change_volume(delta))
    elif action in ("mute", "unmute", "toggle_mute"):
        if action == "mute": return str(wc.set_mute(True))
        if action == "unmute": return str(wc.set_mute(False))
        return str(wc.toggle_mute())
    elif action == "get_mute_state":
        return str(wc.get_mute_state())
    elif action == "list_audio_devices":
        return str(wc.list_audio_devices())
    elif action == "set_default_audio":
        dev = str(value or parameters.get("name", "")).strip()
        dev_type = str(parameters.get("type", "output")).strip()
        return str(wc.set_default_audio_device(dev, dev_type))
    elif action == "get_mic_level":
        return str(wc.get_mic_level())
    elif action == "set_mic_level":
        return str(wc.set_mic_level(int(value if value is not None else 50)))

    # Display & Brightness
    elif action == "get_brightness":
        return str(wc.get_brightness())
    elif action == "set_brightness":
        return str(wc.set_brightness(int(value if value is not None else 50)))
    elif action in ("brightness_up", "brightness_down"):
        delta = 10 if action == "brightness_up" else -10
        return str(wc.change_brightness(delta))
    elif action == "enumerate_displays":
        return str(wc.enumerate_displays())
    elif action == "projection_mode":
        mode = str(value or parameters.get("mode", "extend")).strip()
        return str(wc.switch_projection_mode(mode))
    elif action == "night_light_status":
        return str(wc.get_night_light_status())
    elif action == "toggle_night_light":
        return str(wc.toggle_night_light())
    elif action == "gpu_info":
        return str(wc.get_gpu_info())

    # Wi-Fi, Bluetooth & Hotspot
    elif action in ("battery_status", "power_status"):
        return str(wc.get_power_status())
    elif action == "battery_report":
        return str(wc.generate_battery_report())
    elif action == "wifi_status":
        return str(wc.get_wifi_status())
    elif action == "wifi_on":
        return str(wc.set_wifi_state(True))
    elif action == "wifi_off":
        return str(wc.set_wifi_state(False))
    elif action == "list_wifi_networks":
        return str(wc.list_wifi_networks())
    elif action == "connect_wifi":
        ssid = str(value or parameters.get("name", "")).strip()
        return str(wc.connect_wifi(ssid))
    elif action == "disconnect_wifi":
        return str(wc.disconnect_wifi())
    elif action == "bluetooth_status":
        return str(wc.get_bluetooth_status())
    elif action == "bluetooth_on":
        return str(wc.set_bluetooth_state(True))
    elif action == "bluetooth_off":
        return str(wc.set_bluetooth_state(False))
    elif action == "list_bluetooth_devices":
        return str(wc.list_bluetooth_devices())
    elif action == "hotspot_status":
        return str(wc.get_hotspot_status())
    elif action == "toggle_hotspot":
        return str(wc.toggle_hotspot())
    elif action == "airplane_mode_status":
        return str(wc.get_airplane_mode_status())

    # Network Diagnostics & VPN
    elif action == "network_diagnostics":
        return str(wc.run_network_diagnostics())
    elif action == "flush_dns":
        return str(wc.flush_dns())
    elif action in ("list_vpn", "vpn_status"):
        return str(wc.list_vpn_connections())

    # Power Schemes & Timeouts
    elif action == "power_plans":
        return str(wc.get_power_plans())
    elif action == "set_power_plan":
        plan = str(value or parameters.get("name", "")).strip()
        return str(wc.set_power_plan(plan))
    elif action == "display_timeout":
        mins = int(value if value is not None else 10)
        return str(wc.set_display_timeout(mins))
    elif action == "sleep_timeout":
        mins = int(value if value is not None else 30)
        return str(wc.set_sleep_timeout(mins))
    elif action == "sleep":
        return str(wc.request_sleep())
    elif action == "hibernate":
        return str(wc.request_hibernate())
    elif action == "cancel_shutdown":
        return str(wc.cancel_shutdown())
    elif action == "recovery_options":
        return str(wc.open_recovery_options())

    # Theme & Personalization
    elif action == "theme_status":
        return str(wc.get_theme_status())
    elif action == "set_theme":
        m = str(value or parameters.get("mode", "dark")).strip()
        return str(wc.set_theme(m))
    elif action == "toggle_theme":
        return str(wc.toggle_theme())
    elif action == "set_wallpaper":
        wp = str(value or parameters.get("path", "")).strip()
        return str(wc.set_wallpaper(wp))
    elif action == "transparency_status":
        return str(wc.get_transparency_status())

    # Security & Updates
    elif action == "security_status":
        return str(wc.get_security_status())
    elif action == "elevation_status":
        return str(wc.get_elevation_status())
    elif action == "windows_version":
        return str(wc.get_windows_version())
    elif action == "check_updates":
        return str(wc.check_windows_updates())

    # Startup & Storage
    elif action == "startup_apps":
        return str(wc.list_startup_apps())
    elif action == "disk_usage":
        return str(wc.get_disk_usage())
    elif action == "preview_cleanup":
        return str(wc.preview_temp_cleanup())
    elif action == "empty_recycle_bin":
        return str(wc.empty_recycle_bin())

    # Services & Processes
    elif action in ("service_status", "service_start", "service_stop", "service_restart"):
        svc_name = parameters.get("name", "")
        if not svc_name: return "Missing service name."
        act = action.split("_")[1]
        return str(wc.service_control(svc_name, act))
    elif action == "list_processes":
        return str(wc.list_running_processes())
    elif action in ("close_application", "close_app"):
        app = str(value or parameters.get("name", "")).strip()
        return str(wc.close_application_gracefully(app))

    # Focus & Settings
    elif action == "focus_status":
        return str(wc.get_focus_status())
    elif action == "open_settings":
        page = str(value or parameters.get("page", "display")).strip()
        return str(wc.open_settings_page(page))

    # Native Windows Management
    elif action == "list_windows":
        return list_windows()
    elif action in ("focus_window", "minimize_window", "maximize_window", "restore_window", "move_window", "resize_window", "center_window", "bring_to_front"):
        title = parameters.get("title", "")
        x = parameters.get("x", 0)
        y = parameters.get("y", 0)
        w = parameters.get("w", 800)
        h = parameters.get("h", 600)
        act = action.replace("_window", "")
        if action == "bring_to_front": act = "bring_to_front"
        return window_manage(act, title, x, y, w, h)
    elif action == "system_info":
        return system_info()
    elif action == "log_out":
        _run_ps("logoff")
        return "Logging out..."
    
    return f"Unsupported laptop control action: '{action}'. Call with a supported Windows control action."

TOOL = {
    "name": "laptop_control",
    "description": (
        "Advanced Windows 11 system and laptop control layer. "
        "Audio: get_volume, set_volume, volume_up, volume_down, mute, unmute, toggle_mute, get_mute_state, list_audio_devices, set_default_audio, get_mic_level, set_mic_level. "
        "Display: get_brightness, set_brightness, brightness_up, brightness_down, enumerate_displays, projection_mode, night_light_status, toggle_night_light, gpu_info. "
        "Network: wifi_status, wifi_on, wifi_off, list_wifi_networks, connect_wifi, disconnect_wifi, bluetooth_status, bluetooth_on, bluetooth_off, list_bluetooth_devices, hotspot_status, toggle_hotspot, airplane_mode_status, network_diagnostics, flush_dns, list_vpn. "
        "Power & Battery: power_status, battery_report, power_plans, set_power_plan, display_timeout, sleep_timeout, sleep, hibernate, cancel_shutdown, recovery_options. "
        "Personalization: theme_status, set_theme, toggle_theme, set_wallpaper, transparency_status. "
        "System & Maintenance: security_status, elevation_status, windows_version, check_updates, startup_apps, disk_usage, preview_cleanup, empty_recycle_bin, list_processes, close_application, service_status, service_start, service_stop, service_restart, focus_status, open_settings, list_windows, focus_window, minimize_window, maximize_window, restore_window, move_window, resize_window, center_window, system_info."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "The exact system action to perform (e.g. set_volume, set_brightness, wifi_status, list_wifi_networks, connect_wifi, network_diagnostics, power_status, power_plans, set_theme, security_status, disk_usage, preview_cleanup, empty_recycle_bin, etc.)"
            },
            "value": {
                "type": "STRING",
                "description": "Optional numeric percentage (for volume, brightness, timeouts), mode string (dark/light, duplicate/extend), or general target value."
            },
            "name": {
                "type": "STRING",
                "description": "Target name (SSID for connect_wifi, service name, app name, device name, or power plan name)."
            },
            "page": {
                "type": "STRING",
                "description": "Settings page key for open_settings (e.g. display, sound, wifi, bluetooth, powersleep, notifications, recovery, etc.)"
            },
            "title": {
                "type": "STRING",
                "description": "Window title if action is *_window"
            },
            "x": {"type": "INTEGER", "description": "X coordinate for move_window"},
            "y": {"type": "INTEGER", "description": "Y coordinate for move_window"},
            "w": {"type": "INTEGER", "description": "Width for resize_window"},
            "h": {"type": "INTEGER", "description": "Height for resize_window"}
        },
        "required": ["action"]
    },
    "handler": laptop_control
}
