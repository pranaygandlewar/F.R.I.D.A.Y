"""
FRIDAY PRM — Full Regression Test Suite
Tests: Public Mode, Private Mode, Security, Regression (existing features)
"""
import sys, json
sys.path.insert(0, '.')

from core.private_mode import (
    set_private_mode_active, is_private_mode_active,
    is_sensitive_query, is_sensitive_entry, is_personal_contact,
    verify_password, enable_private_mode, disable_private_mode,
)
from memory.memory_manager import (
    format_memory_for_prompt, search_memory, load_memory,
)
from memory.prm_manager import (
    get_person, list_people, search_prm, format_prm_for_prompt,
    add_memory, forget_memory, show_profile, update_person,
)
from core.action_loader import discover_actions
from pathlib import Path

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

memory = load_memory()

# ════════════════════════════════════════════════════════════
print("\n══ 1. PUBLIC MODE TESTS (Private Mode OFF) ══")
# ════════════════════════════════════════════════════════════
set_private_mode_active(False)

# 1a. get_person returns None
r = get_person("divya")
if r is None: ok("get_person('divya') = None when locked")
else: fail("get_person should return None", str(r)[:60])

# 1b. get_person via alias returns None
r = get_person("khushi")
if r is None: ok("get_person('khushi') alias = None when locked")
else: fail("get_person alias should return None", str(r)[:60])

# 1c. list_people locked
r = list_people()
if "Personal Mode" in r: ok("list_people locked")
else: fail("list_people not locked", r[:60])

# 1d. search_prm locked
r = search_prm("divya")
if "Personal Mode" in r: ok("search_prm('divya') locked")
else: fail("search_prm not locked", r[:60])

# 1e. format_prm_for_prompt returns empty
r = format_prm_for_prompt()
if r == "": ok("format_prm_for_prompt() = '' when locked")
else: fail("format_prm_for_prompt leaked", r[:60])

# 1f. add_memory locked
r = add_memory("divya", "test")
if "Personal Mode" in r: ok("add_memory locked")
else: fail("add_memory not locked", r[:60])

# 1g. update_person locked
r = update_person("divya", "personal_significance", "test")
if "Personal Mode" in r: ok("update_person locked")
else: fail("update_person not locked", r[:60])

# 1h. show_profile locked
r = show_profile("divya")
if "Personal Mode" in r: ok("show_profile locked")
else: fail("show_profile not locked", r[:60])

# 1i. forget_memory locked
r = forget_memory("divya", 0)
if "Personal Mode" in r: ok("forget_memory locked")
else: fail("forget_memory not locked", r[:60])

# 1j. search_memory('divya') returns locked message
r = search_memory("divya")
if "Personal Mode" in r or "personal information" in r.lower():
    ok("search_memory('divya') returns locked message")
else: fail("search_memory('divya') not locked", r[:80])

# 1k. format_memory_for_prompt does NOT contain PRM block
prompt_block = format_memory_for_prompt(memory)
if "PRIVATE MODE ACTIVE" not in prompt_block:
    ok("format_memory_for_prompt: no PRM block when locked")
else: fail("PRM block leaked into public prompt", prompt_block[:60])

# ════════════════════════════════════════════════════════════
print("\n══ 2. PRIVATE MODE TESTS (Private Mode ON) ══")
# ════════════════════════════════════════════════════════════
set_private_mode_active(True)

# 2a. get_person returns profile
p = get_person("divya")
if p is not None and p.get("name") == "Divya":
    ok("get_person('divya') returns profile when unlocked")
else: fail("get_person failed", str(p)[:60])

# 2b. alias resolution
p = get_person("khushi")
if p is not None and p.get("name") == "Divya":
    ok("get_person('khushi') alias resolves to Divya")
else: fail("alias resolution failed", str(p)[:60])

# 2c. list_people contains Divya
r = list_people()
if "Divya" in r: ok("list_people shows Divya")
else: fail("list_people missing Divya", r[:60])

