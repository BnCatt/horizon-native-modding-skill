# Hook points and helpers

Stable surface: `crates/horizon-client/src/game/native_hooks.rs` (hook fns `native_*` that the game
calls) plus helper fns on `Game` (`native_setting`, `native_text`…) and a few in other files
(`game/native_net.rs`…). The catalog `native-hooks.json` (repo root) maps hook names to targets;
inject with `hook = "<name>"`, `hook_version = 1`. Hook points are only ever added; each addition
raises `NATIVE_HOOKS_API`.

## Check what a Nightly offers

```bash
git show <sha>:crates/horizon-client/src/game/native_hooks.rs | grep "const NATIVE_HOOKS_API"
git show <sha>:crates/horizon-client/src/game/native_hooks.rs | grep -n "fn native_client_packet"
python - <<'PY'   # list catalog hooks/helpers
import json; d=json.load(open('native-hooks.json'))
print([h['name'] for h in d['hooks']][:50]); print([h['name'] for h in d['helpers']][:50])
PY
```

Each hook's doc comment states its API level ("API 408") and side (client/server/window).

## Client-side hooks that cover most mods

| Hook (name) | Signature (abridged) | Notes |
| --- | --- | --- |
| `tick` | `native_tick(&mut self)` | every Game, incl. single-player's server thread: check `native_window()` |
| `frame` | `native_frame(&mut self, elapsed)` | every frame, title screen included; good for lazy setting loads |
| `client_packet` (API 408) | `native_client_packet(&mut self, packet: &ClientboundPlayPacket)` | every play packet incl. custom payloads; read-only |
| `key` | `native_key(&mut self, key: &str, pressed: bool)` | compare with `native_mod_key(id, name, default)` |
| `hud` | `native_hud(&mut self, batch, corners)` | in-world HUD |
| `screen_render_post` | `(&self, batch, screen: &NativeScreenView)` | all screens incl. title ones: `screen.id` = `title`, `multiplayer`, `direct_connect`, `inventory`, … (stable ids); `screen.mouse` = GUI coords |
| `screen_mouse_button_pressed_pre` | `(&self, screen, button, modifiers, canceled: &mut bool)` | set `*canceled = true` to swallow the click |
| `screen_mouse_button_released_pre` (API 80) | `(&self, screen, button, modifiers, canceled)` | end of a drag: store slider values here |
| `screen_mouse_dragged_pre` (API 123) | `(&self, screen, button, delta: [f32; 2], modifiers, canceled)` | sliders; `screen.mouse` is the pointer |
| `screen_key_pressed_pre`, `screen_char_typed_pre`, `screen_mouse_scrolled_pre` | | text fields in mod screens |
| `mods` | `(&mut self, mods: &mut Vec<NativeMod>)` | the mod's row in Options > Mods (`NativeMod {id,title,description,keys}`) |
| `settings`, `settings_click` | buttons on the mod's settings page | |
| `command`, `commands` | client commands | |

Helpers: `native_on(id)` (Options > Mods switch), `native_setting(id,key)` /
`native_set_setting(id,key,value)` (files in `horizon-mods/.horizon-mod-data/<id>/`),
`native_data_dir(id)` (that folder: ship files such as DLLs there), `native_player()`
(x,y,z,yaw…), `native_playing()`, `native_chat(text)`, `native_text(batch,text,[x,y],rgb,shadow)`,
`native_fill(batch,[x,y,w,h],argb)`, `native_text_width(text)`, `native_cursor()`,
`native_sprite(batch,name,src,dst) -> bool` / `native_sprite_size(name)` (API 19, GUI atlas: see
gui-sprites.md), `native_corner_shown(Corner)` + `corners.place(Corner, w, h) -> (x, y)` (stack HUD
blocks with other mods'),
`native_mod_screen()/…_open/…_close`, `native_window()`.

Networking (`game/native_net.rs`):
- `native_send_packet(ServerboundPlayPacket) -> Result` (API 409): any raw play packet to any server,
  vanilla/Paper included — use this for plugin channels such as `voicechat:*`.
- `native_net_send_to_server` / `native_net_from_server` are Horizon's own mod-net protocol: they
  fail on vanilla/Paper servers. Not for talking to Bukkit plugins.

## What a client hook can't give you (yet)

- The address the player joined, the other players' UUIDs and positions, the camera: the
  `EntityRef` helpers (`native_entity_position`…) return `None` on a client (server-side only).
  Reading them means an internal `[[module]]` in `game/remote.rs` (`Remote.session.address`,
  private `level_players: HashMap<i32,u128>`, `game.mobs` with `m.position`) — keep it to one file.
  Tracking positions yourself from packets is fragile in 26.3 (`VecDelta`/`PositionPath` deltas).
- Anything in the connection path (protocol version choice) — internal, pinned.
