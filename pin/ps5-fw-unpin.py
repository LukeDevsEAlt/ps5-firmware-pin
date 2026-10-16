#!/usr/bin/env python3
"""
ps5-fw-unpin: undo ps5-fw-pin.py so the console can update normally.

Restores /etc/hosts from the .fwpin.bak backup that --full made. --floor
changes nothing permanent, so after a --floor pin the only thing to undo is
the console setting (Automatic Downloads), which you flip back yourself.

Usage:
  python3 pin/ps5-fw-unpin.py --host <PS5 IP> [--port 2323] [--dry-run]
"""

import argparse
import sys

from ps5shell import PS5Shell

BACKUP_SUFFIX = ".fwpin.bak"
HOSTS_FILES = ("/dev/nfs/etc/hosts", "/etc/hosts")


def restore_hosts(shell, dry_run):
    for hosts_path in HOSTS_FILES:
        backup_path = hosts_path + BACKUP_SUFFIX
        if not shell.exists(backup_path):
            continue
        print(f"backup found: {backup_path}")
        if dry_run:
            print(f"[dry-run] would restore it over {hosts_path}")
        else:
            shell.run(f"cp {backup_path} {hosts_path}")
            shell.run(f"rm {backup_path}")
            print(f"restored {hosts_path} from backup")
        return
    print("no hosts backup found: nothing was pinned with --full, or it was already undone.")


def main():
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
        restore_hosts(shell, args.dry_run)

    print()
    print("unpinned. To turn automatic update downloads back on:")
    print("  Settings > System > System Software and Updates > Automatic Downloads > On")
    return 0


if __name__ == "__main__":
    sys.exit(main())
