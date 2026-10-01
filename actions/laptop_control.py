import subprocess
import platform
import json
import re
import time
import ctypes
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
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
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
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        
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
        rect = ctypes.wintypes.RECT()
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
        rect = ctypes.wintypes.RECT()
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
        rect = ctypes.wintypes.RECT()
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
        rect = ctypes.wintypes.RECT()
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
    action = parameters.get("action", "").lower()
    
    if action == "battery_status":
        return get_battery()
    elif action == "wifi_status":
        return get_wifi_status()
    elif action == "wifi_on":
        _run_ps("Enable-NetAdapter -Name (Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'}).Name -Confirm:$false")
        return "Verified: " + get_wifi_status()
    elif action == "wifi_off":
        _run_ps("Disable-NetAdapter -Name (Get-NetAdapter | Where-Object {$_.PhysicalMediaType -eq 'Native 802.11'}).Name -Confirm:$false")
        return "Verified: " + get_wifi_status()
    elif action == "bluetooth_status":
        return get_bluetooth_status()
    elif action == "bluetooth_on":
        return set_bluetooth_state("On")
    elif action == "bluetooth_off":
        return set_bluetooth_state("Off")
    elif action == "list_audio_devices":
        return get_audio_devices()
    elif action in ("service_status", "service_start", "service_stop", "service_restart"):
        svc_name = parameters.get("name", "")
        if not svc_name: return "Missing service name."
        act = action.split("_")[1]
        return service_control(act, svc_name)
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
    elif action == "hibernate":
        _run_ps("shutdown -h")
        return "Hibernating..."
    elif action == "log_out":
        _run_ps("logoff")
        return "Logging out..."
    elif action == "cancel_shutdown":
        _run_ps("shutdown -a")
        return "Shutdown cancelled."
    
    return f"Unsupported laptop control action: {action}"

TOOL = {
    "name": "laptop_control",
    "description": "Windows native laptop and system control. Manages Wi-Fi, Bluetooth, battery, services, native window management, system info.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "One of: battery_status, wifi_status, wifi_on, wifi_off, bluetooth_status, bluetooth_on, bluetooth_off, list_audio_devices, service_status, service_start, service_stop, service_restart, list_windows, focus_window, minimize_window, maximize_window, restore_window, move_window, resize_window, center_window, bring_to_front, system_info, hibernate, log_out, cancel_shutdown"
            },
            "name": {
                "type": "STRING",
                "description": "Service name if action is service_*"
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
