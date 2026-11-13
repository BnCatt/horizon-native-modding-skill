# Testing for real: Paper + RCON + horizon-ctl

"It compiled" is not "it works". Drive the actual game.

## A disposable Paper server

- Any `paper-<ver>.jar` (or an existing local server folder: copy the jar, `cache`, `versions`,
  `libraries` to skip downloads) + the owner's `eula.txt`.
- `server.properties` for tests: `online-mode=false` (horizon-ctl connects with an offline name),
  a spare `server-port`, `level-type=minecraft\:flat`, `enable-rcon=true`, `rcon.port`,
  `rcon.password`, **`pause-when-empty-seconds=-1`** (1.21.2+ pauses an empty server after 60 s),
  `spawn-protection=0`.
- Java 21 for 1.21.x. Wait for `Done (` in the log. `scripts/rcon.py` sends commands.
- Public test servers: `online-mode=true` when the whitelist is off.

## horizon-ctl

Each installed version ships `horizon-ctl.exe`. Isolate the player's data: fresh `HORIZON_HOME`,
run from that folder (the game dir is the working directory), `HORIZON_NO_AUDIO=1`,
`HORIZON_LAUNCHER_NO_SELF_UPDATE=1`, and `HORIZON_OLDER_SERVERS=1` for older servers.

```bash
CTL=".../versions/<tag>/horizon-ctl.exe"; S="--socket $PWD/ctl.sock"
$CTL $S launch --offscreen --version <tag>            # an installed (or native-…) version
$CTL $S launch --offscreen --game <exe> --resources <versions/<tag>/.local/horizon-client/26.3>
$CTL $S connect 127.0.0.1:25599 TestName
$CTL $S status | grep -oE '"decode_errors":[0-9]+|"chunks":[0-9]+'
$CTL $S ui            # widget ids on the current screen;  $CTL $S click <id>
$CTL $S click-at <guiX> <guiY> [right]                # e.g. a mod button
$CTL $S screenshot shot.png                           # then look at it
$CTL $S quit
```

- A fresh home shows the accessibility welcome (`click continue`) and the multiplayer warning
  (`click proceed`).
- Its output log is `<socket>.log` beside the socket; the game's own log is
  `$HORIZON_HOME/logs/latest.log`.
- Useful action commands: `break X Y Z`, `place X Y Z --item`, `interact X Y Z`, `use-item --hold S`,
  `attack <id>`, `select <slot|item>`, `drop`, `chat`, `command`, `respawn`, `entities R type`,
  `looking-at`, `inventory`, `screen`, `events`.
- `move` doesn't steer a ridden horse (also in single player): not an adapter bug.
- `key <k>` alone does nothing: use `key <k> tap` (or `down` / `up`). `key c down` + `wait 5` holds a
  zoom key; `key f3 tap` opens the debug screen for a screenshot.
- `click-at` and `screen` don't see **native mod screens** (`"screen":"mod"`, no buttons): a mod's own
  menu can be opened with its key and screenshotted, not clicked. Set its settings for a test by
  writing the files in the test home's `horizon-mods/.horizon-mod-data/<id>/` before launch.
- `open <World> <seed> creative` makes a single-player world from the title screen; then
  `wait-ready`, `give`, `select`, `look`, `scroll-at X Y`, `mouse-move DX DY` (goes through
  sensitivity and the cinematic camera: a smoothed turn shows as a small yaw right after the move and
  the rest some ticks later, which is how to prove the cinematic camera is on).
- `messages` lists recent chat lines: check a mod's chat output (or its absence) there.
- **Tick-exact steps go in one `script`.** Every separate `horizon-ctl` call costs several ticks
  (a new process and a round trip), so "attack, 2 ticks later swap, 9 ticks later screenshot" as
  four calls shoots the screenshot after a 23-tick animation is over. Pipe the lines to
  `horizon-ctl script` (`attack` / `wait 2` / `select golden_apple` / `wait 9` /
  `screenshot C:/abs/path.png`): `wait`'s replies show the tick each step ran at.
- `state` (not `status`) has the player's `swings` (arm swings started), `using`, `mining`: use it
  to check that an `attack` in the air really swung.
- A visual A/B of an animation fix: the same script with the mod's setting off and on, plus a
  screenshot at rest; "on" equals the rest pose, "off" shows the bug. Different world names put the
  player elsewhere, so compare the hand, not the scenery.
- `click <id>` uses the label's slug (`Lunge animation fix: ON` → `lunge-animation-fix`, the value
  after the colon is not part of it); `ui` lists the ids. The Options > Mods rows are
  `<name>-<version>` with a `settings[-N]` button each, reachable from the title screen.
- An installed Nightly's `horizon-ctl.exe` and prepared resources also drive a newer locally built
  `horizon-client.exe` (seen: 2026-11-07's ctl and resources with a 2026-11-13 build), so the newest
  Nightly doesn't have to be installed in the launcher to test against its source.

## Bisecting translation bugs

`scripts/bisect.py <client log> <commands.txt>` runs each RCON command, waits 1.5 s and prints which
ones added `could not translate` lines. A good command list: `give` items with every interesting
component, `summon` every entity type, displays, particles, titles/bossbar/scoreboard/teams,
dimension changes, death and respawn. Also play client-side actions (break/place, open a chest and
shift-click, eat, throw, attack, shear, trade, ride). Compare against a build without your fix to
show the before/after.
- On the title screens `key` and `type` answer "no world open": keyboard input to a title-menu
  overlay (Escape, a search box) can't be driven by horizon-ctl; test it by hand. `click-at` and
  `click-button` work there (`ui` gives `gui_size`; a screenshot is `gui_size` × the GUI scale).
