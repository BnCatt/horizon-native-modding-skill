# Publishing a native mod to Horizon's mod browser

The launcher's and the website's mod browser read one `index.json` built by
[horizon-rust/horizon-mods](https://github.com/horizon-rust/horizon-mods). Rules: its `MOD-POLICY.md`
and Horizon's `docs/api/mod-index.md` (read them on the Nightly you build; this is the November 2026
state). Publishing is outward-facing: do it only when the player asked, after they have the build.

## The shape that works

1. **A public GitHub repository** with the mod's source and a LICENSE the reviewers may read: MIT,
   MIT-0, BSD-2/3, 0BSD, Apache-2.0, ISC, zlib, Unlicense or CC0 (GPL/LGPL/MPL/all-rights-reserved
   need a written grant). A fork of an MIT mod keeps the original copyright line and credits it.
2. **A GitHub release** (not a draft, not a pre-release) with the `.hnmod` as an asset. Tag `v1.0.0`;
   the version, game and pins come from the file's own `horizon-native.json`. Ship run-time DLLs
   and their licence files as extra assets.
3. **Check the file** as the registry's CI does. `cargo-horizon-mod` is in Horizon's workspace:
   `cargo install --locked --path <horizon source>/crates/cargo-horizon-mod --root <dir>` (launcher's
   toolchain, target dir outside `%APPDATA%` on Windows), then
   `cargo-horizon-mod horizon-mod check <file>.hnmod`. A pinned native mod reports
   `format native-1/<horizon>/<mixins>`; native source is never run by the check: reviewers read it.
4. **A pull request** to `horizon-rust/horizon-mods` adding `mods/<id>.toml` (or use the form at
   playhorizon.dev/mods/submit). With `repo = "owner/name"`, later versions come from new releases
   automatically, no PR per version. Entry:

   ```toml
   id = "my_mod"                      # = the manifest id = the file name
   kind = "native-mod"
   repo = "Owner/my-mod"
   owners = ["Owner"]
   owner_ids = [12345678]             # gh api users/Owner --jq .id
   name = "My Mod"
   summary = "One line, at most 160 characters."
   description = """Markdown: what it does, keys, what it touches, credits, not-affiliated note."""
   authors = ["Owner"]
   license = "MIT"
   categories = ["utility"]           # see other entries: utility, social, …
   tags = ["zoom", "camera"]
   ```

   Fill the PR template's checklist truthfully. An AI agent's PR starts with
   `> 🤖 Opened by <login>'s AI agent (<tool, model>), not by <login> personally.`

## Traps

- **Only an entry's owners can add versions.** If another person's entry already has your id (you
  forked their mod), either get them to add you or list yours under **a new id**: rename the mod
  id, data folder, crate, `[[module]]` names and helper prefixes (see voice-chat.md), and say in the
  PR why it is a separate listing.
- **Assets of all-rights-reserved mods** (Simple Voice Chat's icons, OptiFine anything) can't be in
  the file or the repository; behaviour can be reproduced, files can't. Say "not affiliated".
- **Trademarks in names**: describe ("OptiFine-style zoom") rather than claim to be the original.
- A brand-new repository for a fork: `git archive HEAD | tar -x` into a new folder, `git init`, one
  commit, keep LICENSE and credits; archive (don't delete) the old fork if an upstream PR still
  points at its branches.
