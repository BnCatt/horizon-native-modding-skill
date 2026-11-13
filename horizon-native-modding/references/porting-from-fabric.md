# Porting a Fabric (or Forge/NeoForge) mod 1:1

There is no converter. Fabric→Forge layers (Sinytra Connector) work because both sides run the same
JVM bytecode; Horizon has no JVM, no runtime loader and its own code layout, so a Java mod's mixin
targets have no counterpart to remap to. A port is a re-implementation: read the Java, find the
Horizon hook that does the same job, write it again in Rust, then **prove** it matches.

"1:1" means: same features, same defaults, same config field names, same strings, same pixels, same
sounds. Anything that can't match is written down, not hidden. The reference port is uku's Armor HUD
(`ukus_armor_hud`, API 411, no pin, pixel-identical on every tested config); the steps below are how
it was done.

## 0. Before writing code: licence and provenance

- Read the original's licence first. MIT/BSD/Apache: fine, keep the copyright line. The `.hnmod` root
  only accepts `horizon-native.json` + `mixins/**` (`unexpected native source: LICENSE`), so put the
  licence text in the header comment of the main module, and LICENSE + credits in the repository.
- CC BY-NC-SA and other non-listed licences: the port inherits it; the registry needs a written
  review grant (see publishing.md).
- **All-rights-reserved or no licence:** a client written from reading that source can't be listed in
  the registry, and the PR must say where a wire format was learned. Decide this before porting, not
  after (a voice chat port was refused for this).

## 1. Get the original running and inventory it

- Clone the original at the tag for MC 26.3 (the version Horizon is) and run its dev client
  (`./gradlew :fabric:runClient`, JDK 25 for 26.3). Keep it under the port's `ref/` folder, out of
  the package.
- Write a parity checklist before coding, one row per item, from the source, not from the docs:
  every config field (name, type, default, range, validation), every keybind (default key), every
  drawn element and the condition that draws it, every mixin (target + what it changes), every sound,
  texture and `en_us.json` string, every screen and its widgets. This list is the definition of done.
- Note which vanilla methods the mod calls for layout (`Mth.roundToward`, `FrameLayout`,
  `Math.round(lerp(...))`): the port must use the same formulas, so read vanilla's source for them
  too (decompiled 26.3 in `ref/vanilla-src`).

## 2. Map every Java piece to Horizon

Prefer numbered hook points (no pin). Check each against the player's Nightly (`native-hooks.json`,
`NATIVE_HOOKS_API`); names below were checked on API 411.

| Fabric / Java side | Horizon | Notes |
| --- | --- | --- |
| `ClientModInitializer.onInitializeClient` | none: lazy state in a `static` (`OnceLock`/`Mutex`), filled on first `frame`/`tick` | there is no init call |
| `ClientTickEvents.END_CLIENT_TICK`, `MinecraftClient.tick` mixin | `tick` hook | also fires on single player's server thread: gate on `native_window()` |
| `HudRenderCallback`, `HudElementRegistry`, mixins into `Gui.render*` | `gui_layer_pre` / `gui_layer_post` (API 139), or `hud` | layer ids: `minecraft:crosshair`, `hotbar`, `effects`, `boss_overlay`, `vehicle_health`, `contextual_info_bar`, `player_health`, `selected_item_name`, `sleep_overlay`, `overlay_message`, `title`, `scoreboard_sidebar`, `subtitle_overlay`, `chat`, `tab_list`. `canceled` in pre hides a layer. To *push* a vanilla element (effects, boss bars, subtitles), record `batch.vertices.len()` in pre and shift the vertices added by post |
| `DrawContext.drawText/fill/drawGuiTexture/drawItem` | `native_text`, `native_fill`, `native_sprite` / `native_gui_nine_slice`, `native_item_stack(batch, stack, at, size)` (API 313, draws decorations except the count), `native_gui_tooltip` | widths with `native_text_width` |
| `KeyBindingHelper.registerKeyBinding` | `native_mod_key(id, name, default)` + `key` hook | a key released over a screen only reaches `input_key` |
| Cloth Config / YACL / ukulib / own JSON | `native_setting` / `native_set_setting` (one file per key in `horizon-mods/.horizon-mod-data/<id>/`) | **keep the Java field names as keys**: test scripts then set the same names on both sides |
| Mod Menu config entry | `mods` (row + keys) + `settings` / `settings_click` (Options > Mods page) | |
| A custom `Screen` (config screen) | `native_mod_screen_open/close` + `screen_render_post` + `screen_*_pre` input hooks (press, release, drag, scroll, key, char) + `menu_background` (blur, API 411) | `native_mod_screen_open` refuses while another screen is open: open it from a key, or on return to the game. Widgets are drawn from vanilla sprites (gui-sprites.md) |
| Vanilla sound (`playSound(SoundEvents.X)`) | `native_play_local_sound(id, at, volume, pitch, delay)` (API 83) | |
| The mod's own `.ogg` | a `[[crate]]` that embeds the file and plays it (symphonia + cpal, both in Horizon's lock) | a `.hnmod` can't ship `assets/`; you lose device choice, subtitles and 3D position: list it as a difference |
| The mod's own textures | compiled-in pixel data (gui-sprites.md) | no PNGs in a `.hnmod` |
| `ClientPlayNetworking` receive / `CustomPayload` | `client_packet` (API 408, read-only) | |
| `ClientPlayNetworking.send` | `native_send_packet(ServerboundPlayPacket)` (API 409) | works on vanilla/Paper; `native_net_*` don't |
| `ClientCommandRegistrationCallback` | `command` / `commands` | |
| `GameRenderer.getFov` mixins, zoom | `zoom` (`NativeZoom`, 1..=10) or `compute_fov` | |
| Hiding the hand | `render_hand` (cancel) | |
| Mouse wheel | `wheel` (claim it) | |
| Action bar message | `native_client_action_bar(text, animate)` | |
| `@Accessor`, `@Shadow` of private fields | one `[[module]]` in the file that owns the field (the "peek" module) | pins the mod; keep *every* internal read in this one file so a Nightly that moves a field breaks in one place |
| `@Inject(HEAD, cancellable = true)` into code with no hook | `kind = "HEAD"` with `ControlFlow<R>` (pins) | |
| `LivingEntity.baseTick` mixin before `SwingState.tick` (arm swing: `currentSwing`, `getModifiedSwingDuration`) | local player: HEAD of `horizon_client::game::hand::Game<'_>::tick_hand` (`game.swing` is `first_person::SwingState { current: Option<SwingDescription>, ticks, … }`, duration via `first_person::swing_duration`); other entities: HEAD of `horizon_client_lib::mobs::ai::tick_swing(m)` | no hook point (pins; checked on Nightly 2026-11-13, API 415). A `Mob` keeps only `ai.swinging`, `ai.swing_duration` and `extra.swing_stab`, not the whole animation. `ItemStack.getAttackAnimation` = `spear::Kinetic::of(&stack.item)` → `attack_animation()`, else `SwingAnimation::DEFAULT`; the interact animation is always `DEFAULT`. Gate the local helper on `native_window()` (`level().isClientSide()`) |
| State a helper in the game crate and one in the lib crate both need (an on/off flag read in `mobs::…`, set from a `frame` hook) | one `[[module]]` in a lib-crate file (`visibility = "pub"`) holding `static` atomics; the game crate reads it as `horizon_client::<path>::<module>` | `native_setting` / `native_on` need `Game`, which lib-crate targets don't have: copy the value into the atomic each frame |
| `@Overwrite`, `@ModifyConstant` | `OVERWRITE` / `MODIFY_CONSTANT`; if the body has a closure, a cancellable HEAD that always `Break`s with a copy of the body | |
| `I18n` / `Text.translatable` | the `en_us.json` string, verbatim | |

