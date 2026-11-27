"""
Test suite for Comprehensive Keyboard Backlit & Aura Control.
Tests brightness levels, named RGB colors, hex codes, effects, and natural language matching.
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from core.action_loader import discover_actions
from actions.computer_settings import _detect_action, computer_settings
from actions.laptop_control import laptop_control
from core.asus_aura import (
    cycle_keyboard_backlight,
    set_keyboard_brightness,
    get_keyboard_brightness,
    parse_color_and_mode,
)

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
    ("low the backlit", "keyboard_backlight"),
    ("dim the backlit", "keyboard_backlight"),
    ("keyboard brightness", "keyboard_backlight"),
]

for phrase, expected in test_phrases:
    detected = _detect_action(phrase)
    action = detected.get("action")
    if action == expected:
        ok(f"'{phrase}' -> '{action}'")
    else:
        fail(f"'{phrase}' expected '{expected}'", f"got '{action}'")

print("\n══ 2. COLOR & MODE PARSING ══")
colors_to_test = [
    ("red", (255, 0, 0), 0),
    ("emerald", (80, 200, 120), 0),
    ("hotpink", (255, 20, 147), 0),
    ("gold", (255, 215, 0), 0),
    ("navy", (0, 0, 128), 0),
    ("lavender", (230, 230, 250), 0),
    ("#FF00AA", (255, 0, 170), 0),
    ("rgb(100, 150, 200)", (100, 150, 200), 0),
    ("rainbow", (255, 0, 0), 2),
    ("breathing", (0, 255, 255), 1),
    ("strobe", (255, 255, 255), 3),
]

for c_str, exp_rgb, exp_mode in colors_to_test:
    rgb, mode, name = parse_color_and_mode(c_str)
    if rgb == exp_rgb and mode == exp_mode:
        ok(f"parse_color_and_mode('{c_str}') -> RGB {rgb}, mode {mode} ({name})")
    else:
        fail(f"parse_color_and_mode('{c_str}')", f"expected {exp_rgb}, mode {exp_mode}; got {rgb}, mode {mode}")

print("\n══ 3. BRIGHTNESS CONTROL ══")
# Test brightness setting and reading
for lvl in [0, 1, 2, 3]:
    res, set_lvl = set_keyboard_brightness(lvl)
    cur = get_keyboard_brightness()
    if set_lvl == lvl:
        ok(f"set_keyboard_brightness({lvl}) -> current {cur} (hardware ok={res})")
    else:
        fail(f"set_keyboard_brightness({lvl})", f"got set_lvl={set_lvl}")

# Test natural language brightness dispatch
r_low = cycle_keyboard_backlight("low the backlit")
if "lowered to Level" in r_low or "Level 1" in r_low:
    ok(f"cycle_keyboard_backlight('low the backlit'): {r_low}")
else:
    fail("cycle_keyboard_backlight('low the backlit')", r_low)

r_max = cycle_keyboard_backlight("max brightness")
if "Maximum" in r_max:
    ok(f"cycle_keyboard_backlight('max brightness'): {r_max}")
else:
    fail("cycle_keyboard_backlight('max brightness')", r_max)

print("\n══ 4. ALL RGB COLORS EXECUTION VIA COMPUTER_SETTINGS ══")
# Specific color - Crimson
r_crimson = computer_settings({"action": "keyboard_backlight", "value": "crimson"})
if "Crimson" in r_crimson:
    ok(f"computer_settings(value='crimson'): {r_crimson}")
else:
    fail("computer_settings with crimson", r_crimson)

# Specific Hex Code
r_hex = computer_settings({"action": "keyboard_backlight", "value": "#00FFAA"})
if "#00FFAA" in r_hex:
    ok(f"computer_settings(value='#00FFAA'): {r_hex}")
else:
    fail("computer_settings with #00FFAA", r_hex)

# Mode - Rainbow
r_rainbow = computer_settings({"action": "keyboard_backlight", "value": "rainbow"})
if "Color Cycle (Rainbow)" in r_rainbow:
    ok(f"computer_settings(value='rainbow'): {r_rainbow}")
else:
    fail("computer_settings with rainbow", r_rainbow)

print("\n══ 5. LAPTOP_CONTROL DISPATCH ══")
r_lap = laptop_control({"action": "keyboard_backlight", "value": "lavender"})
if "Lavender" in r_lap:
    ok(f"laptop_control(value='lavender'): {r_lap}")
else:
    fail("laptop_control(value='lavender')", r_lap)

print("\n══ 6. PROMPT & ACTION REGISTRY VERIFICATION ══")
registry = discover_actions(Path("actions"), logger=lambda _: None)
if registry.has("computer_settings") and registry.has("laptop_control"):
    ok("registry has computer_settings and laptop_control")
else:
    fail("registry check failed")

prompt_text = Path("core/prompt.txt").read_text(encoding="utf-8")
if "KEYBOARD BACKLIT & AURA (FN + F4) PROTOCOL" in prompt_text and "RGB color" in prompt_text:
    ok("prompt.txt contains enhanced RGB & Brightness protocol")
else:
    fail("prompt.txt missing enhanced RGB & Brightness protocol")

print(f"\n══ TOTAL: {passed} passed / {failed} failed ══")
if failed == 0:
    print("✅  ALL COMPREHENSIVE KEYBOARD BACKLIT TESTS PASSED.")
else:
    sys.exit(1)
