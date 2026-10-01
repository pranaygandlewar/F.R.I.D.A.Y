import json
import logging

def evaluate(tool_name: str, parameters: dict) -> tuple[int, str]:
    """
    EDITH Security Policy.
    Returns (risk_level, reason).
    LEVEL 0 — INFORMATION
    LEVEL 1 — REVERSIBLE
    LEVEL 2 — SENSITIVE
    LEVEL 3 — HIGH RISK / IRREVERSIBLE
    LEVEL 4 — BLOCKED
    """
    
    # 1. Computer Settings
    if tool_name == "computer_settings":
        action = str(parameters.get("action", "")).lower().strip()
        if not action and parameters.get("description"):
            # A rough estimate if action is missing but description is present
            desc = parameters.get("description", "").lower()
            if "wifi" in desc or "restart" in desc or "shutdown" in desc:
                return 3, "Potentially irreversible system change"
                
        if action in ("restart", "shutdown", "toggle_wifi"):
            return 3, f"Irreversible action: {action}"
        elif action in ("volume_up", "volume_down", "volume_set", "mute", "unmute", "toggle_mute", "brightness_up", "brightness_down", "dark_mode"):
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
        if action in ("read", "list", "search"):
            return 0, "Read-only file access"
        elif action in ("create", "write", "append", "rename", "move"):
            return 1, "Reversible file modification"
        elif action == "delete":
            return 3, "Irreversible file deletion"
        else:
            return 2, "File operation"
            
    # 6. File Processor
    elif tool_name == "file_processor":
        action = str(parameters.get("action", "")).lower().strip()
        if action in ("read", "summarize", "search"):
            return 0, "Read-only file access"
        elif action in ("delete"):
            return 3, "Irreversible file deletion"
        else:
            return 1, "File processing"

    # 7. System Monitor / Background Monitor
    elif tool_name in ("system_status", "manage_monitor"):
        return 0, "System information access"
        
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
        if action in ("battery_status", "wifi_status", "bluetooth_status", "cpu_info", "gpu_info", "ram_usage", "disk_usage", "temperature", "network_status", "running_processes", "uptime", "os_version", "hardware_info", "list_windows", "list_audio_devices"):
            return 0, "System information access"
        elif action in ("focus_window", "minimize_window", "maximize_window", "restore_window", "move_window", "resize_window", "center_window", "bring_to_front"):
            return 1, "Window management"
        elif action in ("bluetooth_on", "bluetooth_off", "wifi_on", "wifi_off"):
            return 3, f"Irreversible network change: {action}"
        elif action in ("service_start", "service_stop", "service_restart"):
            return 3, f"Service modification: {action}"
        elif action in ("hibernate", "log_out"):
            return 3, f"Power change: {action}"
        else:
            return 2, f"System control: {action}"

    # Default fallback
    return 1, "Default reversible action"
