"""Watch how much GTT memory a process holds, by default gnome-shell.

On AMD APUs the GPU has only a small carve-out of memory of its own; everything beyond it is GTT,
taken from system RAM. A leaking compositor can hold gigabytes this way until you log out. This tool
reads the numbers the kernel publishes in /proc/<pid>/fdinfo (no root needed) and warns above a limit.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

GTT = re.compile(r"drm-memory-gtt:\s+(\d+)[ \t]*(KiB|MiB)?")
CLIENT = re.compile(r"drm-client-id:\s+(\d+)")
UNITS = {"KiB": 1024, "MiB": 1024 * 1024}
PROC = Path("/proc")


def gtt_mb(fdinfo: Path) -> int | None:
    """GTT memory in MB of one process, from its fdinfo folder, or None when the kernel publishes no GTT
    figure for it. Every DRM client counts once, even with several open files. The kernel reports the
    size in bytes, KiB or MiB; the total is rounded down to whole MB only after adding up all clients."""
    per_client = {}
    for entry in fdinfo.iterdir():
        try:
            text = entry.read_text()
        except OSError:
            continue
        if (client := CLIENT.search(text)) and (gtt := GTT.search(text)):
            per_client[client.group(1)] = int(gtt.group(1)) * UNITS.get(gtt.group(2) or "", 1)
    if not per_client:
        return None
    return sum(per_client.values()) // (1024 * 1024)


def find_pid(name: str) -> int | None:
    """A process of the current user with exactly this name, or None."""
    out = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", name], capture_output=True, text=True,
                         check=False).stdout.split()
    return int(out[0]) if out else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gtt-watch", description="GTT memory of a process (default: gnome-shell).")
    parser.add_argument("--process", default="gnome-shell", help="process name (default: gnome-shell)")
    parser.add_argument("--limit", type=int, metavar="MB", help="exit with status 2 above this many MB")
    parser.add_argument("--notify", action="store_true", help="also show a desktop notification above the limit")
    args = parser.parse_args(argv)

    pid = find_pid(args.process)
    if pid is None:
        print(f"gtt-watch: no {args.process} process for this user", file=sys.stderr)
        return 1
    try:
        mb = gtt_mb(PROC / str(pid) / "fdinfo")
    except OSError as exc:
        print(f"gtt-watch: cannot read fdinfo of {args.process} ({pid}): {exc}", file=sys.stderr)
        return 1
    if mb is None:
        print(f"gtt-watch: no GTT figure in the fdinfo of {args.process} ({pid}), the kernel driver does not "
              "publish one for it", file=sys.stderr)
        return 1

    print(f"{args.process}: {mb} MB GTT")
    if args.limit is not None and mb > args.limit:
        message = f"{args.process} holds {mb} MB of GTT memory (limit {args.limit} MB). Logging out and in frees it."
        print(message, file=sys.stderr)
        if args.notify:
            subprocess.run(["notify-send", "-u", "critical", "GTT memory", message], check=False)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