# 2d. search_prm returns profile
r = search_prm("divya")
if "Divya" in r and "loves" in r.lower(): ok("search_prm('divya') returns profile")
else: fail("search_prm missing data", r[:80])

# 2e. format_prm_for_prompt contains all required sections
prm = format_prm_for_prompt()
checks = [
    ("PRIVATE MODE ACTIVE", "header present"),
    ("Divya", "Divya in block"),
    ("romantic", "relationship category"),
    ("loves", "user feelings"),
    ("homingo", "hackathon professional context"),
]
for check, label in checks:
    if check.lower() in prm.lower(): ok(f"format_prm_for_prompt: {label}")
    else: fail(f"format_prm_for_prompt missing {label}", prm[:100])

# 2f. add_memory then verify stored
r = add_memory("divya", "Talked about project deadlines")
if "saved" in r.lower(): ok("add_memory: saved")
else: fail("add_memory failed", r)
p2 = get_person("divya")
if p2 and len(p2.get("shared_memories", [])) >= 1: ok("shared_memories count incremented")
else: fail("shared_memories not updated", str(p2)[:60])

# 2g. show_profile full
r = show_profile("divya")
if "Divya" in r and "romantic" in r and "feelings" in r.lower():
    ok("show_profile returns full profile")
else: fail("show_profile incomplete", r[:100])

# 2h. forget_memory removes the memory we just added
r = forget_memory("divya", 0)
if "removed" in r.lower() or "Memory removed" in r: ok("forget_memory removed memory")
else: fail("forget_memory failed", r)
p3 = get_person("divya")
if p3 and len(p3.get("shared_memories", [])) == 0: ok("shared_memories back to 0 after forget")
else: fail("shared_memories not removed", str(p3)[:60])

# 2i. search_memory returns PRM data when unlocked
r = search_memory("divya")
if "Personal Relationships" in r or ("Divya" in r and "loves" in r.lower()):
    ok("search_memory('divya') includes PRM data when unlocked")
else: fail("PRM data missing from search_memory", r[:120])

# 2j. format_memory_for_prompt includes PRM block
prompt_block = format_memory_for_prompt(memory)
if "PRIVATE MODE ACTIVE" in prompt_block:
    ok("format_memory_for_prompt: PRM block present when unlocked")
else: fail("PRM block missing from prompt when unlocked", prompt_block[:80])

# ════════════════════════════════════════════════════════════
print("\n══ 3. SECURITY TESTS ══")
# ════════════════════════════════════════════════════════════

# 3a. disable → PRM locked immediately
disable_private_mode()
r = get_person("divya")
if r is None: ok("get_person None after disable_private_mode()")
else: fail("get_person not locked after disable", str(r)[:60])

r = format_prm_for_prompt()
if r == "": ok("format_prm_for_prompt empty after disable")
else: fail("PRM not locked after disable", r[:60])

# 3b. Wrong password → no access
set_private_mode_active(False)
ok_flag, msg = enable_private_mode("wrong password")
if not ok_flag and not is_private_mode_active():
    ok("Wrong password: Private Mode stays OFF")
else: fail("Wrong password granted access!")

r = get_person("divya")
if r is None: ok("get_person None after wrong password")
else: fail("get_person leaked after wrong password", str(r)[:60])

# 3c. Correct password → enable works
ok_flag2, _ = enable_private_mode("12 11 7")
if ok_flag2 and is_private_mode_active():
    ok("Correct password (12 11 7): Private Mode enabled")
else: fail("Correct password failed to enable Private Mode")

# 3d. PRM file has no password stored
prm_raw = Path("memory/personal_relationships.json").read_text(encoding="utf-8")
for pw_hint in ["12 11 7", "barah gyarah", "bara akra", "twelve eleven"]:
    if pw_hint in prm_raw:
        fail(f"Password hint '{pw_hint}' found in PRM file!")
    else:
        ok(f"PRM file: no password hint '{pw_hint}'")

