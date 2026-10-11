"""
actions/planner.py - Multi-step Mission Execution Engine for FRIDAY
"""
from __future__ import annotations

import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Data model ──────────────────────────────────────────────────────────────

@dataclass
class MissionStep:
    step_id: int
    tool: str
    params: dict = field(default_factory=dict)
    description: str = ""
    risk_level: int = -1
    edith_reason: str = ""
    status: str = "PENDING"
    result: str = ""
    verification_result: str = "PENDING"
    error: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class Mission:
    description: str
    steps: list
    state: str = "PLANNING"
    current_index: int = 0
    context: dict = field(default_factory=dict)
    started_at: float = field(default_factory=time.monotonic)
    completed_at: Optional[float] = None

    @property
    def current_step(self):
        if 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    @property
    def completed_count(self):
        return sum(1 for s in self.steps if s.status == "COMPLETED")

    @property
    def total_count(self):
        return len(self.steps)

    def summary(self):
        lines = [
            f"Mission: {self.description}",
            f"State: {self.state}  ({self.completed_count}/{self.total_count} completed)",
        ]
        for s in self.steps:
            verif = f"  [verify={s.verification_result}]" if s.verification_result not in ("PENDING", "") else ""
            err = f"  ERROR: {s.error}" if s.error else ""
            lines.append(f"  Step {s.step_id}. {s.tool}({s.description}) -> {s.status}{verif}{err}")
        return "\n".join(lines)


# ── Module state ─────────────────────────────────────────────────────────────

_mission: Optional[Mission] = None
_lock = threading.Lock()
_action_runner: Optional[Any] = None


def bind_action_runner(runner) -> None:
    """Call once at startup from main.py: bind_action_runner(action_registry)"""
    global _action_runner
    _action_runner = runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run_action(name: str, params: dict):
    """Execute name through the registry (EDITH + confirm gate included)."""
    if _action_runner is None:
        return "", "Action runner not bound."
    try:
        result = _action_runner.run(name, params, ctx={})
        return str(result or "Done."), ""
    except Exception as e:
        traceback.print_exc()
        return "", str(e)


def _verify_step(step: MissionStep) -> str:
    """Best-effort post-execution verification. Returns SUCCESS/FAILED/UNAVAILABLE."""
    try:
        tool = step.tool.lower()
        result_lower = step.result.lower()

        if tool == "laptop_control":
            action = str(step.params.get("action", "")).lower()
            if action == "bluetooth_on":
                if _action_runner and _action_runner.has("laptop_control"):
                    chk, _ = _run_action("laptop_control", {"action": "bluetooth_status"})
                    return "SUCCESS" if any(w in chk.lower() for w in ("on", "enabled", "connected")) else "FAILED"
            elif action == "bluetooth_off":
                if _action_runner and _action_runner.has("laptop_control"):
                    chk, _ = _run_action("laptop_control", {"action": "bluetooth_status"})
                    return "SUCCESS" if any(w in chk.lower() for w in ("off", "disabled")) else "FAILED"
            elif action in ("wifi_on", "wifi_off"):
                if _action_runner and _action_runner.has("laptop_control"):
                    chk, _ = _run_action("laptop_control", {"action": "wifi_status"})
                    if action == "wifi_on":
                        return "SUCCESS" if any(w in chk.lower() for w in ("connected", "enabled")) else "FAILED"
                    else:
                        return "SUCCESS" if any(w in chk.lower() for w in ("disconnected", "disabled")) else "FAILED"
            elif action in ("maximize_window", "minimize_window", "restore_window"):
                if _action_runner and _action_runner.has("laptop_control"):
                    chk, _ = _run_action("laptop_control", {"action": "list_windows"})
                    return "SUCCESS" if ("error" not in chk.lower() and chk.strip()) else "UNAVAILABLE"
            elif action in ("volume_set", "volume_up", "volume_down", "mute", "unmute"):
                return "SUCCESS" if ("error" not in result_lower and "failed" not in result_lower) else "FAILED"
            else:
                return "SUCCESS" if ("error" not in result_lower and "failed" not in result_lower) else "UNAVAILABLE"

        elif tool == "open_app":
            app = str(step.params.get("app", step.params.get("name", ""))).lower()
            if _action_runner and _action_runner.has("laptop_control"):
                chk, _ = _run_action("laptop_control", {"action": "list_windows"})
                if app and app[:5] in chk.lower():
                    return "SUCCESS"
            return "SUCCESS" if ("error" not in result_lower and "failed" not in result_lower and "not found" not in result_lower) else "FAILED"

        elif tool == "computer_settings":
            return "SUCCESS" if ("error" not in result_lower and "failed" not in result_lower) else "FAILED"

        elif tool == "web_search":
            return "SUCCESS" if (result_lower and "no results" not in result_lower and "failed" not in result_lower) else "FAILED"

        elif tool == "browser_control":
            return "SUCCESS" if ("error" not in result_lower and "failed" not in result_lower) else "UNAVAILABLE"

        elif tool in ("file_controller", "file_processor"):
            return "SUCCESS" if ("error" not in result_lower and "failed" not in result_lower and "not found" not in result_lower) else "FAILED"

        else:
            return "SUCCESS" if ("error" not in result_lower and "failed" not in result_lower and "blocked" not in result_lower) else "UNAVAILABLE"

    except Exception:
        return "UNAVAILABLE"


