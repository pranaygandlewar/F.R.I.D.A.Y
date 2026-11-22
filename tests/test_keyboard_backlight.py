"""
Test suite for Keyboard Backlit & Aura (Fn + F4) control.
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from core.action_loader import discover_actions
from actions.computer_settings import _detect_action, computer_settings
from actions.laptop_control import laptop_control
from core.asus_aura import cycle_keyboard_backlight

passed = 0
failed = 0

def ok(label):
    global passed
    passed += 1
    print(f"  PASS: {label}")

def fail(label, detail=""):
    global failed
    failed += 1
    print(f"  FAIL: {label}" + (f" — {detail}" if detail else ""))

print("\n══ 1. NATURAL LANGUAGE INTENT DETECTION ══")
test_phrases = [
    ("change backlit", "keyboard_backlight"),
    ("change backlit of keyboard", "keyboard_backlight"),
    ("change backlight", "keyboard_backlight"),
    ("keyboard light", "keyboard_backlight"),
    ("keyboard backlight", "keyboard_backlight"),
    ("aura", "keyboard_backlight"),
    ("change aura", "keyboard_backlight"),
    ("backlit color", "keyboard_backlight"),
    ("keyboard color", "keyboard_backlight"),
    ("fn f4", "keyboard_backlight"),
    ("keyboard light change", "keyboard_backlight"),
    ("change keyboard light", "keyboard_backlight"),
]

for phrase, expected in test_phrases:
    detected = _detect_action(phrase)
    action = detected.get("action")
    if action == expected:
        ok(f"'{phrase}' -> '{action}'")
    else:
        fail(f"'{phrase}' expected '{expected}'", f"got '{action}'")

print("\n══ 2. COMPUTER_SETTINGS EXECUTION ══")
# Cycle next
r1 = computer_settings({"action": "keyboard_backlight"})
if "Keyboard backlit changed via Fn + F4" in r1:
    ok(f"computer_settings(keyboard_backlight): {r1}")
else:
    fail("computer_settings(keyboard_backlight)", r1)

# Specific color - Red
r2 = computer_settings({"action": "keyboard_backlight", "value": "red"})
if "Red" in r2:
    ok(f"computer_settings(value='red'): {r2}")
else:
    fail("computer_settings with red", r2)

# Specific color - Rainbow
r3 = computer_settings({"action": "keyboard_backlight", "value": "rainbow"})
if "Color Cycle (Rainbow)" in r3:
    ok(f"computer_settings(value='rainbow'): {r3}")
else:
    fail("computer_settings with rainbow", r3)

# Description fallback
r4 = computer_settings({"description": "change backlit of keyboard"})
if "Keyboard backlit changed via Fn + F4" in r4:
    ok(f"computer_settings(description='change backlit of keyboard'): {r4}")
else:
    fail("description fallback failed", r4)

print("\n══ 3. LAPTOP_CONTROL EXECUTION ══")
r5 = laptop_control({"action": "keyboard_backlight"})
if "Keyboard backlit changed via Fn + F4" in r5:
    ok(f"laptop_control(action='keyboard_backlight'): {r5}")
else:
    fail("laptop_control(keyboard_backlight)", r5)

print("\n══ 4. ACTION LOADER DISCOVERY ══")
registry = discover_actions(Path("actions"), logger=lambda _: None)
if registry.has("computer_settings"):
    ok("registry has computer_settings")
else:
    fail("registry missing computer_settings")

if registry.has("laptop_control"):
    ok("registry has laptop_control")
else:
    fail("registry missing laptop_control")

print("\n══ 5. PROMPT VERIFICATION ══")
prompt_text = Path("core/prompt.txt").read_text(encoding="utf-8")
if "[KEYBOARD BACKLIT & AURA (FN + F4) PROTOCOL]" in prompt_text:
    ok("prompt.txt contains KEYBOARD BACKLIT & AURA section")
else:
    fail("prompt.txt missing KEYBOARD BACKLIT section")

if "keyboard_backlight" in prompt_text:
    ok("prompt.txt instructs calling computer_settings(action='keyboard_backlight')")
else:
    fail("prompt.txt missing action name")

print(f"\n══ TOTAL: {passed} passed / {failed} failed ══")
if failed == 0:
    print("✅  ALL KEYBOARD BACKLIT TESTS PASSED.")
else:
    sys.exit(1)
