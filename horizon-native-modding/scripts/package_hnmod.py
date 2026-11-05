#!/usr/bin/env python3
"""Package a horizon-mixins bundle as a source-only `.hnmod` (what the launcher installs and builds).

    python package_hnmod.py <bundle dir> [--compat compatibility.json] [--out DIR] [--install]

<bundle dir> holds horizon-mixin.toml (its [mod] id/version and [compatibility] horizon_revision).
compatibility.json (default: two levels up from the bundle, i.e. the repo root) gives game,
horizon_revision, horizon_mixins_revision and optionally "hooks". The archive holds
horizon-native.json + mixins/<id>/**.rs|.toml with fixed dates/modes (same sources → same bytes).
--install copies it to the launcher's native mods folder as <id>.hnmod.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tomllib
import zipfile
from pathlib import Path


def installed_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "horizon" / "horizon-native-mods"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/horizon/horizon-native-mods"
    return Path.home() / ".local/share/horizon/horizon-native-mods"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("--compat")
    ap.add_argument("--out")
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    bundle = Path(a.bundle).resolve()
    root = bundle.parents[1]
    compat = json.loads(Path(a.compat or root / "compatibility.json").read_text(encoding="utf-8"))
    mixin = tomllib.loads((bundle / "horizon-mixin.toml").read_text(encoding="utf-8"))
    mod = mixin["mod"]
    if mixin.get("compatibility", {}).get("horizon_revision") != compat["horizon_revision"]:
        sys.exit("horizon-mixin.toml and compatibility.json pin different Horizon revisions")
    for lock in bundle.rglob("Cargo.lock"):
        sys.exit(f"remove {lock}: a mod crate builds on Horizon's Cargo.lock")
    manifest = dict(schema=1, id=mod["id"], version=mod["version"], game=compat["game"],
                    horizon=compat["horizon_revision"], mixins=compat["horizon_mixins_revision"])
    if "hooks" in compat:
        manifest["hooks"] = compat["hooks"]
    files = {"horizon-native.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()}
    for path in sorted(bundle.rglob("*")):
        if path.is_file() and path.suffix in (".rs", ".toml"):
            files[f"mixins/{bundle.name}/{path.relative_to(bundle).as_posix()}"] = path.read_bytes()
    out_dir = Path(a.out) if a.out else root / "target"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{mod['id']}-{mod['version']}.hnmod"
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    result = dict(file=str(out), files=len(files), size=out.stat().st_size,
                  sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    if a.install:
        dest = installed_dir() / f"{mod['id']}.hnmod"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, dest)
        result["installed"] = str(dest)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
