"""Minimal RCON client for a test server.

    python rcon.py "cmd1" "cmd2" "sleep 2" ...

Env: RCON_HOST (127.0.0.1), RCON_PORT (25575), RCON_PASS (required). A `sleep N` argument waits.
"""
import os
import socket
import struct
import sys
import time

HOST = os.environ.get("RCON_HOST", "127.0.0.1")
PORT = int(os.environ.get("RCON_PORT", "25575"))
PASS = os.environ.get("RCON_PASS", "")


def pkt(rid, kind, body):
    data = struct.pack("<ii", rid, kind) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(data)) + data


def read(s):
    raw = b""
    while len(raw) < 4:
        raw += s.recv(4 - len(raw))
    (n,) = struct.unpack("<i", raw)
    data = b""
    while len(data) < n:
        data += s.recv(n - len(data))
    rid, _kind = struct.unpack("<ii", data[:8])
    return rid, data[8:-2].decode("utf-8", "replace")


def connect():
    if not PASS:
        sys.exit("set RCON_PASS")
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.sendall(pkt(1, 3, PASS))
    rid, _ = read(s)
    if rid == -1:
        sys.exit("rcon auth failed")
    return s


def main():
    s = connect()
    for i, cmd in enumerate(sys.argv[1:], start=2):
        if cmd.startswith("sleep "):
            time.sleep(float(cmd.split()[1]))
            continue
        s.sendall(pkt(i, 2, cmd))
        _, out = read(s)
        print(f"> {cmd}\n  {out.strip()[:300]}")
    s.close()


if __name__ == "__main__":
    main()
