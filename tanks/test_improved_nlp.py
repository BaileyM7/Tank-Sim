"""Test script demonstrating improved NLP robustness with synonym support.

Run this to see which command variations now work with the enhanced parser.
"""
from tanks.command_system import parse_command


def test_command(text: str, expected: str = ""):
    """Parse a command and show the result."""
    parsed = parse_command(text)
    if not parsed:
        status = "❌ NO MATCH"
        result = ""
    else:
        status = "✅ PARSED"
        parts = []
        for p in parsed:
            params_str = ", ".join(f"{k}={v}" for k, v in p.params.items())
            parts.append(f"{p.type.name}({params_str})" if params_str else f"{p.type.name}")
        result = " + ".join(parts)

    print(f"  {status}: {result}")
    if expected:
        print(f"           {expected}")
    return parsed


print("=" * 80)
print("IMPROVED NLP PARSER - SYNONYM SUPPORT DEMONSTRATION")
print("=" * 80)

print("\n" + "-" * 80)
print("1. MOVE COMMAND SYNONYMS (New!)")
print("─" * 80)

print("\n✅ Now works with multiple verbs:")
test_command("move to I6", "Original")
test_command("go to I6", "NEW: 'go' synonym")
test_command("travel to I6", "NEW: 'travel' synonym")
test_command("navigate to I6", "NEW: 'navigate' synonym")
test_command("drive to I6", "NEW: 'drive' synonym")
test_command("head to I6", "NEW: 'head' synonym")
test_command("proceed to I6", "NEW: 'proceed' synonym")
test_command("advance to I6", "NEW: 'advance' synonym")
test_command("retreat to A1", "NEW: 'retreat' synonym")

print("\n✅ Now works with different prepositions:")
test_command("move to I6", "Original 'to'")
test_command("move towards I6", "NEW: 'towards' preposition")
test_command("navigate toward I6", "NEW: 'toward' preposition")
test_command("go at I6", "NEW: 'at' preposition")

print("\n✅ Now works with 'cell' prefix:")
test_command("move to I6", "Original")
test_command("move to cell I6", "NEW: optional 'cell' prefix")
test_command("go to cell I6", "NEW: combines synonym + prefix")


print("\n" + "-" * 80)
print("2. PATROL COMMAND SYNONYMS (New!)")
print("─" * 80)

print("\n✅ Now works with multiple verbs:")
test_command("patrol between B2 and B9", "Original")
test_command("circle between B2 and B9", "NEW: 'circle' synonym")
test_command("loop between B2 and B9", "NEW: 'loop' synonym")
test_command("alternate between B2 and B9", "NEW: 'alternate' synonym")
test_command("go back and forth between B2 and B9", "NEW: natural phrasing")

print("\n✅ Now works with from/to syntax:")
test_command("patrol between B2 and B9", "Original 'between...and'")
test_command("patrol from B2 to B9", "NEW: 'from...to' syntax")
test_command("loop from B2 to B9", "NEW: combines synonym + from/to")


print("\n" + "-" * 80)
print("3. GUARD COMMAND SYNONYMS (New!)")
print("─" * 80)

print("\n✅ Now works with multiple verbs:")
test_command("guard E5", "Original")
test_command("defend E5", "NEW: 'defend' synonym")
test_command("hold E5", "NEW: 'hold' synonym")
test_command("protect E5", "NEW: 'protect' synonym")
test_command("secure E5", "NEW: 'secure' synonym")
test_command("camp E5", "NEW: 'camp' synonym (gamer lingo)")

print("\n✅ Now works with flexible phrasing:")
test_command("guard position E5", "Original")
test_command("defend position E5", "NEW: synonym + position")
test_command("hold area E5", "NEW: 'area' instead of 'position'")
test_command("secure spot E5", "NEW: 'spot' instead of 'position'")
test_command("protect point E5", "NEW: 'point' instead of 'position'")
test_command("guard at E5", "NEW: with 'at' preposition")
test_command("defend the position at E5", "NEW: 'the' + preposition")


print("\n" + "-" * 80)
print("4. FACE/TURN COMMAND SYNONYMS (New!)")
print("─" * 80)

print("\n✅ Now works with multiple verbs:")
test_command("face north", "Original")
test_command("turn north", "NEW: 'turn' synonym")
test_command("rotate north", "NEW: 'rotate' synonym")
test_command("look north", "NEW: 'look' synonym")
test_command("point north", "NEW: 'point' synonym")
test_command("aim north", "NEW: 'aim' synonym")

print("\n✅ Now works with full cardinal words:")
test_command("face ne", "Original abbreviation")
test_command("face northeast", "NEW: full word 'northeast'")
test_command("turn northwest", "NEW: synonym + full word")
test_command("look southeast", "NEW: synonym + full word")
test_command("face southwest", "NEW: full word 'southwest'")


print("\n" + "-" * 80)
print("5. SHOOT COMMAND SYNONYMS (New!)")
print("─" * 80)

