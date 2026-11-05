---
name: horizon-native-modding
description: >-
  Build, fix, package and test native mods (.hnmod, horizon-mixins bundles) for Horizon, the Rust
  rewrite of Minecraft: Java Edition 26.3 (github.com/horizon-rust/horizon), and get its launcher's
  native build to succeed on Windows. Covers hook points vs internal targets, pinning to a Nightly,
  crate-id traps (horizon_client vs horizon_client_lib), helpers/modules/crates rules, repairing
  third-party mods after a Nightly moves code, the older-servers protocol adapter (joining 1.21.x
  servers, version picker, 1.21.11 EitherHolder items), a Simple Voice Chat client mod (Opus on
  Windows), and end-to-end testing with a local Paper server, RCON and horizon-ctl. Use this whenever
  someone mentions Horizon, horizon-launcher, horizon-mixins, .hnmod, horizon-native-mods, "Rust
  Minecraft" modding, native-build errors (E_TARGET_NOT_FOUND, E_CRATE, E_REVISION, os error 32),
  porting a Fabric mod to Horizon, ViaFabricPlus-like version selection, or voice chat in Horizon,
  even if they don't say "skill" or "native mod". Turkish cues: "horizon mod yap", "rust minecraft
  mod", "native mod derle", "hnmod", "launcher derleme hatası", "1.21.11 sunucuya gir".
---

# Horizon native modding

Horizon is Minecraft: Java Edition 26.3 rewritten in Rust. A **native mod** is a
[horizon-mixins](https://github.com/horizon-rust/horizon-mixins) bundle: Rust source that the
launcher splices into Horizon's own source and compiles into a new game build. There is no runtime
loader and no Java: every change is a compile-time edit of the game, so most problems are either
"the thing I target moved" or "the build environment fights me".

Read the reference that matches the task; this page is the map and the rules that bite most often.

| Task | Read |
| --- | --- |
| Write or change a mod (manifest, helpers, modules, crates) | `references/mixins-manifest.md` |
| Pick hook points, check what a Nightly offers (API level) | `references/hook-points.md` |
| Launcher build fails, Windows `os error 32`, dev loop | `references/launcher-build-windows.md` |
| Someone's mods broke after a Nightly update | `references/fixing-third-party-mods.md` |
| Join 1.21.x servers, version picker, item translation bugs | `references/older-servers.md` |
| Simple Voice Chat client / audio / Opus on Windows | `references/voice-chat.md` |
| Prove it works (Paper + RCON + horizon-ctl, bisecting) | `references/testing.md` |

## The workflow

1. **Get the exact source the player runs.** Every Nightly keeps its source as the git tag
   `nightly-source/<date>-<short>` in `horizon-rust/horizon`. The launcher's selected version is in
   `%APPDATA%\horizon-launcher\settings.json` (`"selected"`). Work against that tag, not `main`:
   targets, struct fields and the hook API level differ between Nightlies, sometimes within a day.
   `git fetch origin tag nightly-source/…` then `git worktree add --detach ../horizon-<short> <sha>`.
2. **Prefer hook points over internal targets.** A mod that only injects at `native_hooks.rs` hook
   points (named in `native-hooks.json`, used with `hook = "…"` + `hook_version`) can declare
   `"hooks": N` and builds on every later Horizon. Touching any other function, field or private
   type means **pinning** to one commit, and the player stays on that Horizon until the mod is
   updated. When you must reach inside, put every such access in one small `[[module]]` so a
   moved field breaks the build in one place.
3. **Write the bundle** (`horizon-mixin.toml` + helper `.rs` + optional `[[module]]` and `[[crate]]`).
   The rules that most often fail a plan are in `references/mixins-manifest.md`.
4. **Plan before you build.** `horizon-mixins plan --workspace <tag worktree> --mods <dir of bundles>
   --out <abs path>` checks every target in seconds. Plan with *all* the player's installed mods
   together, because they inject at the same places and an unrelated broken mod stops the whole build.
5. **Package** as a source-only `.hnmod` (`scripts/package_hnmod.py`) and drop it into
   `%APPDATA%\horizon\horizon-native-mods\`. The launcher compiles it. If the player wants to keep
   compiling to themselves, stop here; a full game build takes 8–15 minutes (dev) and much longer
   (release).
6. **Build through the launcher** when asked: `horizon-launcher native-build --trust-native-code
   --allow-version-mismatch --profile dev|performance|release`. `--trust-native-code` is the
   player's consent; pass it only when the player has said to build. Fix failures with
   `references/launcher-build-windows.md`.
7. **Test for real** (`references/testing.md`): plan/compile passing is not "works". Drive the game
   with horizon-ctl, check the log, take a screenshot.

## Rules that bite

- **Crate ids in targets are package names.** `net`, `lan`, `title` and most client code live in the
  `horizon-client-lib` package, whose library is *named* `horizon_client`. In a mixin `target`,
  write `horizon_client_lib::net::older_server`; in helper code inside that crate, `crate::net::…`;
  from the game crate's helpers, `horizon_client::net::…`. Code moves between `horizon-client` and
  `horizon-client-lib` between Nightlies, which surfaces as `E_TARGET_NOT_FOUND`.
- **Support modules (`[[module]]`) may not start with `//!`** (inner doc = file attribute →
  `E_MODULE`). Use `//`. A module is added as a child of the target file's module, so it can read
  that module's private fields: this is how a mod reaches internals without changing visibility.
