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
widget sprites with stand-ins (gui-sprites.md), own 16×16 icons, a status icon bottom left
(microphone / muted / off / disconnected / whispering, in that priority), the group's members top
left with a speaker by whoever talks, and a speaker over talking players' heads.

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
  icon and the over-head speakers both check it.
- A "Chat Messages" setting gates every line the mod puts in the chat (toggle feedback, group
  joins, errors): filter where the lines are taken, not at each call site.
- Renaming a mod's id moves its data folder and its `horizon-mods.txt` lines: copy
  `.horizon-mod-data/<old>/` to the new id and rewrite `mod.<old>`/`key.<old>.*`. Also rename the
  crate, the `[[module]]` names and helper fn prefixes, or the old and new mod can't be built
  together.

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
