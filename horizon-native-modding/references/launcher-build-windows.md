# The launcher's native build, and making it pass on Windows

## Paths

- Launcher: `%LOCALAPPDATA%\Programs\horizon-launcher\horizon-launcher.exe`; data
  `%APPDATA%\horizon-launcher\` (`settings.json`: `selected`, `native_profile`; `versions\<tag>\`
  holds each installed game incl. `horizon-ctl.exe` and prepared resources in
  `.local\horizon-client\26.3`).
- Game data (default instance): `%APPDATA%\horizon\` — `horizon-native-mods\*.hnmod`,
  `horizon-mods\.horizon-mod-data\<id>\`, `logs\latest.log`.
- Native build workspace: `%APPDATA%\horizon-launcher\native\` — `source\<sha>` (pristine),
  `patched\<key>` (cached patched trees, last 3 kept), `stage`, `stage.new`, `mixins.incoming`,
  `target` (cargo), `tools\<rev12>\bin\horizon-mixins.exe`, `build.log` (full log of the last build).
- Rust: the launcher's own toolchain `%APPDATA%\horizon-launcher\rust\<ver>-x86_64-pc-windows-gnu`
  (`bin` + `mingw64\bin` on PATH, `CARGO_HOME=%APPDATA%\horizon-launcher\cargo`). It ships gcc but
  **no rustfmt/clippy**: download `rustfmt`/`clippy` components for the same version from
  `static.rust-lang.org/dist/channel-rust-<ver>.toml` (verify `xz_hash`) and put them on PATH first.

## Command

```bat
horizon-launcher native-build --trust-native-code --allow-version-mismatch --profile dev
```

- Profiles: `performance` (= cargo `fast`), `dev` (`fast` + `opt-level=0` for horizon-client:
  quickest rebuild), `release` (thin LTO, codegen-units=1: slowest). Settings page names: Performance
  / Development / Release build.
- `--allow-version-mismatch`: the player's mods pin different Nightlies (common). Builds on the
  newest pin. `--ignore-pins` builds everything on the selected version instead.
- `--trust-native-code` = the player's consent to run the mods' code. Use only when they asked.
- Success prints `native-<short>-<hash> built and selected for its instance`.
- Close the launcher GUI first: a running GUI holds files in `native\` → os error 32.

## os error 32 ("The process cannot access the file because it is being used by another process")

Seen three ways; fix in this order:

1. **GUI open** → close it (`Stop-Process -Name horizon-launcher`), retry.
2. **Cache pruning**: after "Reusing patched game source"/"Applying the mixins", the launcher
   deletes all but 3 `patched\*` snapshots and that delete can fail. Before building, move all but
   the newest two snapshots (by `patched\<key>\.last-used` mtime) plus `stage.new`,
   `mixins.incoming`, `.horizon-mixins-lock-*` into a backup folder (`scripts/prep_native_build.sh`).
3. **rustc can't remove `.tmpXXXX.temp-archive` in `native\target\fast\deps`** ("failed to build
   archive … failed to remove temporary directory"). The same crates fail every retry; a Windows
   Defender folder exclusion did *not* help in practice. What fixed it: put the target dir outside
   `%APPDATA%` with a junction:

   ```powershell
   $src="$env:APPDATA\horizon-launcher\native\target"; $dst="C:\path\outside\appdata\horizon-native-target"
   Move-Item $src $dst; cmd /c mklink /J "$src" "$dst"
   ```

   Reversible (remove the junction, move the folder back). Leftover empty `.tmp*.temp-archive`
   folders can be deleted once the build stops.

## Reading failures

- `build.log` ends with the horizon-mixins JSON (`code`, `message`, `mod_id`, `injection_id`,
  `target`) or the cargo errors. A failing mod is often **not yours**: the first error stops the
  build. See `fixing-third-party-mods.md`.
- "Some mods were made for other Horizon versions (a → x, b → y…)" is a hint, not the error.

## A Windows machine without the launcher

To test a mod crate and build DLLs where no launcher is installed:
- `winget install Rustlang.Rustup`, then `rustup toolchain install stable-x86_64-pc-windows-gnu
  --profile minimal` and make it the default (Horizon builds with the GNU toolchain), and
  `winget install BrechtSanders.WinLibs.POSIX.UCRT` for gcc. WinLibs lands in
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_*\mingw64\bin`; put it
  and `~/.cargo/bin` on PATH in every shell (a small `env.sh` to source).
- `git config --global core.longpaths true` before cloning Horizon (`Filename too long` otherwise).
  A shallow fetch of one revision is enough to read hook signatures (~170 MB).

## Local dev loop without the launcher

Faster for iterating on your own mod (no other mods, incremental):

1. Worktree of the Nightly tag; copy your bundle, rewrite its pin to the worktree's HEAD.
2. `horizon-mixins apply` into a fresh dir; sync changed files into a kept `stage/`.
3. `cargo build --locked -p horizon-client --profile fast` with a dedicated `CARGO_TARGET_DIR`
   outside `%APPDATA%` (first build ~10–15 min, then ~5).
4. Run it with a horizon-ctl from any installed version: `horizon-ctl launch --game <exe>
   --resources <versions\<tag>\.local\horizon-client\26.3> --offscreen` (see testing.md). The exe is
   locked while a client runs: quit clients before rebuilding.