print("\n✅ Now works with multiple verbs:")
test_command("shoot", "Original")
test_command("fire", "NEW: 'fire' synonym")
test_command("attack", "NEW: 'attack' synonym")
test_command("engage", "NEW: 'engage' synonym")

print("\n✅ Shoot-on-sight with more targets:")
test_command("shoot at anything in sight", "Original")
test_command("fire at enemies in sight", "NEW: 'fire' + 'enemies'")
test_command("attack targets in sight", "NEW: 'attack' + 'targets'")
test_command("engage hostiles in sight", "NEW: 'engage' + 'hostiles'")
test_command("fire at contacts in view", "NEW: 'contacts' + 'view'")
test_command("shoot opponents in range", "NEW: 'opponents' + 'range'")
test_command("attack anyone on sight", "NEW: 'anyone' + 'on sight'")

print("\n✅ More flexible phrasing for auto-shoot:")
test_command("shoot at anything in sight", "Original: 'in sight'")
test_command("shoot enemies in view", "NEW: 'in view'")
test_command("fire at targets within range", "NEW: 'within range'")
test_command("attack on contact", "NEW: 'on contact'")
test_command("engage hostiles on sight", "NEW: 'on sight'")


print("\n" + "-" * 80)
print("6. COMPLEX COMPOUND COMMANDS (Enhanced!)")
print("─" * 80)

print("\n✅ Synonym combinations in compound commands:")
test_command("patrol between B2 and B9 and shoot at anything in sight")
print("  Original compound command")

test_command("loop from B2 to B9 and fire at enemies in view")
print("  NEW: All synonyms in compound")

test_command("go to I6 and engage hostiles on sight")
print("  NEW: 'go' + 'engage' synonyms")

test_command("defend position E5 and attack targets in range")
print("  NEW: 'defend' + 'attack' synonyms")

test_command("circle between C3 and C9 and fire at contacts in view")
print("  NEW: Natural military-style phrasing")

test_command("advance to cell R12 and shoot anyone in sight")
print("  NEW: 'advance' + 'cell' prefix + 'anyone'")


print("\n" + "-" * 80)
print("7. VALIDATION - OUT OF BOUNDS DETECTION (New!)")
print("─" * 80)

print("\n⚠️ Invalid cells are now caught and filtered:")
test_command("move to Z99", "Out of bounds (max is R12)")
test_command("go to S1", "Column S doesn't exist (max R)")
test_command("patrol between B2 and T5", "T5 out of bounds")
test_command("guard position A13", "Row 13 doesn't exist (max 12)")
test_command("move to I0", "Row 0 doesn't exist (min 1)")

print("\n✅ Valid boundary cells work:")
test_command("move to A1", "Top-left corner (valid)")
test_command("move to R12", "Bottom-right corner (valid)")
test_command("move to R1", "Top-right corner (valid)")
test_command("move to A12", "Bottom-left corner (valid)")


print("\n" + "-" * 80)
print("8. STILL DOESN'T WORK (Limitations)")
print("─" * 80)

print("\n❌ These still require exact phrasing patterns:")
test_command("can you move to I6?", "Polite questions not supported")
test_command("please go to I6", "'please' prefix not supported")
test_command("I want you to patrol B2 to B9", "Conversational not supported")
test_command("moveto I6", "Missing space (words must be separated)")
test_command("moove to I6", "Typos/misspellings not supported")
test_command("patroll between B2 and B9", "Typos not supported")


print("\n" + "=" * 80)
print("SUMMARY OF IMPROVEMENTS")
print("=" * 80)
print("""
✅ NEWLY SUPPORTED:
  - Move synonyms: go, travel, navigate, drive, head, proceed, advance, retreat
  - Patrol synonyms: circle, loop, alternate, "go back and forth"
  - Guard synonyms: defend, hold, protect, secure, camp
  - Face synonyms: turn, rotate, look, point, aim
  - Shoot synonyms: fire, attack, engage
  - Preposition variations: to/towards/toward/at
  - Patrol syntax: "between X and Y" OR "from X to Y"
  - Full cardinal directions: northeast, northwest, southeast, southwest
  - Optional "cell" prefix: "move to cell I6"
  - Target variations: enemies, targets, hostiles, contacts, opponents, anyone
  - View variations: in sight, in view, in range, on sight, on contact, within range
  - Cell coordinate validation (A-R, 1-12) with warnings

❌ STILL NOT SUPPORTED (would need LLM):
  - Typos and misspellings
  - Polite/conversational phrasing ("can you...", "please...")
  - Abstract/high-level commands ("be aggressive", "flank")
  - Context-dependent commands ("go there", "attack him")
  - Words merged without spaces ("moveto", "guardE5")

📊 BEFORE vs AFTER:
  - Before: ~6 command patterns, exact phrasing required
  - After: ~60+ natural variations supported with synonyms
  - Synonym coverage: 5-8 variations per command type
  - Validation: Automatic bounds checking for cell coordinates
""")

print("\n" + "=" * 80)
