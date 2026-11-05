# Repairing mods after a Nightly moved code

Most `.hnmod`s are pinned to the Nightly they were made for. When the player updates, the launcher
builds all of them on the newest pin; anything that moved breaks the whole build. Find every break
at once, patch the installed copies minimally, keep backups, and tell the player (and ideally the
mod's author) what changed.

## Procedure

1. Back up `%APPDATA%\horizon\horizon-native-mods\` (copy the `.hnmod`s you'll touch).
2. Extract every installed mod into one folder (each zip holds `mixins/<id>/…`), rewrite every
   `horizon_revision` to the build commit, and plan them together against the Nightly's source:

   ```bash
   mkdir -p all/x && cd all/x && for f in "$APPDATA"/horizon/horizon-native-mods/*.hnmod; do unzip -qo "$f"; done
   mv mixins/* .. && cd .. && rmdir -p x/mixins 2>/dev/null; rm -rf x
   for d in */; do sed -i "s/^horizon_revision = .*/horizon_revision = \"$SHA\"/" "$d/horizon-mixin.toml"; done
   "$HM" plan --workspace <source of $SHA> --mods <abs path of all> --out <abs plan.json>
   ```

   `plan` stops at the first error: fix it in the extracted copy, re-plan, repeat until `"status": "ok"`.
3. `plan` doesn't type-check helpers. Before a full build, grep helpers for calls/struct literals of
   things that changed (look at the Nightly's signatures). Then build (dev profile) and fix
   compiler errors the same way.
4. Apply each fix to the installed `.hnmod` with `scripts/patch_hnmod.py` (rewrites one entry of the
   zip, keeps the rest byte-identical).

## Kinds of breakage seen (26.3 Nightlies, Nov 2026) and their fixes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `E_TARGET_NOT_FOUND …game::titles::Game<'_>::draw_titles` | renamed | `draw_title` (same signature) |
| `E_TARGET_NOT_FOUND horizon_client::lan::hub::Hub::stack` | `lan` moved to the lib package | `horizon_client_lib::lan::hub::Hub::stack` (helper paths `crate::lan::…` unchanged) |
| `E_TARGET_NOT_FOUND horizon_client::net::…` | `net` is in the lib package | `horizon_client_lib::net::…` |
| `E0063 missing field 'action' in initializer of title::Button` | struct gained a field | add `action: None,` to the literal |
| `E0061 this function takes 7 arguments but 6` at `Game::tooltip_box(batch, atlas, …)` | became a method taking the stack | `game.tooltip_box(batch, Some(stack), x, y, w, h)` |
| quirk field renamed (`either_holder_song_and_tag_resistance` → `either_holders_and_tag_resistance` on main) | upstream refactor | match the Nightly you build on |

General approach: open the Nightly's definition (`grep -rn "fn <name>\|struct <Name>"`), compare
with the call in the helper, change the call. Don't rewrite mods wholesale; one-line fixes are easy
for the author to adopt and for the player to verify.
