#!/bin/bash
# Find files/folders present in both Movies and Kids (potential duplicates)
cd /mnt/storage || exit 1

echo "=== Names present in BOTH Movies/ and Kids/ ==="
while IFS= read -r f; do
    [ -z "$f" ] && continue
    echo "$f"
    echo "  Movies: $(stat -c '%s bytes' "Movies/$f" 2>/dev/null || echo '?')"
    echo "  Kids:   $(stat -c '%s bytes' "Kids/$f" 2>/dev/null || echo '?')"
done < <(comm -12 <(ls -1 Movies/ | sort) <(ls -1 Kids/ | sort))