If a row has no hook in the player's Nightly, look for one added later (hooks are only ever added),
else use an internal target in the peek module, else list the feature as a known difference.

## 3. Shape of the port

- `core.rs` (`[[module]]` in `game.rs`): config, drawing, screens: a line-by-line translation of the
  Java, each function commented with the Java method it ports (`// ArmorHudRenderer.drawArmorHud`).
  Port the logic as it is, including odd branches; don't "clean it up".
- `peek.rs`: the only internal reads, with the exact fields listed in its header.
- One tiny helper `.rs` per hook that only calls into `core`.
- `[[crate]]` only for heavy dependencies (audio). Test it with `cargo test --offline`, then delete
  its `Cargo.lock`.
- Pure layout/maths in plain functions so `rustc --edition 2024 --test` can check them without the game.

## 4. Prove parity side by side

1. **One server for both clients**: the launcher's vanilla `26.3.jar` (26.3's default is
   `white-list=true`: `whitelist off`), offline, flat, RCON. A `scene.sh <player>` gives each player
   the same items, damage, effects and position.
2. **The Java client driven by a test harness**: a small class added only to the `ref/` copy (never
   upstream, never shipped) that polls `run/harness/cmd.txt` on the client thread: `shot NAME`,
   `scale N`, `config`, `tab N`, `set <field> <value>`, `click X Y`, `close`, then writes `done.txt`.
3. **The Horizon client driven by horizon-ctl** (testing.md), config files written into the test
   home's `.horizon-mod-data/<id>/` before launch, using the same field names.
4. **Same physical size and GUI scale** on both. With Windows DPI scaling the Horizon window size is
   logical: 683×384 at 125 % = 854×480 physical.
5. Shoot both, put them side by side, count differing pixels per region with a tolerance and write a
   diff image (red = differs). Run a matrix: default config, then each option that moves or restyles
   something, each screen tab, invalid input states.
6. Iterate until the only differences are random (bob, world) or listed limitations. Then interact
   for real (clicks, typing, Done/Reset, settings files on disk).

## 5. Traps that break pixel parity

- `Math.round(x)` is `floor(x + 0.5)`; Rust's `round()` rounds half away from zero. Same for
  positives, different for negative halves (`Math.round(-2.5) == -2`). Use `(x + 0.5).floor()` when
  the value can be negative.
- Java integer `/` truncates like Rust's, but `Mth.floorDiv`/`positiveCeilDiv` don't: port the helper
  (`roundToward = positiveCeilDiv(input, multiple) * multiple`).
- A layout value vanilla computes with `lerp` + `Math.round` (e.g. a footer Y of 6.5 → 7) is off by
  one pixel if you hard-code the truncated number.
- Where the Java crashes (e.g. a negative value it never validated), don't crash; do nothing and
  note it.
- Horizon's text is placed from `-width/2`; glyphs end with an empty column. Anchor to what is drawn,
  not to the advance width.

## 6. Ship with an honest README

List every known difference (what, why, whether a later hook could fix it), the original's licence
and credits, the hook API level or the pin, and how parity was checked. Offer what the port taught
back to this skill (SKILL.md, "Give back what you learn").