- **Mod crates (`[[crate]]`) depend only on crates already in Horizon's `Cargo.lock`**, have no
  `build.rs`, no `Cargo.lock` of their own (`E_CRATE` if one is lying around from a local
  `cargo test`; delete it) and can't depend on Horizon's path crates. A C library (libopus) must be
  loaded at run time with `libloading`, and its DLL shipped beside the mod (see voice-chat).
- **`horizon-mixins` refuses a pin mismatch** (`E_REVISION`). For local plans/builds against another
  commit, copy the bundle and rewrite `[compatibility] horizon_revision`, as the launcher does in
  its own copy.
- **Horizon's logger drops other crates' `info!`.** Only targets starting with `horizon` reach
  `logs/latest.log`: `log::info!(target: "horizon_mymod", …)`.
- **Cancellable HEAD helpers return `ControlFlow<R>`** where `R` is the target's return type; a
  helper is compiled as a local fn inside the target, so it sees that file's imports and private
  types (`Older`, `Reader`, …). `OVERWRITE` refuses bodies with closures; use a cancellable HEAD
  that always `Break`s instead.
- **Joining servers of other versions is off by default** (`HORIZON_OLDER_SERVERS=1`). A mod can
  turn it on (see `references/older-servers.md`); don't make players set environment variables.
- **Outward-facing steps** (issues, PRs, pushes to horizon-rust) come after the player has run the
  build themselves. Horizon's AGENTS.md rules: claim an issue (`🤖 Agent: /claim`), PR body starts
  with `> 🤖 Opened by <login>'s AI agent (<tool, model>), not by <login> personally.`, small PRs,
  `tools/pr_ready.py` output in the template.

## Scripts

- `scripts/package_hnmod.py <bundle dir> [--install]`: deterministic source-only `.hnmod`.
- `scripts/patch_hnmod.py <file.hnmod> <path-in-zip> <old> <new>`: one-line fix inside an installed
  `.hnmod` (back the original up first).
- `scripts/rcon.py "cmd" …` and `scripts/bisect.py <client log> <commands.txt>`: drive a Paper test
  server and find which command makes the client log `could not translate`.
- `scripts/build_opus.py <opus src> <gcc> <out>`: `opus.dll` from the official libopus source with
  the launcher's own MinGW.
- `scripts/prep_native_build.sh`: clears the launcher's stale build leftovers before a native build.
