# Writing a bundle: horizon-mixin.toml, helpers, modules, crates

The authority is Horizon's `docs/native-mods.md` (3000+ lines; grep it) and the horizon-mixins
README. This file is the working subset with the traps found in practice.

## Layout

```
mymod/                         # repo root
├── compatibility.json         # game, hooks or horizon_revision, horizon_mixins_revision
├── mixins/mymod/
│   ├── horizon-mixin.toml
│   ├── *.rs                   # one helper per injection, plus module sources
│   └── engine/                # optional [[crate]] (Cargo.toml + src/)
└── tools/package.py           # → target/mymod-x.y.z.hnmod
```

`.hnmod` = zip of `horizon-native.json` + `mixins/<id>/**.rs|.toml` (source only; besides those
only `data/` and README/LICENSE/COPYING pass, so images or text data go into generated `.rs`).
Entry names need `/` (never Windows' backslash), and a `.gitattributes` with `* text=auto eol=lf`
keeps `core.autocrlf` from changing the bytes (and hashes) between machines. A combined `.hmod`
(`horizon-mod.toml` + `assets/` + the same) is described in Horizon's `docs/mod-files.md`, but the
launcher (f319701, main) only loads `.hnmod` from `horizon-native-mods/`: see gui-sprites.md.
`horizon-native.json`: `{schema:1, id, version, game:"26.3", horizon:<commit>, mixins:<horizon-mixins
commit>, hooks?:N}`. With `hooks`, `horizon` is just the commit it was tested on.

## Manifest skeleton

```toml
[mod]
id = "mymod"
version = "1.0.0"
priority = 100                 # same-site hooks run by priority desc, then mod id

[compatibility]
horizon_revision = "<full 40-char sha>"   # must equal compatibility.json's

[[crate]]                      # heavy code compiled once; helpers call crate_name::fn
id = "engine"
path = "engine"

[[module]]                     # a module added INTO an existing source file
id = "state"
file = "crates/horizon-client/src/net.rs"
name = "mymod_state"           # becomes horizon_client::net::mymod_state
source = "state.rs"
visibility = "pub"             # pub to reach it from the game crate, pub(crate) otherwise

[[injection]]                  # a stable hook point (preferred)
id = "tick"
hook = "tick"
hook_version = 1
kind = "HEAD"
helper = "tick.rs"
bindings = [ { name = "game", ty = "&mut crate::game::Game<'_>", value = "&mut *self" } ]

[[injection]]                  # an internal function (forces a pin)
id = "pick"
kind = "HEAD"
cancellable = true
target = "horizon_client_lib::net::older_server"
helper = "pick.rs"
bindings = [ { name = "address", ty = "&str", value = "address" } ]
```

Injection kinds in the README: HEAD (optionally cancellable), interior cancellation, BEFORE_CALL,
AFTER_CALL, AFTER_ASSIGN, MODIFY_EXPRESSION_VALUE, RETURN, MODIFY_ARG(S), MODIFY_CONSTANT,
MODIFY_VARIABLE, WRAP_OPERATION, OVERWRITE. HEAD + cancellable covers most needs.

## Targets

- Form: `crate::module::function`, `crate::module::Type<'_>::method`. The crate part is the
  **package** name with `_`: `horizon_client` (game crate, `crates/horizon-client` with `game.rs`),
  `horizon_client_lib` (the lib whose sources also sit under `crates/horizon-client/src/`:
  `net.rs`, `lan/`, `title.rs`, `hud`, `items` re-exports…), `horizon_protocol`, `horizon_items`,
  `horizon_client_render`, `horizon_world`…
- To tell which: `grep -n "pub mod <name>" crates/horizon-client/src/client_lib.rs` (lib) vs
  `crates/horizon-client/src/game.rs` / `main.rs` (game crate).
- Private fns are fine as targets (`horizon_protocol::item::older_layout` is private).
- A target that moved or was renamed fails `plan` with `E_TARGET_NOT_FOUND` and the exact id.

## Helpers

- One fn per file; its parameters are the bindings, in order.
- Listen hook / plain HEAD: returns `()`.
- Cancellable HEAD: returns `std::ops::ControlFlow<R>` where `R` is the target's return type
  (`Continue(())` runs the original body, `Break(v)` returns `v`). Example (target returns
  `Option<ServerVersion>`): `fn pick(address: &str) -> ControlFlow<Option<ServerVersion>>`.
- The helper is compiled as a local fn inside the target: it sees the target file's `use` imports
  and private items (types like `Older`, `Reader`, `Result` alias). `?` works if you wrap it in a
  closure returning the target's `Result` (see older-servers.md for an example).
- `self` is not `self` in a helper: bind it (`value = "&mut *self"` / `"&*self"`); no `Self` either.
- Values moved by the original body need `&param` bindings or you get move errors.
- `OVERWRITE` refuses functions whose body contains closures (`E_UNSUPPORTED_CONTROL_FLOW`): use a
  cancellable HEAD that always `Break`s with a helper holding a copy of the body.

## Modules

- `[[module]]` sources must not start with `//!` or `#![…]` (`E_MODULE: support module source cannot
  have file attributes or a shebang`). Use `//` comments.
- A module is a child of the file's module → it can read that module's private struct fields
  (e.g. a module in `game/remote.rs` can read `Remote`'s private `level_players`). Put every
  internal access of a mod in one module; everything else through hook points.
- Use statics (`AtomicU8`, `OnceLock`, `Mutex`) for state shared between hooks and threads (screen
  hooks run on the window thread; connection code on a network thread).

## Crates

- Only registry crates already in Horizon's `Cargo.lock`, by version requirement (`E_CRATE_DEPENDENCY`
  otherwise). Check: `grep -A1 '^name = "<crate>"$' Cargo.lock`. Useful ones present on 26.3 Nightlies:
  `cpal`, `libloading`, `ring`, `log`, `cc` (but you can't use it: no build scripts), `dasp_sample`.
  Not present: `opus`, `audiopus`, `nnnoiseless`, `rubato`.
- No `build.rs`, no own `Cargo.lock` (`E_CRATE: a bundle crate cannot ship a Cargo.lock`), no
  `[workspace]`, no path/git deps, no dependency on Horizon crates. Types from the game reach the
  crate only through helper code.
- Unit-test the crate alone with `cargo test --offline` (launcher's toolchain, its CARGO_HOME), then
  delete the `Cargo.lock` it creates before planning. Outside the launcher, a fresh lock resolves
  newer crate versions than Horizon's; pin them to Horizon's `Cargo.lock` first
  (`cargo update -p cpal --precise 0.16.0`, same for `libloading`, `ring`, `log`…), so the tests
  run what the game build will.
- Type-check helpers without building the game: a scratch crate that depends on the mod crate and
  declares stand-ins with the exact signatures the helpers call (`mod game { pub struct Game<'a>(…);
  impl Game<'_> { pub fn native_sprite(&self, batch: &mut HudBatch, name: &str, src: [f32; 4],
  dst: [f32; 4]) -> bool {…} … } }`, `mod horizon_client { pub mod hud { pub struct HudBatch {…} } }`),
  then `include!` the helper files and `cargo check`. Copy each signature from the target
  revision's `native_hooks.rs`. It catches closure and borrow mistakes in seconds; it is not a
  substitute for `horizon-mixins plan` and a real build.

## compatibility.json

```json
{ "game": "26.3", "hooks": 409,
  "horizon_repository": "https://github.com/horizon-rust/horizon",
  "horizon_revision": "<tested commit>",
  "horizon_mixins_repository": "https://github.com/horizon-rust/horizon-mixins",
  "horizon_mixins_revision": "<launcher's MIXINS_REV>" }
```

Omit `hooks` for a pinned mod. The launcher's horizon-mixins revision is `MIXINS_REV` in
`launcher/src/native_mods.rs`; its built CLI sits in
`%APPDATA%\horizon-launcher\native\tools\<rev12>\bin\horizon-mixins.exe`.

## Plan / apply locally

```bash
HM=$APPDATA/horizon-launcher/native/tools/<rev12>/bin/horizon-mixins.exe
"$HM" plan  --workspace <worktree> --mods <dir with one folder per bundle> --out <ABSOLUTE path, no "..">
"$HM" apply --workspace <worktree> --mods <dir> --out <FRESH dir>   # Windows: can't replace an existing stage
```

`apply` on Windows refuses an existing output (`E_ATOMIC_STAGE`). For incremental builds apply into
a fresh folder and copy only changed files into the kept stage (mtimes untouched elsewhere), then
`cargo build --locked -p horizon-client --profile fast` there.
