"""
Updated PRM test suite — public/private two-tier system.
"""
import sys, json
sys.path.insert(0, '.')

from core.private_mode import set_private_mode_active
from memory.memory_manager import format_memory_for_prompt, search_memory, load_memory
from memory.prm_manager import (
    get_person, get_public_info, list_people, search_prm,
    format_prm_for_prompt, format_public_prm_for_prompt,
    add_memory, forget_memory, show_profile,
)

passed = 0; failed = 0

def ok(label):
    global passed; passed += 1; print(f"  PASS: {label}")

def fail(label, detail=""):
    global failed; failed += 1
    print(f"  FAIL: {label}" + (f" — {detail[:80]}" if detail else ""))

memory = load_memory()

# ═══════════════════════════════════════════════
print("\n══ 1. PUBLIC MODE — Public info accessible ══")
# ═══════════════════════════════════════════════
set_private_mode_active(False)

# Public info always accessible
pub = get_public_info("divya")
if pub and "collegemate" in str(pub).lower(): ok("get_public_info('divya') returns public data")
else: fail("get_public_info failed", str(pub)[:80])

pub_alias = get_public_info("khushi")
if pub_alias and "collegemate" in str(pub_alias).lower(): ok("get_public_info('khushi') alias works")
else: fail("get_public_info alias failed", str(pub_alias)[:80])

# format_public_prm_for_prompt — always works
pub_block = format_public_prm_for_prompt()
for check in ["Divya", "collegemate", "hackathon", "exam partner"]:
    if check.lower() in pub_block.lower(): ok(f"Public PRM block contains '{check}'")
    else: fail(f"Public PRM block missing '{check}'", pub_block[:100])

# Private info still locked
priv = get_person("divya")
if priv is None: ok("get_person (private) = None when locked")
else: fail("get_person leaked private data")

priv_block = format_prm_for_prompt()
if priv_block == "": ok("format_prm_for_prompt = '' when locked")
else: fail("Private PRM leaked", priv_block[:60])

# ═══════════════════════════════════════════════
print("\n══ 2. PUBLIC MODE — search_prm shows public side ══")
# ═══════════════════════════════════════════════
r = search_prm("divya")
if "collegemate" in r.lower() or "hackathon" in r.lower():
    ok("search_prm('divya') returns public info when locked")
else: fail("search_prm public info missing", r[:100])

if "loves" not in r.lower() and "whole life" not in r.lower():
    ok("search_prm: private feelings NOT shown when locked")
else: fail("search_prm: private feelings leaked when locked!", r[:100])

if "Private Mode" in r or "private info hidden" in r.lower():
    ok("search_prm: indicates private mode needed for more")
else: fail("search_prm: no indicator about private mode", r[:100])

# format_memory_for_prompt includes public block, not private
prompt_block = format_memory_for_prompt(memory)
if "collegemate" in prompt_block.lower() or "hackathon" in prompt_block.lower():
    ok("format_memory_for_prompt: public PRM in prompt when locked")
else: fail("format_memory_for_prompt: public PRM missing", prompt_block[-200:])

if "PRIVATE MODE ACTIVE" not in prompt_block:
    ok("format_memory_for_prompt: no private PRM block when locked")
else: fail("Private PRM leaked into locked prompt")

if "9699645603" not in prompt_block and "loves her deeply" not in prompt_block:
    ok("format_memory_for_prompt: no sensitive private data when locked")
else: fail("Sensitive private data leaked into locked prompt")

# ═══════════════════════════════════════════════
print("\n══ 3. PRIVATE MODE — Full access ══")
# ═══════════════════════════════════════════════
set_private_mode_active(True)

# Private profile accessible
p = get_person("divya")
priv_info = p.get("private_info", {}) if p else {}
feelings = priv_info.get("user_feelings", [])
if p and len(feelings) >= 5:
    ok(f"get_person: {len(feelings)} feelings in private_info")