# 3e. Update person is blocked when Private Mode OFF
set_private_mode_active(False)
r = update_person("divya", "personal_significance", "HACKED")
if "Personal Mode" in r:
    ok("update_person blocked when Private Mode OFF")
else: fail("update_person not blocked!", r[:60])

# Verify value not changed
set_private_mode_active(True)
p_check = get_person("divya")
if p_check and "HACKED" not in p_check.get("personal_significance", ""):
    ok("Significance not modified by blocked update")
else: fail("Significance was modified by blocked update!")

# 3f. Auth check is before file I/O (verify _priv() check)
set_private_mode_active(False)
import io, unittest.mock as mock
calls = []
original_load = __import__("memory.prm_manager", fromlist=["load_prm"]).load_prm
def mock_load():
    calls.append("load_prm_called")
    return original_load()
with mock.patch("memory.prm_manager.load_prm", mock_load):
    _ = get_person("divya")
if not calls:
    ok("Auth check is BEFORE file I/O (load_prm not called when locked)")
else: fail("load_prm was called even when Private Mode OFF — auth check too late!")

set_private_mode_active(False)

# ════════════════════════════════════════════════════════════
print("\n══ 4. REGRESSION TESTS (Existing Features) ══")
# ════════════════════════════════════════════════════════════

# 4a. Password verification still works
for pw, expected in [
    ("12 11 7", True), ("barah gyarah sat", True), ("bara akra sat", True),
    ("twelve eleven seven", True), ("wrong", False), ("12 11", False),
]:
    result = verify_password(pw)
    if result == expected: ok(f"verify_password('{pw}') = {expected}")
    else: fail(f"verify_password('{pw}')", f"expected {expected} got {result}")

# 4b. is_sensitive_query still works
for q, expected in [
    ("who is divya", True), ("divya ka number", True),
    ("what is the weather", False), ("open chrome", False),
]:
    r = is_sensitive_query(q)
    if r == expected: ok(f"is_sensitive_query('{q}') = {expected}")
    else: fail(f"is_sensitive_query('{q}')", f"expected {expected} got {r}")

# 4c. is_sensitive_entry still works
assert is_sensitive_entry("relationships", "divya_name", "Wife") == True
ok("is_sensitive_entry(relationships/divya_name) = True")
assert is_sensitive_entry("preferences", "favorite_color", "black") == False
ok("is_sensitive_entry(preferences/favorite_color) = False")

# 4d. is_personal_contact still works
assert is_personal_contact("divya") == True; ok("is_personal_contact('divya') = True")
assert is_personal_contact("shruti") == True; ok("is_personal_contact('shruti') = True")
assert is_personal_contact("john") == False; ok("is_personal_contact('john') = False")

# 4e. format_memory_for_prompt still filters sensitive entries when locked
set_private_mode_active(False)
locked_prompt = format_memory_for_prompt(memory)   # fresh call with mode OFF
priv_data = ["9699645603", "divya", "7057274830"]
for sensitive in priv_data:
    if sensitive in locked_prompt.lower():
        fail(f"Sensitive data '{sensitive}' leaked into locked prompt")
    else:
        ok(f"Locked prompt: '{sensitive}' not present")

# 4f. Action tool still discoverable
registry = discover_actions(Path("actions"), logger=lambda x: None)
for tool_name in ["relationship_memory", "personal_mode", "send_message"]:
    if registry.has(tool_name): ok(f"Action '{tool_name}' still discovered")
    else: fail(f"Action '{tool_name}' missing from registry!")

# ════════════════════════════════════════════════════════════
print(f"\n══ RESULTS: {passed} passed / {failed} failed ══")
if failed == 0:
    print("✅  ALL TESTS PASSED — PRM implementation complete.")
else:
    print(f"❌  {failed} FAILURES — review output above.")
    sys.exit(1)
