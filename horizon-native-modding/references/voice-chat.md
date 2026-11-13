# Simple Voice Chat client for Horizon

Goal: talk with Java players on servers running the Simple Voice Chat (SVC) plugin/mod. Starting
point: Nirokx/horizon-voice-chat (MIT, written from scratch in Rust: protocol, AES-128-GCM,
Opus via libloading, cpal audio, 3D mix, groups, menu on V, push-to-talk on Caps Lock). Its 1.0.0 is
pinned to an old Nightly and reads `remote::handle_packet` / `tick_remote` / `remote_entity_position`
(gone later) — port it to hook points:

| Need | Hook point / helper |
| --- | --- |
| server's `voicechat:*` payloads | `client_packet` (API 408): match `play::Clientbound::CustomPayload(p)` |
| send payloads to a Bukkit server | `native_send_packet(play::Serverbound::CustomPayload(configuration::CustomPayload{channel,data}))` (API 409) |
| per-tick work | `tick` + `if !game.native_window() { return }` |
| listener position | `native_player()` |
| joined address, other players, camera | one internal `[[module]]` in `game/remote.rs` (see hook-points.md) |
| menu, keys, HUD, settings | `screen_*`, `key`, `hud`, `settings`, `mods` hooks |
| sliders | `native_screen_mouse_dragged_pre` (API 123) + `..._button_released_pre` (gui-sprites.md) |

Declare `"hooks": 409` → builds on any later Horizon (the module is the only fragile part).

## Opus on Windows

- No Opus crate in Horizon's lock and no build scripts → load libopus at run time. Windows has none:
  ship `opus.dll` and load it from the mod's data folder first
  (`game.native_data_dir(id)` → `horizon-mods/.horizon-mod-data/<id>/opus.dll`), then system names.
- Build it reproducibly from the official tarball (verify `SHA256SUMS.txt` at
  downloads.xiph.org/releases/opus/) with the launcher's MinGW: `scripts/build_opus.py` (plain C,
  float, `-DOPUS_BUILD -DDLL_EXPORT -DUSE_ALLOCA`, `-static-libgcc`). Result depends only on
  KERNEL32/msvcrt; ship libopus' COPYING (BSD-3) next to it.
- Smoke test via ctypes: create encoder (48000, mono, VOIP 2048) / decoder, encode a 440 Hz frame of
  960 samples, decode, compare RMS.

## Logging and test tone

- Log with `target: "horizon_voicechat"` (Horizon only keeps `horizon*` targets).
- A `HORIZON_VOICECHAT_TEST_TONE=1` switch that feeds a 440 Hz sine instead of the microphone and
  forces transmit lets you test without a mic: client A sends, client B's log counts
  "sound packets heard"; the SVC server log says "successfully connected to voice chat" per player.

## Server side

SVC Bukkit/Paper plugin from Modrinth (`api.modrinth.com/v2/project/simple-voice-chat/version?
loaders=["bukkit","paper"]&game_versions=["<ver>"]`, check the sha512), UDP 24454 open. With
Horizon joining a 1.21.11 server the adapter must be on (older-servers.md); payload channels pass
through unchanged.

## Looking like the Java mod (1.2.0)

BnCatt/horizon-voice-chat 1.2.0 redid the menu as SVC's screens: a stack (main → settings / groups /
create group / adjust volumes / device lists; Escape pops one, the open key closes all), vanilla
widget sprites with stand-ins (gui-sprites.md), own 16×16 icons, a status icon bottom left, the
group's members top left, and a speaker over talking players' heads. Simple Chat Rust 1.1.0 moved
all of that to SVC's exact numbers (see "Matching SVC's layout" below).

- Keep every screen a pure function `layout(screen, state, view, gui size, mouse, text width) ->
  (draws, widgets)`; clicks hit-test the widgets drawn last. Then each screen is unit-testable
  without the game (symmetry, everything on screen at 320×240, long names cut, scrolling).
- Per-player volume: 0–400 % like SVC, stored as `volume.<hyphenated uuid>` with
  `native_set_setting`, loaded when the player's state first arrives. Store on button release.
- Device choice: list names with cpal (`input_devices()` / `output_devices()`), keep the chosen
  *name* (None = system default), fall back to the default with a log line when it's gone, and
  restart the audio streams on change.
