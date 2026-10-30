import json
import logging

def evaluate(tool_name: str, parameters: dict) -> tuple[int, str]:
    """
    EDITH Security Policy.
    Returns (risk_level, reason).
    LEVEL 0 — INFORMATION
    LEVEL 1 — REVERSIBLE
    LEVEL 2 — SENSITIVE
    LEVEL 3 — HIGH RISK / IRREVERSIBLE (Requires confirmation: ONLY shutdown, restart, delete)
    LEVEL 4 — BLOCKED
    """
    
    # 1. Computer Settings
    if tool_name == "computer_settings":
        action = str(parameters.get("action", "")).lower().strip()
        if not action and parameters.get("description"):
            # A rough estimate if action is missing but description is present
            desc = parameters.get("description", "").lower()
            if "restart" in desc or "shutdown" in desc:
                return 3, "Potentially irreversible system change"
                
        if action in ("restart", "shutdown"):
            return 3, f"Irreversible action: {action}"
        elif action in ("volume_up", "volume_down", "volume_set", "mute", "unmute", "toggle_mute", "brightness_up", "brightness_down", "dark_mode", "toggle_wifi"):
            return 1, "Reversible setting change"
        else:
            return 1, "Application or window setting"
            
    # 2. Computer Control
    elif tool_name == "computer_control":
        action = str(parameters.get("action", "")).lower().strip()
        if action in ("screenshot", "copy"):
            return 0, "Information access"
        elif action in ("type", "smart_type", "paste", "clear_field", "random_data"):
            return 1, "Reversible input"
        elif action in ("click", "double_click", "right_click", "move", "drag", "hotkey", "press", "scroll", "focus_window", "screen_find", "screen_click"):
            return 1, "Reversible input or navigation"
        elif action == "user_data":
            return 2, "Accessing user profile data"
        else:
            return 1, "Standard computer control"
            
    # 3. Web Search
    elif tool_name == "web_search":
        return 0, "Information retrieval"

    # 4. Browser Control
    elif tool_name == "browser_control":
        action = str(parameters.get("action", "")).lower().strip()
        if action in ("go_back", "go_forward", "refresh", "scroll_down", "scroll_up"):
            return 1, "Reversible browser action"
        elif action == "close_tab":
            return 1, "Reversible browser action"
        elif action in ("click", "type", "submit"):
            return 2, "Active browser interaction"
        else:
            return 0, "Information access"

    # 5. File Controller
    elif tool_name == "file_controller":
        action = str(parameters.get("action", "")).lower().strip()
        if action in ("read", "list", "search", "largest", "disk_usage", "info"):
            return 0, "Read-only file access"
        elif action in ("create", "create_file", "create_folder", "write", "append", "rename", "move", "copy", "organize_desktop"):
            return 1, "Reversible file modification"
        elif action in ("delete", "delete_file", "delete_folder", "remove"):
            return 3, "Irreversible file deletion"
        else:
            return 1, "File operation"
            
    # 6. File Processor
    elif tool_name == "file_processor":
        action = str(parameters.get("action", "")).lower().strip()
        if action in ("read", "summarize", "search"):
            return 0, "Read-only file access"
        elif action in ("delete", "remove"):
            return 3, "Irreversible file deletion"
        else:
            return 1, "File processing"

    # 7. System Monitor / Background Monitor / Camera
    elif tool_name in ("system_status", "manage_monitor", "open_camera", "close_camera", "screen_process"):
        return 0, "System / camera interface access"
        
    # 8. Open App
    elif tool_name == "open_app":
        return 1, "Opening application"

    # 9. Send Message
    elif tool_name == "send_message":
        return 2, "Sending communication"

    # 10. Planner (New tool)
    elif tool_name == "planner":
        # The planner itself just plans/manages tasks, but individual steps are checked.
        action = str(parameters.get("action", "")).lower().strip()
        if action == "cancel":
            return 1, "Task cancellation"
        return 0, "Planner operation"
        
    # 11. Laptop Control (New Tool)
    elif tool_name == "laptop_control":
        action = str(parameters.get("action", "")).lower().strip()
        if action in (
            "battery_status", "power_status", "wifi_status", "bluetooth_status", "cpu_info",
            "gpu_info", "ram_usage", "disk_usage", "temperature", "network_status", "network_diagnostics",
            "running_processes", "list_processes", "uptime", "os_version", "windows_version",
            "hardware_info", "list_windows", "list_audio_devices", "list_wifi_networks",
            "list_bluetooth_devices", "list_vpn", "hotspot_status", "airplane_mode_status",
            "theme_status", "get_volume", "get_mute_state", "get_brightness", "get_mic_level",
            "security_status", "elevation_status", "startup_apps", "focus_status", "preview_cleanup"
        ):
            return 0, "System information access"
        elif action in ("focus_window", "minimize_window", "maximize_window", "restore_window", "move_window", "resize_window", "center_window", "bring_to_front"):
            return 1, "Window management"
        elif action in ("bluetooth_on", "bluetooth_off", "wifi_on", "wifi_off"):
            return 1, f"Network change: {action}"
        elif action in ("service_start", "service_stop", "service_restart"):
            return 2, f"Service modification: {action}"
        elif action in ("hibernate", "log_out"):
            return 2, f"Power change: {action}"
        elif action in ("restart", "shutdown", "empty_recycle_bin", "delete"):
            return 3, f"Irreversible action: {action}"
        else:
            return 1, f"System control: {action}"

    # Global check: only shutdown, restart, and delete can ever require Level 3 confirmation
    action = str(parameters.get("action", "")).lower().strip()
    if action in ("shutdown", "restart", "delete", "delete_file", "delete_folder", "remove", "empty_recycle_bin"):
        return 3, f"Irreversible action: {action}"

    # Default fallback
    return 1, "Default reversible action"
