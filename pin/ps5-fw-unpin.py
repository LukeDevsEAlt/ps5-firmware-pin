#!/usr/bin/env python3
"""
ps5-fw-unpin: undo ps5-fw-pin.py so the console can update normally.

Restores /etc/hosts from the .fwpin.bak backup that --full made. --floor
changes nothing permanent, so after a --floor pin the only thing to undo is
the console setting (Automatic Downloads), which you flip back yourself.

Usage:
  python3 pin/ps5-fw-unpin.py --host <PS5 IP> [--port 2323] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys

from ps5shell import PS5Shell

BACKUP_SUFFIX = ".fwpin.bak"
HOSTS_FILES = ("/dev/nfs/etc/hosts", "/etc/hosts")


def restore_hosts(shell: PS5Shell, dry_run: bool) -> bool:
    """Put the backed-up hosts file back. Returns False if the restore didn't stick."""
    for hosts_path in HOSTS_FILES:
        backup_path = hosts_path + BACKUP_SUFFIX
        if not shell.exists(backup_path):
            continue
        print(f"backup found: {backup_path}")
        if dry_run:
            print(f"[dry-run] would restore it over {hosts_path}")
            return True
        shell.run(f"cp {backup_path} {hosts_path}")
        if shell.run(f"cat {hosts_path}", wait=4) != shell.run(f"cat {backup_path}", wait=4):
            print(f"restoring {hosts_path} failed (read-only mount?). Backup kept at {backup_path}.")
            return False
        shell.run(f"rm {backup_path}")
        print(f"restored {hosts_path} from backup")
        return True
    print("no hosts backup found: nothing was pinned with --full, or it was already undone.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Undo a PS5 firmware pin.")
    parser.add_argument("--host", required=True,
                        help="PS5 IP address (Settings > Network > Connection Status)")
    parser.add_argument("--port", type=int, default=2323, help="shsrv port (default 2323)")
    parser.add_argument("--dry-run", action="store_true", help="show changes without making them")
    args = parser.parse_args()

    print("== ps5-fw-unpin ==")
    try:
        shell = PS5Shell(args.host, args.port)
    except OSError as error:
        print(f"cannot reach shsrv at {args.host}:{args.port}: {error}")
        print("Is the jailbreak active and the shsrv payload loaded?")
        return 2

    with shell:
        restored = restore_hosts(shell, args.dry_run)
    if not restored:
        return 1

    print()
    print("unpinned. To turn automatic update downloads back on:")
    print("  Settings > System > System Software and Updates > Automatic Downloads > On")
    return 0


if __name__ == "__main__":
    sys.exit(main())
