# horizon-native-modding — a Claude skill

A [Claude Code](https://claude.com/claude-code) / Agent skill for building, fixing, packaging and
testing **native mods** for [Horizon](https://github.com/horizon-rust/horizon), the Rust rewrite of
Minecraft: Java Edition 26.3, and for getting the Horizon launcher's native build to pass on Windows.

Everything in it was learned the hard way on real 26.3 Nightlies (November 2026): writing
hook-point mods, porting a Simple Voice Chat client, a ViaFabricPlus-style version picker for the
older-servers adapter, fixing the adapter's 1.21.11 item translation, and repairing third-party mods
that broke when a Nightly moved code.

## What's inside

```
horizon-native-modding/
├── SKILL.md                       # the map + the rules that bite most
├── references/
│   ├── mixins-manifest.md         # horizon-mixin.toml, helpers, [[module]], [[crate]], plan/apply
│   ├── hook-points.md             # useful hooks/helpers, API levels, what a client can't get
│   ├── launcher-build-windows.md  # native-build, profiles, os error 32 fixes, dev loop
│   ├── fixing-third-party-mods.md # plan-all procedure + real breakages and fixes
│   ├── older-servers.md           # protocol adapter, version picker mod, EitherHolder items
│   ├── gui-sprites.md             # vanilla-looking screens: sprites, nine-slice, sliders, icons
│   ├── voice-chat.md              # Simple Voice Chat client on hook points, opus/rnnoise on Windows
│   ├── publishing.md              # mod browser: registry PR, licences, ids, releases
│   └── testing.md                 # Paper + RCON + horizon-ctl, bisecting translation bugs
└── scripts/
    ├── package_hnmod.py           # deterministic source-only .hnmod (+ --install)
    ├── patch_hnmod.py             # one-line fix inside an installed .hnmod
    ├── prep_native_build.sh       # clear the launcher's stale build leftovers
    ├── rcon.py, bisect.py         # drive a test server, find failing packets
    ├── build_opus.py              # opus.dll from official libopus with MinGW
    └── build_rnnoise.py           # rnnoise.dll from xiph's v0.2 release tarball
```

## Install

Claude Code (user-wide):

```bash
git clone https://github.com/BnCatt/horizon-native-modding-skill
cp -r horizon-native-modding-skill/horizon-native-modding ~/.claude/skills/
```

Or per project: copy the `horizon-native-modding` folder into `<project>/.claude/skills/`.
Claude picks it up when you mention Horizon, `.hnmod`, horizon-mixins, native-build errors, etc.

## Notes

- Horizon moves fast; targets, struct fields and the hook API change between Nightlies. The skill
  teaches how to check against the exact `nightly-source/<date>-<short>` tag rather than trusting
  any list — including the examples here.
- Not affiliated with Mojang, Microsoft, the Horizon project or Simple Voice Chat.

## License

MIT (see LICENSE). `scripts/build_opus.py` builds libopus and `scripts/build_rnnoise.py` rnnoise,
both BSD-3-Clause; ship their COPYING with any DLL you distribute.

## Contributing — agents too

The skill asks the agent using it to **offer a pull request here with whatever it learned** that the
skill didn't cover (with its user's OK), so every Horizon task makes the next one easier. See
[CONTRIBUTING.md](CONTRIBUTING.md).
