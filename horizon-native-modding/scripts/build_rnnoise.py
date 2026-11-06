"""Build rnnoise.dll (Windows x86_64) from xiph/rnnoise's v0.2 release with MinGW gcc.

    python scripts/build_rnnoise.py <rnnoise-0.2.tar.gz> <gcc.exe> <out dir>

The tarball is the release's own asset,
https://github.com/xiph/rnnoise/releases/download/v0.2/rnnoise-0.2.tar.gz
(the git tree lacks the model, the release carries it in src/rnnoise_data.c),
and is checked against the SHA-256 below before anything is built. Plain C,
floating point, no SIMD paths (as build_opus.py builds libopus); libgcc
is linked in statically, so the DLL needs nothing but Windows itself. rnnoise
is BSD-3-Clause: its COPYING goes next to the DLL as COPYING.rnnoise.
"""
import hashlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

VERSION = "0.2"
SHA256 = "90fce4b00b9ff24c08dbfe31b82ffd43bae383d85c5535676d28b0a2b11c0d37"

# RNNOISE_SOURCES in the release's Makefile.am, without the x86 run-time
# dispatch (SSE4.1/AVX2), which needs a config.h from ./configure.
SOURCES = [
    "src/denoise.c",
    "src/rnn.c",
    "src/pitch.c",
    "src/kiss_fft.c",
    "src/celt_lpc.c",
    "src/nnet.c",
    "src/nnet_default.c",
    "src/parse_lpcnet_weights.c",
    "src/rnnoise_data.c",
    "src/rnnoise_tables.c",
]


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    tarball, gcc, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
    if digest != SHA256:
        sys.exit(f"{tarball}: SHA-256 {digest}, not rnnoise {VERSION}'s {SHA256}")
    out.mkdir(parents=True, exist_ok=True)
    unpacked = out / "src"
    shutil.rmtree(unpacked, ignore_errors=True)
    with tarfile.open(tarball) as t:
        t.extractall(unpacked, filter="data")
    src = unpacked / f"rnnoise-{VERSION}"
    obj = out / "obj"
    obj.mkdir(exist_ok=True)
    flags = [
        "-O2", "-std=gnu99", "-fvisibility=hidden",
        "-DWIN32", "-DRNNOISE_BUILD", "-DDLL_EXPORT", "-DHAVE_LRINT", "-DHAVE_LRINTF",
        f'-DPACKAGE_VERSION="{VERSION}"',
        "-I" + str(src / "include"), "-I" + str(src / "src"),
    ]
    objects = []
    for f in SOURCES:
        o = obj / (Path(f).stem + ".o")
        subprocess.run([str(gcc), *flags, "-c", str(src / f), "-o", str(o)], check=True)
        objects.append(str(o))
    dll = out / "rnnoise.dll"
    subprocess.run([str(gcc), "-shared", "-static-libgcc", "-s", "-o", str(dll), *objects], check=True)
    shutil.copy(src / "COPYING", out / "COPYING.rnnoise")
    shutil.rmtree(obj)
    shutil.rmtree(unpacked)
    print(f"{dll} ({dll.stat().st_size} bytes) from {len(SOURCES)} files, rnnoise {VERSION}")


if __name__ == "__main__":
    main()
