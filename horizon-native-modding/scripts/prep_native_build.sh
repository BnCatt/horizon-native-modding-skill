#!/usr/bin/env bash
# Before `horizon-launcher native-build` on Windows (Git Bash): move the launcher's stale build
# leftovers out of the way so its cache pruning and staging don't hit os error 32. Nothing is
# deleted: everything goes to a dated backup folder next to native/.
#   bash prep_native_build.sh
set -u
N="${APPDATA}/horizon-launcher/native"
[ -d "$N" ] || { echo "no $N"; exit 1; }
if tasklist 2>/dev/null | grep -qi horizon-launcher.exe; then
  echo "close the Horizon launcher first (it holds files in native/)"; exit 1
fi
BK="${APPDATA}/horizon-launcher/native-leftovers-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BK"
cd "$N" || exit 1
for x in stage.new mixins.incoming .horizon-mixins-lock-* .stage.new.horizon-mixins-stage.lock; do
  [ -e "$x" ] && mv "$x" "$BK/" && echo "moved: $x"
done
# Keep the two most recently used patched snapshots; the build adds one and prunes past three.
if [ -d patched ]; then
  cd patched
  for d in */; do
    printf "%s %s\n" "$(stat -c %Y "${d}.last-used" 2>/dev/null || echo 0)" "${d%/}"
  done | sort -rn | tail -n +3 | while read -r _ d; do
    mv "$d" "$BK/patched-$d" && echo "moved: patched/$d"
  done
fi
if [ -d "$N/target" ] && ! [ -L "$N/target" ] && ! cmd //c "dir /AL \"$(cygpath -w "$N")\"" 2>/dev/null | grep -q "<JUNCTION>.*target"; then
  echo "note: native/target is a plain folder under %APPDATA%; if rustc fails with"
  echo "      'failed to remove temporary directory ... os error 32', junction it elsewhere"
  echo "      (see references/launcher-build-windows.md)."
fi
echo "leftovers in $BK"