- "Talking" = a voice packet from that player within the last ~300 ms (and, for yourself, the mic
  thread's transmitting flag).

## Icons, hide key, chat lines (Simple Chat Rust 1.0.0)

- Simple Voice Chat is **"Copyright (c) Max Henkel - All Rights Reserved"**: its textures may not be
  shipped in a published mod. Draw your own, and let players drop PNGs into
  `.horizon-mod-data/<id>/icons/<name>.png`, decoded at run time with the `png` crate (0.18, in
  Horizon's Cargo.lock) and drawn as fills (a player's own copy, never redistributed).
- A hide-icons key (SVC's default is H) just flips the stored `hide_icons` setting; the HUD status
  icon and the name-tag icons both check it.
- A "Chat Messages" setting gates every line the mod puts in the chat (toggle feedback, group
  joins, errors): filter where the lines are taken, not at each call site.
- Renaming a mod's id moves its data folder and its `horizon-mods.txt` lines: copy
  `.horizon-mod-data/<old>/` to the new id and rewrite `mod.<old>`/`key.<old>.*`. Also rename the
  crate, the `[[module]]` names and helper fn prefixes, or the old and new mod can't be built
  together. Grep the tools too: a generator writing `mixins/<old>/…/icons.rs` fails only when run
  (and its "committed files are current" test with it).

## Noise suppression (rnnoise)

SVC's "denoiser" is rnnoise. No crate for it in Horizon's lock (`nnnoiseless` is absent), so load
it like libopus:
- One `dylib` helper: try `native_data_dir(id)/<name>` first, then system names
  (`librnnoise.so.0`, `librnnoise.0.dylib`, Homebrew paths, `rnnoise.dll`); keep every error for the
  message. Share it between opus and rnnoise.
- API: `rnnoise_create(NULL)` (built-in model), `rnnoise_process_frame(st, out, in) -> f32` on
  **480** floats at 48 kHz, `rnnoise_destroy`. Check `rnnoise_get_frame_size() == 480`. Samples are
  16-bit *scaled* floats: multiply by 32768 in, divide out. An Opus frame (960) is two rnnoise frames.
- Make the denoiser lazily on the mic thread; when the DLL is missing, grey the setting out ("N/A",
  tooltip with why) and pass audio through unchanged.
- Windows DLL: `scripts/build_rnnoise.py` from the **release tarball** (the git tree has no model;
  `rnnoise-0.2.tar.gz` from github.com/xiph/rnnoise/releases carries `src/rnnoise_data.c`, ~1.4 MB
  DLL). No upstream checksum is published for it: the script pins the SHA-256 of v0.2's asset. Pass
  `-DWIN32 -DRNNOISE_BUILD -DDLL_EXPORT` or nothing is exported. BSD-3: ship `COPYING.rnnoise`.
- Test: a second of xorshift hiss should drop ≥ 6 dB (measured −74 dB) while a 440 Hz tone with
  harmonics under the same hiss keeps > −10 dB (measured −0.2 dB). Point tests at the built DLLs
  with an env var (`VOICECHAT_TEST_OPUS_DIR`) and set it before the first load in *every* test, or
  a parallel test caches "not found" first.

## Matching SVC's layout (Simple Chat Rust 1.1.0)

Players compare against the Java mod side by side; "close" reads as wrong. Take the numbers from
SVC's source (branch for the MC version, `gui/*Screen.java`, `RenderEvents`, `GroupChatManager`)
and pin each one in a layout test. What 1.1.0 uses (GUI pixels, panel-relative unless noted):
- **HUD status icon**: `[16, h - 32, 16, 16]` (`hud_icon_pos_x` 16, `_y` -16). Priority:
  disconnected → off → muted → whispering → talking; nothing when idle.
- **Name-tag icon** (other players only): gui-sprites.md "Next to a player's name tag". Priority:
  whispering → talking → disconnected → in a group that isn't yours (group icon) → voice chat off →
  muted; players without a voice state get none.
- **Group HUD**: from (4, 4), one 20 px cell per member 22 px apart downwards, face 16 px at +2,
  a talk outline around the cell, speaker-off small on the face.
- **Main** 195×76 centred: title y 7 (`0x404040`, no shadow); text buttons Settings `[6,21,75,20]`,
  Group `[114,21,75,20]`; 20×20 icon buttons at y 50: mute x 6, disable x 28, adjust volumes x 50,
  hide icons x 169.
- **Settings** 248×219: rows `x 10, w 228, y 20 + 21·i`: volume, amplification, denoiser, (mic test
  20×20 | activation type at x 31 w 207), PTT key (or VAD), threshold, audio type, (Select Microphone
  `w 113` | Select Speaker at `x 125`), Back (only outside a world: a free row for an extra toggle).
- **List screens** (join group, group, devices): 236 wide, `left = (w - 236) / 2 + 2`, `top = 32`,
  header 16, units of 18, footer 32: `units = max(3, (h - 16 - 32 - 64) / 18)`. Entries are 216×32
  in 36 px cells centred on the *screen* (not the panel), from list top + 4; fills `0xFF4A4A4A`,
  hovered `0xFF5A5A5A`, chosen device `0xFF282828`; padding 4, text vertically at `h/2 - 4`, white,
  no shadow. Footer button `[left + 7, top + height - 27, 222, 20]`.
- **Join group** entry: lock 16 px at +4, name after it, member faces 12 px two rows from the right;
  click = join (a password group opens **Enter Password** 195×74: label (8,21), field `[7,30,181,14]`,
  Join Group `[7,47,181,20]`). **Create Group** 195×124: labels (8,21)/(8,47), fields
  `[7,30,181,14]`/`[7,56,181,14]`, type `[6,74,183,20]`, Create `[6,97,183,20]` (disabled until named).
- **Group** (in one): entries with a 24 px outline at +4 (face 8/10 of it), name at +32, a ≤100 px
  volume slider on the hovered member (not yourself); icon buttons at the footer y: mute 7,
  disable 30, group HUD 53, leave 209.
- **Adjust Volumes**: footer 8, `units = max(4, …)`, one tab `[left, top - 22, 236, 20]`, search
  field `[left + 28, top + 22, 196, 12]` with a 12 px magnifier at (10, 20), list from top + 32;
  entry: face 24 at +4, name at +32, 100 px slider at the right.
- Horizon gives mods no skin textures, so faces are stand-ins (a colour from the uuid + the name's
  first letter); say so to the player rather than leaving blank squares.
- The PTT key's name for the settings row: `game.native_mod_key(id, KEY_PTT, default)` (returns
  `String`) in the screen hook, handed to the engine before it lays out.
- Test trap: two `voice()` (a `MutexGuard`) calls in one expression, e.g.
  `assert_eq!((voice().a, voice().b), …)`, deadlock: the first guard lives to the end of the
  statement. The test run just hangs; bind one guard in a block.
