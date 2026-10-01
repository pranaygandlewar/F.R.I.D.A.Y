import json
import traceback

class Mission:
    def __init__(self, description: str, steps: list):
        self.description = description
        self.steps = steps  # list of dicts: {"tool": str, "params": dict, "status": "PENDING", "result": ""}
        self.current_step = 0
        self.status = "RUNNING" # RUNNING, PAUSED, CANCELLED, COMPLETED, FAILED

_CURRENT_MISSION = None

def planner(parameters: dict, player=None, **kwargs) -> str:
    global _CURRENT_MISSION
    action = parameters.get("action", "").lower()
    
    if action == "start":
        desc = parameters.get("mission", "Unknown Mission")
        steps = parameters.get("steps", [])
        if not steps:
            return "No steps provided for the mission."
        for s in steps:
            s["status"] = "PENDING"
            s["result"] = ""
            s["risk_level"] = "UNKNOWN"
            s["verification"] = "PENDING"
        _CURRENT_MISSION = Mission(desc, steps)
        
        return f"Mission '{desc}' started with {len(steps)} steps. Use the appropriate tools to execute step 1, or use planner 'next_step' if you want me to guide you."
        
    elif action == "status":
        if not _CURRENT_MISSION:
            return "No active mission."
        res = [f"Mission: {_CURRENT_MISSION.description}", f"Status: {_CURRENT_MISSION.status}"]
        for i, s in enumerate(_CURRENT_MISSION.steps):
            res.append(f" {i+1}. {s.get('tool')} - {s.get('status')} - {s.get('result')}")
        return "\n".join(res)
        
    elif action == "update_step":
        if not _CURRENT_MISSION:
            return "No active mission."
        idx = parameters.get("step_index", -1)
        if 0 <= idx < len(_CURRENT_MISSION.steps):
            step = _CURRENT_MISSION.steps[idx]
            if "status" in parameters: step["status"] = parameters["status"]
            if "result" in parameters: step["result"] = parameters["result"]
            if "verification" in parameters: step["verification"] = parameters["verification"]
            if "risk_level" in parameters: step["risk_level"] = parameters["risk_level"]
            return f"Step {idx} updated."
        return "Invalid step index."
        
    elif action == "pause":
        if _CURRENT_MISSION:
            _CURRENT_MISSION.status = "PAUSED"
            return "Mission paused."
        return "No active mission."
        
    elif action == "resume":
        if _CURRENT_MISSION:
            _CURRENT_MISSION.status = "RUNNING"
            return "Mission resumed."
        return "No active mission."
        
    elif action == "cancel":
        if _CURRENT_MISSION:
            _CURRENT_MISSION.status = "CANCELLED"
            return "Mission cancelled."
        return "No active mission."
        
    return f"Unknown planner action: {action}"

TOOL = {
    "name": "planner",
    "description": "Lightweight planner for multi-step requests and mission control. Use this when a user asks for multiple distinct operations.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "One of: start, status, update_step, pause, resume, cancel"
            },
            "mission": {
                "type": "STRING",
                "description": "Description of the mission (for start)"
            },
            "steps": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "tool": {"type": "STRING"},
                        "params": {"type": "OBJECT"}
                    }
                },
                "description": "List of steps (for start)"
            },
            "step_index": {
                "type": "INTEGER",
                "description": "Index of the step to update (for update_step)"
            },
            "status": {
                "type": "STRING",
                "description": "PENDING, RUNNING, WAITING_CONFIRMATION, COMPLETED, FAILED, BLOCKED, CANCELLED"
            },
            "result": {
                "type": "STRING",
                "description": "Result or error message"
            },
            "verification": {
                "type": "STRING",
                "description": "SUCCESS, FAILED, UNKNOWN"
            },
            "risk_level": {
                "type": "STRING",
                "description": "EDITH risk level of the step"
            }
        },
        "required": ["action"]
    },
    "handler": planner
}
