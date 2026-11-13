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
| `E_TARGET_NOT_FOUND horizon_client::game::Game<'_>::click_creative` (Nightly 2026-11-13) | the method's `impl Game` block moved out of `game.rs` into `game/creative_screen.rs` | the target id carries the file's module: `horizon_client::game::creative_screen::Game<'_>::click_creative`; `grep -rn "fn <name>" crates/` finds the new file |
| `E0004 non-exhaustive patterns: ServerVersion::V1_20_3 and V1_20_2 not covered` (2026-11-13) | upstream added enum variants (new server versions); a mod `match`es the enum exhaustively | add the arms; in new code prefer a `_ =>` arm or upstream's own tables (`ServerVersion::ALL`, its `NAME`s) so the next variant doesn't break the build |
| `E0061 … takes 6 arguments but 5` at `bundle::tooltip_layout(items, stack, x, y, w)` (2026-11-13) | gained `description_lines: usize`; the game now calls `horizon_client::item_tooltip::bundle_tooltip(…, description_lines)` | a helper that stands in for a whole body (`draw_stack_tooltip_with`) must be re-copied from the Nightly's body, not patched at the call: the same body also gained a `native_tooltip_render_pre` cancel |
| `E0609 no field options_to_game on Game` (Mod Menu 0.3.3, 2026-11-13) | the field was removed | drop its save/restore around `open_options_at` |
| a mod's own packet fix became redundant (older-servers' `sign_update` re-layout, 2026-11-13) | upstream now translates it (`adapter/translate.rs`) | remove the mod's branch: grep the Nightly for the packet before carrying a workaround forward |

A helper that copies a whole function body (cancellable HEAD that always `Break`s) compiles as long
as the names it uses exist, even when upstream changed the body: after moving a pin, diff the
upstream function between the old and the new pin (`git diff <old> <new> -- <file>`, or extract both
bodies and `diff` them) and re-copy when it changed.

General approach: open the Nightly's definition (`grep -rn "fn <name>\|struct <Name>"`), compare
with the call in the helper, change the call. Don't rewrite mods wholesale; one-line fixes are easy
for the author to adopt and for the player to verify.