else: fail("get_person missing private feelings", str(feelings)[:80])

# Shayari stored
shayaris = priv_info.get("shayari", [])
if len(shayaris) >= 2: ok(f"private_info has {len(shayaris)} shayaris stored")
else: fail("Not enough shayaris", str(shayaris)[:80])

# Hindi feelings stored
h_feels = priv_info.get("feelings_in_hindi", [])
if len(h_feels) >= 3: ok(f"Hindi feelings: {len(h_feels)} stored")
else: fail("Hindi feelings missing", str(h_feels)[:80])

# Marathi feelings stored
m_feels = priv_info.get("feelings_in_marathi", [])
if len(m_feels) >= 2: ok(f"Marathi feelings: {len(m_feels)} stored")
else: fail("Marathi feelings missing", str(m_feels)[:80])

# format_prm_for_prompt contains all sections
prm = format_prm_for_prompt()
for check in ["PRIVATE MODE ACTIVE", "Divya", "collegemate", "love her", "shayari", "hackathon"]:
    if check.lower() in prm.lower(): ok(f"Private PRM block: '{check}'")
    else: fail(f"Private PRM block missing '{check}'", prm[:200])

# search_prm shows full private data
r = search_prm("divya")
for check in ["collegemate", "love her", "whole life", "shayari"]:
    if check.lower() in r.lower(): ok(f"search_prm private: '{check}' present")
    else: fail(f"search_prm private: '{check}' missing", r[:200])

# show_profile has both tiers
r = show_profile("divya")
if "Public" in r and "Private" in r: ok("show_profile has both Public and Private sections")
else: fail("show_profile missing sections", r[:100])

# prompt block has both
prompt_block_priv = format_memory_for_prompt(memory)
if "PRIVATE MODE ACTIVE" in prompt_block_priv: ok("Full prompt: private PRM block present")
else: fail("Private PRM missing from prompt")
if "collegemate" in prompt_block_priv.lower(): ok("Full prompt: public PRM still present")
else: fail("Public PRM missing from prompt when private mode on")

# ═══════════════════════════════════════════════
print("\n══ 4. SECURITY ══")
# ═══════════════════════════════════════════════

# PRM file contains no password
prm_raw = open("memory/personal_relationships.json", encoding="utf-8").read()
for pw in ["12 11 7", "barah gyarah", "bara akra", "twelve eleven"]:
    if pw not in prm_raw: ok(f"PRM file: no password '{pw}'")
    else: fail(f"Password '{pw}' found in PRM file!")

# Disable → private locked immediately
set_private_mode_active(False)
priv_after = get_person("divya")
if priv_after is None: ok("get_person None after lock")
else: fail("Private data accessible after lock!")

prm_after = format_prm_for_prompt()
if prm_after == "": ok("format_prm_for_prompt empty after lock")
else: fail("Private PRM still accessible after lock!")

# Public still accessible after lock
pub_after = get_public_info("divya")
if pub_after and "collegemate" in str(pub_after).lower():
    ok("get_public_info still works after lock (public data always accessible)")
else: fail("get_public_info broken after lock", str(pub_after)[:80])

# ═══════════════════════════════════════════════
print("\n══ 5. PROMPT.TXT SECTION ══")
# ═══════════════════════════════════════════════
prompt_txt = open("core/prompt.txt", encoding="utf-8").read()
for check in ["TIER 1", "TIER 2", "STEP A", "STEP B", "shayari", "collegemate", "exam partner"]:
    if check in prompt_txt: ok(f"prompt.txt: '{check}' present")
    else: fail(f"prompt.txt: '{check}' missing")

# ═══════════════════════════════════════════════
print(f"\n══ RESULTS: {passed} passed / {failed} failed ══")
if failed == 0:
    print("✅  ALL TESTS PASSED.")
else:
    print(f"❌  {failed} FAILURES.")
    sys.exit(1)
