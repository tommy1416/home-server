#!/usr/bin/env python3
"""Strip leading '[ Tag ] ' prefixes from file/folder names.

Usage:
    python3 strip_torrent9_tags.py [TARGET_DIR]   # dry run (default)
    python3 strip_torrent9_tags.py [TARGET_DIR] --apply   # actually rename

TARGET_DIR defaults to /mnt/storage/Movies if omitted.
"""
import os
import re
import sys
from collections import Counter

TARGET = next((a for a in sys.argv[1:] if not a.startswith("--")), "/mnt/storage/Movies")
# Matches a leading bracketed tag like "[ Torrent9.tv ] rest of name"
PATTERN = re.compile(r"^\[ .* \] (.*)$")

APPLY = "--apply" in sys.argv

plan = []          # list of (old_path, new_path, old_name, new_name)
collisions = []    # same target from multiple sources

for name in sorted(os.listdir(TARGET)):
    m = PATTERN.match(name)
    if not m:
        continue
    newname = m.group(1).strip()
    if not newname:
        continue
    old = os.path.join(TARGET, name)
    new = os.path.join(TARGET, newname)
    plan.append((old, new, name, newname))

# Detect target collisions (two sources mapping to the same name)
targets = [new for _, new, _, _ in plan]
dup_targets = {p for p, c in Counter(targets).items() if c > 1}
for old, new, name, newname in plan:
    if new in dup_targets:
        collisions.append((name, newname))

# Detect targets that already exist on disk (and aren't the source itself)
existing_skips = []
for old, new, name, newname in plan:
    if os.path.exists(new) and os.path.abspath(old) != os.path.abspath(new):
        existing_skips.append((name, newname))

print(f"{'APPLY' if APPLY else 'DRY RUN'}: {len(plan)} item(s) have a bracketed tag prefix")

if collisions:
    print("\n!! COLLISIONS (multiple sources -> same target), SKIPPING:")
    for name, newname in collisions:
        print(f"    {name}  ->  {newname}")

if existing_skips:
    print("\n!! TARGET ALREADY EXISTS, SKIPPING:")
    for name, newname in existing_skips:
        print(f"    {name}  ->  {newname}")

skip_names = {c[0] for c in collisions} | {e[0] for e in existing_skips}

print("\nRenames:")
for old, new, name, newname in plan:
    if name in skip_names:
        continue
    marker = "RENAMED" if APPLY else "would rename"
    print(f"  [{marker}] {name}")
    print(f"        ->  {newname}")
    if APPLY:
        os.rename(old, new)

print(f"\nDone. {'Renamed' if APPLY else 'Would rename'} {len(plan) - len(skip_names)} item(s).")
