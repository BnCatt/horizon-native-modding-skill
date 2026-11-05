"""Run RCON commands one at a time and report which ones make the Horizon client log new
`could not translate` lines (the older-servers adapter failing on a packet).

    RCON_PASS=... python bisect.py <client log> <commands.txt> [--match "could not translate"]

commands.txt: one command per line, `#` comments skipped. Waits 1.5 s after each command.
Prints `BAD <command>` with the new log lines under it, `ok  <command>` otherwise.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rcon  # noqa: E402


def hits(log, needle):
    with open(log, encoding="utf-8", errors="replace") as f:
        return [line.strip() for line in f if needle in line]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("commands")
    ap.add_argument("--match", default="could not translate")
    ap.add_argument("--wait", type=float, default=1.5)
    a = ap.parse_args()
    s = rcon.connect()
    with open(a.commands, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    for i, cmd in enumerate(lines, start=2):
        before = len(hits(a.log, a.match))
        s.sendall(rcon.pkt(i, 2, cmd))
        _, out = rcon.read(s)
        time.sleep(a.wait)
        new = hits(a.log, a.match)[before:]
        print(f"{'BAD ' if new else 'ok  '}{cmd[:110]}  [{out.strip()[:60]}]")
        for w in new:
            print("      " + w[-170:])


if __name__ == "__main__":
    main()
