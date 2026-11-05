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
