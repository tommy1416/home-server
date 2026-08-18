#!/bin/bash
# Count FLAC files in the Music library and list any that are NOT 16-bit
# (24-bit FLAC files fail to remux/play in Jellyfin web browser)
# Usage: ./count-24bit-flac.sh [root_dir]   (default: /mnt/storage/Music)

ROOT="${1:-/mnt/storage/Music}"
total=0
non16=0

while IFS= read -r -d '' f; do
  total=$((total+1))
  b=$(ffprobe -v quiet -select_streams a:0 -show_entries stream=bits_per_raw_sample -of default=nw=1:nk=1 "$f" 2>/dev/null)
  if [ "$b" != "16" ]; then
    non16=$((non16+1))
    echo "$b :: $f"
  fi
done < <(find "$ROOT" -iname '*.flac' -print0 2>/dev/null)

echo "======================================"
echo "TOTAL_FLACS=$total  NON_16_BIT=$non16"
