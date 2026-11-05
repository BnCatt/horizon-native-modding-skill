#!/usr/bin/env python3
"""Replace text in one file inside an installed .hnmod, keeping every other entry as it was.

    python patch_hnmod.py <file.hnmod> <path inside zip> <old text> <new text> [--backup DIR]

Exits non-zero when <old text> isn't found (nothing is written then). Use for one-line fixes of
third-party mods after a Nightly moved code (see references/fixing-third-party-mods.md).
"""
import argparse
import os
import shutil
import sys
import zipfile


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("hnmod")
    ap.add_argument("entry")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--backup")
    a = ap.parse_args()
    with zipfile.ZipFile(a.hnmod) as z:
        if a.entry not in z.namelist():
            sys.exit(f"{a.entry} not in {a.hnmod}: {z.namelist()}")
        text = z.read(a.entry).decode("utf-8")
    hits = text.count(a.old)
    if not hits:
        sys.exit(f"'{a.old}' not found in {a.entry}")
    if a.backup:
        os.makedirs(a.backup, exist_ok=True)
        shutil.copy2(a.hnmod, os.path.join(a.backup, os.path.basename(a.hnmod)))
    tmp = a.hnmod + ".tmp"
    with zipfile.ZipFile(a.hnmod) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == a.entry:
                data = data.decode("utf-8").replace(a.old, a.new).encode("utf-8")
            dst.writestr(info, data)
    os.replace(tmp, a.hnmod)
    print(f"{a.entry}: {hits} replacement(s)")


if __name__ == "__main__":
    main()