def _skip_remaining(mission: Mission) -> None:
    for s in mission.steps:
        if s.status == "PENDING":
            s.status = "SKIPPED"


# ── Main handler ─────────────────────────────────────────────────────────────

def planner(parameters: dict, player=None, **kwargs) -> str:
    global _mission
    action = str(parameters.get("action", "")).lower().strip()

    # ── START ────────────────────────────────────────────────────────────────
    if action == "start":
        with _lock:
            if _mission and _mission.state in ("COMPLETED", "FAILED", "CANCELLED"):
                _mission = None
            if _mission:
                return (f"Mission already active (state={_mission.state}). "
                        "Call planner action='cancel' first.")
            desc = str(parameters.get("mission", "Mission"))
            raw = parameters.get("steps", [])
            if not raw:
                return "No steps provided."
            steps = []
            for i, s in enumerate(raw or []):
                if not isinstance(s, dict):
                    continue
                steps.append(MissionStep(
                    step_id=i + 1,
                    tool=str(s.get("tool", "")),
                    params=dict(s.get("params", {})),
                    description=str(s.get("description", s.get("tool", ""))),
                ))
            if not steps:
                return "No valid steps. Each step needs a 'tool' field."
            _mission = Mission(description=desc, steps=steps)
        lines = "\n".join(f"  {s.step_id}. {s.tool}: {s.description}" for s in steps)
        return (f"Mission '{desc}' registered with {len(steps)} steps:\n{lines}\n\n"
                "Call planner action='next_step' to begin step 1.")

    # ── NEXT_STEP ────────────────────────────────────────────────────────────
    elif action == "next_step":
        with _lock:
            if _mission is None:
                return "No active mission. Use action='start' first."
            if _mission.state == "PAUSED":
                return "Mission is paused. Use action='resume' first."
            if _mission.state == "WAITING_CONFIRMATION":
                return "Waiting for user confirmation on screen. Do not continue until confirmed."
            if _mission.state in ("CANCELLED", "COMPLETED", "FAILED"):
                return f"Mission is already {_mission.state}."

            step = None
            for s in _mission.steps:
                if s.status == "PENDING":
                    step = s
                    _mission.current_index = _mission.steps.index(s)
                    break

            if step is None:
                _mission.state = "COMPLETED"
                _mission.completed_at = time.monotonic()
                return _mission.summary() + "\n\nAll steps complete."

            _mission.state = "EXECUTING"
            step.status = "RUNNING"
            step.started_at = time.monotonic()

            override = parameters.get("params")
            if isinstance(override, dict) and override:
                step.params.update(override)

        # EDITH evaluation
        from core import edith as _edith
        risk, reason = _edith.evaluate(step.tool, step.params)
        with _lock:
            step.risk_level = risk
            step.edith_reason = reason

        if risk == 4:
            with _lock:
                step.status = "BLOCKED"
                step.error = f"EDITH Level 4 blocked: {reason}"
                _skip_remaining(_mission)
                _mission.state = "FAILED"
            return (f"[EDITH BLOCKED] Step {step.step_id} ({step.tool}): {reason}\n"
                    f"Mission FAILED. Remaining steps skipped.\n\n{_mission.summary()}")

        if risk >= 3:
            with _lock:
                step.status = "WAITING_CONFIRMATION"
                _mission.state = "WAITING_CONFIRMATION"

            result, err = _run_action(step.tool, step.params)

            with _lock:
                if err:
                    step.status = "FAILED"
                    step.error = err
                    _skip_remaining(_mission)
                    _mission.state = "FAILED"
                    return (f"Step {step.step_id} ({step.tool}) failed: {err}\n"
                            f"Remaining steps skipped.\n\n{_mission.summary()}")

                if "[CONFIRMATION_PENDING]" in result:
                    step.result = result
                    return (f"[MISSION_WAITING_CONFIRMATION]\n"
                            f"Step {step.step_id}/{len(_mission.steps)}: {step.tool} (Risk {risk}) "
                            f"requires confirmation.\n{result}\n\n"
                            f"Tell the user to confirm on screen. After they confirm, "
                            f"call planner action='step_confirmed', then continue with next_step.")
                else:
                    step.status = "COMPLETED"
                    step.result = result
                    step.completed_at = time.monotonic()
                    step.verification_result = _verify_step(step)
                    _mission.state = "EXECUTING"
                    _mission.context[f"step_{step.step_id}_result"] = result
                    _mission.context["last_result"] = result
                    remaining = sum(1 for s in _mission.steps if s.status == "PENDING")
                    return (f"Step {step.step_id}/{len(_mission.steps)} COMPLETED: {step.tool}\n"
                            f"Result: {result}\nVerification: {step.verification_result}\n"
                            f"Context: {_mission.context}\nRemaining: {remaining}\n"
                            + ("Call planner action='next_step' to continue." if remaining
                               else "Mission complete. Call planner action='status'."))

        # Normal execution
        result, err = _run_action(step.tool, step.params)

        with _lock:
            step.completed_at = time.monotonic()
            # Patterns that indicate the action itself failed or was unavailable
            _fail_patterns = (
                "[BLOCKED]",
                "is not available",
                "action not found",
                "could not find",
                "not found",
                "failed to open",
                "failed to launch",
                "error:",
            )
            is_failure = bool(err)
            if not is_failure and result:
                rl = result.lower()
                is_failure = any(p in rl for p in _fail_patterns)
            if is_failure:
                step.status = "FAILED"
                step.error = err or result
                step.verification_result = "FAILED"
                _skip_remaining(_mission)
                _mission.state = "FAILED"
                summary = _mission.summary()
            else:
                step.result = result
                step.status = "COMPLETED"
                step.verification_result = _verify_step(step)
                # If verification itself is FAILED, mark the step failed too
                if step.verification_result == "FAILED":
                    step.status = "FAILED"
                    step.error = f"Verification failed after executing {step.tool}"
                    _skip_remaining(_mission)
                    _mission.state = "FAILED"
                else:
                    _mission.context[f"step_{step.step_id}_result"] = result
                    _mission.context["last_result"] = result
                    if step.description and step.description != step.tool:
                        _mission.context[step.description.lower().replace(" ", "_")[:40]] = result
                    remaining = sum(1 for s in _mission.steps if s.status == "PENDING")
                    if remaining == 0:
                        _mission.state = "COMPLETED"
                        _mission.completed_at = time.monotonic()
                summary = _mission.summary()


        if step.status == "FAILED":
            return (f"Step {step.step_id}/{len(_mission.steps)} FAILED: {step.tool}\n"
                    f"Error: {step.error}\nRemaining steps SKIPPED.\n\n{summary}")

        remaining = sum(1 for s in _mission.steps if s.status == "PENDING")
        return (f"Step {step.step_id}/{len(_mission.steps)} COMPLETED: {step.tool}\n"
                f"Result: {str(result)[:200]}\nVerification: {step.verification_result}\n"
                f"Mission context: {_mission.context}\nRemaining steps: {remaining}\n"
                + ("Call planner action='next_step' to continue." if remaining
                   else "All steps done. Call planner action='status' for final report."))

    # ── STEP_CONFIRMED ────────────────────────────────────────────────────────
    elif action == "step_confirmed":
        with _lock:
            if _mission is None:
                return "No active mission."
            if _mission.state != "WAITING_CONFIRMATION":
                return f"Mission not awaiting confirmation (state={_mission.state})."
            step = _mission.current_step
            if step is None:
                return "No current step found."
            step.status = "COMPLETED"
            step.completed_at = time.monotonic()
            step.verification_result = "SUCCESS"
            step.result = step.result or "Confirmed by user."
            _mission.context[f"step_{step.step_id}_result"] = step.result
            _mission.context["last_result"] = step.result
            _mission.state = "EXECUTING"
            remaining = sum(1 for s in _mission.steps if s.status == "PENDING")
            if remaining == 0:
                _mission.state = "COMPLETED"
        return (f"Step {step.step_id} confirmed and COMPLETED.\nRemaining: {remaining}\n"
                + ("Call planner action='next_step' to continue." if remaining
                   else "Mission complete."))

    # ── STATUS ────────────────────────────────────────────────────────────────
    elif action == "status":
        with _lock:
            if _mission is None:
                return "No active mission. State: IDLE."
            return _mission.summary()

    # ── UPDATE_STEP ───────────────────────────────────────────────────────────
    elif action == "update_step":
        with _lock:
            if _mission is None:
                return "No active mission."
            idx = int(parameters.get("step_index", -1))
            if not (0 <= idx < len(_mission.steps)):
                return f"Invalid step_index {idx}."
            s = _mission.steps[idx]
            for f in ("status", "result", "verification_result", "risk_level", "error"):
                if f in parameters:
                    setattr(s, f, parameters[f])
            return f"Step {idx+1} updated to {s.status}."

    # ── PAUSE ─────────────────────────────────────────────────────────────────
    elif action == "pause":
        with _lock:
            if _mission is None:
                return "No active mission."
            if _mission.state not in ("EXECUTING", "PLANNING"):
                return f"Cannot pause — mission is {_mission.state}."
            _mission.state = "PAUSED"
            remaining = sum(1 for s in _mission.steps if s.status == "PENDING")
            return (f"Mission paused. {_mission.completed_count}/{_mission.total_count} "
                    f"done, {remaining} remaining. Use action='resume' to continue.")

    # ── RESUME ────────────────────────────────────────────────────────────────
    elif action == "resume":
        with _lock:
            if _mission is None:
                return "No active mission."
            if _mission.state != "PAUSED":
                return f"Mission is not paused (state={_mission.state})."
            _mission.state = "EXECUTING"
            remaining = sum(1 for s in _mission.steps if s.status == "PENDING")
            return (f"Mission resumed. {remaining} steps remaining. "
                    "Call planner action='next_step' to continue.")

    # ── CANCEL ────────────────────────────────────────────────────────────────
    elif action == "cancel":
        with _lock:
            if _mission is None:
                return "No active mission."
            completed = _mission.completed_count
            total = _mission.total_count
            for s in _mission.steps:
                if s.status in ("PENDING", "RUNNING", "WAITING_CONFIRMATION"):
                    s.status = "CANCELLED"
            _mission.state = "CANCELLED"
            _mission.completed_at = time.monotonic()
            return f"Mission cancelled. {completed}/{total} steps had completed."

    # ── CLEAR ─────────────────────────────────────────────────────────────────
    elif action == "clear":
        with _lock:
            if _mission is None:
                return "No mission to clear."
            _mission = None
        return "Mission cleared. Ready for a new mission."

    return (f"Unknown action: '{action}'. Valid: "
            "start | next_step | step_confirmed | status | update_step | pause | resume | cancel | clear")


