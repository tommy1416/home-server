#!/usr/bin/env python3
"""Move clear kids movies from /mnt/storage/Movies to /mnt/storage/Kids,
and delete duplicates from Movies that already exist (checksum-verified) in Kids."""
import hashlib
import os
import shutil
import sys

MOVIES = "/mnt/storage/Movies"
KIDS = "/mnt/storage/Kids"

# 12 clear kids/animated titles to MOVE (exact names as on disk)
TO_MOVE = [
    "A.Minecraft.Movie.2025.2160p.AMZN.WEB-DL.HDR10+.DDP5.1.H265-BEN.THE.MEN",
    "Boss.Baby.2017.FRENCH.720p.BluRay.x264-LOST",
    "Moana 2016 FRENCH BDRip XviD-EXTREME",
    "Paddington.in.Peru.2024.1080p.WEB-DL.DDP5.1.H264-AOC",
    "Sing.2016.FRENCH.720p.BluRay.x264-LOST",
    "Spider-Man.Into.the.Spider-Verse.2018.720p.BluRay.x264-NeZu",
    "The.Croods.A.New.Age.2020.720p.WEBRip.800MB.x264-GalaxyRG[TGx]",
    "The.Emoji.Movie.2017.FRENCH.BDRip.XviD-GZR.avi",
    "The Good Dinosaur 2015 1080p BluRay x264 DTS-JYK",
    "The.Super.Mario.Bros.Movie.2023.1080p.HDRip.Dual.Audio.X26",
    "The.Super.Mario.Galaxy.Movie.2026.2160p.iT.WEB-DL.DV.HDR10+.DDP5.1.Atmos.H265.MP4-BEN.THE.MEN",
    "Wish (2023) [1080p] [WEBRip] [5.1] [YTS.MX]",
]

# 3 duplicates already in Kids (identical filenames) -> verify checksum, then delete from Movies
TO_DELETE = [
    "Hoppers 2026 1080p DCP Line Audio H264-DJT.mkv",
    "The.Spongebob.Movie.Search.For.Squarepants.2025.MULTi.TRUEFRENCH.1080p.WEB-DL.H264-Slay3R.mkv",
    "Zootopia.2.2025.1080p.x265.RMTeam.mkv",
]

APPLY = "--apply" in sys.argv


def md5(path, chunk=1024 * 1024):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def is_dir(p):
    return os.path.isdir(p)


print(f"{'APPLY' if APPLY else 'DRY RUN'}")

# ---- MOVES ----
print("\n== MOVES (Movies -> Kids) ==")
move_issues = []
for name in TO_MOVE:
    src = os.path.join(MOVIES, name)
    dst = os.path.join(KIDS, name)
    if not os.path.exists(src):
        move_issues.append(f"MISSING in Movies: {name}")
        continue
    if os.path.exists(dst):
        move_issues.append(f"SKIP (already in Kids): {name}")
        continue
    kind = "dir" if is_dir(src) else "file"
    print(f"  [{'MOVE' if APPLY else 'would move'}] {kind}: {name}")
    if APPLY:
        shutil.move(src, dst)
print(f"  -> {len(TO_MOVE) - len(move_issues)} moved")
for issue in move_issues:
    print(f"  !! {issue}")

# ---- DELETES (checksum-verified) ----
print("\n== DELETES from Movies (verified against Kids copy) ==")
del_issues = []
for name in TO_DELETE:
    src = os.path.join(MOVIES, name)
    dst = os.path.join(KIDS, name)
    if not os.path.exists(src):
        del_issues.append(f"SKIP (no longer in Movies): {name}")
        continue
    if not os.path.exists(dst):
        del_issues.append(f"SKIP (no Kids copy found): {name}")
        continue
    if not os.path.isfile(src) or not os.path.isfile(dst):
        del_issues.append(f"SKIP (not a regular file): {name}")
        continue
    if APPLY:
        m_src, m_dst = md5(src), md5(dst)
    else:
        m_src = m_dst = "(skipped in dry run)"
    match = m_src == m_dst
    print(f"  [{'DELETE' if APPLY and match else ('would delete' if not APPLY else 'NOT deleting')}] {name}")
    if not APPLY:
        print(f"      (checksum verified on apply)")
    elif match:
        os.remove(src)
        print(f"      md5 match, removed from Movies")
    else:
        del_issues.append(f"CHECKSUM MISMATCH, NOT deleting: {name}")
        print(f"      !! md5 MISMATCH (Movies={m_src} vs Kids={m_dst}) - NOT deleted")
print(f"  -> {len(TO_DELETE) - len([d for d in del_issues if 'MISMATCH' in d or 'SKIP' in d or 'no longer' in d])} deleted")

print("\nDone.")
