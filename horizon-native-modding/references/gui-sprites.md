# Vanilla-looking mod screens: sprites, nine-slice, sliders, icons

A mod screen drawn only with `native_fill` + `native_text` looks like a debug overlay. To match
vanilla (and Java mods such as Simple Voice Chat), draw the game's own GUI sprites. Checked on
Horizon `f319701` (API 409); all helpers below are from API 19 or older, so a `"hooks": 409` mod
can use them.

## Helpers

- `game.native_sprite(batch, name, src: [f32; 4], dst: [f32; 4]) -> bool`: part `src` (in the
  sprite's own pixels) of sprite `name`, stretched into `dst` (GUI pixels). **False when the atlas
  has no such sprite**: always have a stand-in.
- `game.native_sprite_size(name) -> Option<[f32; 2]>`: its size, or None.
- Names: vanilla's are `gui/sprites/...` keys without `minecraft:`, e.g.
  `gui/sprites/widget/button`, `..._highlighted`, `..._disabled`, `gui/sprites/widget/slider`,
  `slider_highlighted`, `slider_handle`, `slider_handle_highlighted`, `text_field`,
  `text_field_highlighted`. A content mod's GUI texture is `<ns>:gui/<path>` (from
  `assets/<ns>/textures/gui/<path>.png`).

## Nine-slice like vanilla

Horizon's fallback borders for widgets (what vanilla's `.mcmeta` files give):

| Sprite | Size | Border (l, t, r, b) |
| --- | --- | --- |
| `button`, `button_highlighted`, `button_disabled` | 200×20 | 3 |
| `slider_handle`, `slider_handle_highlighted` | 8×20 | 2, 2, 2, 3 |
| `slider`, `slider_highlighted`, `text_field*` | as the atlas says | 1 |

Draw the four corners as they are and **tile** (repeat, not stretch) the edges and the centre, as
vanilla's `GuiGraphics.blitSprite` nine-slice does. Stretching a 200 px button's centre to 300 px
smears its texture.

Vanilla's numbers worth copying:
- Button label: centred on x; `y + floor((h - 8) / 2)`; white `0xFFFFFF` when active, `0xA0A0A0`
  disabled; cut with "…" when wider than the button.
- Slider handle: `x + floor(v * (w - 8))`, 8 px wide; value under the pointer
  `((cx - (x + 4)) / (w - 8)).clamp(0, 1)`; highlighted track while hovered or dragged.
- Screen titles on a light panel: `0x404040`, no shadow. Dim the world behind an in-game screen
  with a full-screen fill (`0xC0101010`).
- Lay everything out from the GUI size each frame (`batch.width/height`), so it follows GUI scale;
  unit-test the layout at small (320×240) and wide (960×540) sizes.

## Dragging and releasing

Sliders need the pointer while the button is held:

| Target | Since | Signature |
| --- | --- | --- |
| `native_screen_mouse_dragged_pre` | API 123 | `(&self, screen, button: i32, delta: [f32; 2], modifiers: u32, canceled: &mut bool)` |
| `native_screen_mouse_button_released_pre` | API 80 | `(&self, screen, button, modifiers, canceled)` |

`screen.mouse` is the pointer in GUI pixels in both. Pattern: on press over a slider remember it and
its rect; on drag recompute the value from `screen.mouse[0]`; on release stop and **store the
setting then** (not on every drag event).

## Icons the mod draws itself

- A `.hnmod` carries only `horizon-native.json` and `mixins/<id>/**.rs|.toml` (plus `data/`,
  README/LICENSE/COPYING). **No PNGs, no `.txt`**: pixel art has to be compiled in, e.g. a generated
  `icons.rs` with each icon's rows, drawn as runs of same-colour `native_fill`s.
- Keep the source of truth in one generator (16×16 ASCII grids + palette → PNGs *and* `icons.rs`),
  deterministic (fixed zlib level, no timestamps), with a test that the committed files are current.
- The combined `.hmod` (Horizon `docs/mod-files.md`: `horizon-mod.toml` + `assets/` +
  `horizon-native.json` + `mixins/`) could carry the PNGs as `<id>:gui/icons/<name>` textures, but
  launchers at `f319701` and `main` (API 411) only read `.hnmod` from `horizon-native-mods/`
  (the folder scan keeps only `*.hnmod`). Ship both: draw the sprite, and fall back to the
  compiled-in pixels when `native_sprite` returns false. That keeps resource-pack overrides working
  where the `.hmod` loads, and nothing breaks where it doesn't.
- The content half's manifest needs `api = "0.2"`, `capabilities = ["registries"]` (without a
  capability the loader asks for `mod.wasm`), and the same `id` as `horizon-native.json`
  (`Bundle::read` refuses a mismatch).
- Make your own art. Don't copy another mod's textures, even for a look-alike.

## Over players' heads

Project a world point with the camera from the internal module (`labels::project`-style:
yaw/pitch/fov → GUI pixels). For an icon above a name tag, size it from the projection itself: the
GUI distance between `point` and `point + 0.35 blocks up`, clamped to 4..16 px and rounded, so it
shrinks with distance like the name tag. Put it ~1.1 blocks above the eyes (0.3 more when your
own label sits there) and draw far ones first.