# ── Tool declaration ──────────────────────────────────────────────────────────

TOOL = {
    "name": "planner",
    "description": (
        "Multi-step mission execution engine. Use this when the user asks for "
        "multiple distinct operations in one request "
        "(e.g. 'turn on Bluetooth, open Chrome, and search for AI internships'). "
        "WORKFLOW: (1) Call action='start' with mission description and steps list. "
        "(2) Call action='next_step' repeatedly — EDITH evaluates each step independently, "
        "executes it, verifies the result, and passes context to the next step. "
        "If a step needs user confirmation the mission pauses automatically. "
        "If a step fails, remaining steps are SKIPPED automatically. "
        "(3) Call action='status' for the final report after all steps. "
        "User control: action='pause'/'resume'/'cancel' at any time. "
        "Do NOT use this for single-action requests — call that tool directly instead."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": ("One of: start | next_step | step_confirmed | "
                                "status | update_step | pause | resume | cancel | clear")
            },
            "mission": {
                "type": "STRING",
                "description": "Overall mission description (required for start)"
            },
            "steps": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "tool":        {"type": "STRING",  "description": "Exact tool/action name to call"},
                        "params":      {"type": "OBJECT",  "description": "Parameters for this tool"},
                        "description": {"type": "STRING",  "description": "Human-readable step label"},
                    }
                },
                "description": "Ordered list of steps (required for start)"
            },
            "params": {
                "type": "OBJECT",
                "description": ("Optional param overrides for the current next_step call. "
                                "Use to inject context from earlier steps into the current one.")
            },
            "step_index": {
                "type": "INTEGER",
                "description": "0-based step index for update_step"
            },
            "status": {
                "type": "STRING",
                "description": "New status for update_step"
            },
            "result": {
                "type": "STRING",
                "description": "Result text for update_step"
            },
            "verification_result": {
                "type": "STRING",
                "description": "SUCCESS | FAILED | UNAVAILABLE for update_step"
            },
            "risk_level": {
                "type": "INTEGER",
                "description": "EDITH risk level for update_step (0-4)"
            },
            "error": {
                "type": "STRING",
                "description": "Error text for update_step"
            }
        },
        "required": ["action"]
    },
    "handler": planner
}
