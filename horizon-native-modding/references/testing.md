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

## Bisecting translation bugs

`scripts/bisect.py <client log> <commands.txt>` runs each RCON command, waits 1.5 s and prints which
ones added `could not translate` lines. A good command list: `give` items with every interesting
component, `summon` every entity type, displays, particles, titles/bossbar/scoreboard/teams,
dimension changes, death and respawn. Also play client-side actions (break/place, open a chest and
shift-click, eat, throw, attack, shear, trade, ride). Compare against a build without your fix to
show the before/after.
