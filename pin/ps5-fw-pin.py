#!/usr/bin/env python3
"""
ps5-fw-pin: keep a jailbroken PS5 on its current firmware.

Stops the console from staging a newer firmware (for example staying on
13.60.007 while 14.x is out and Relapse doesn't support it).

  --floor  (default, always works)
    Reads the firmware version and stops if it is 14.x, deletes any pending
    /update/PS5UPDATE.PUP, then checks /update is clean. Pair it with
    Settings > System > System Software and Updates > Automatic Downloads > Off.

  --full   (needs /dev/nfs from the kstuff app or etaHEN kfs)
    Everything --floor does, plus backs up the real /etc/hosts and points the
    update servers at 127.0.0.1, so the console never sees an update exists.

Usage:
  python3 pin/ps5-fw-pin.py --host <PS5 IP> [--port 2323] [--floor | --full] [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys

from ps5shell import PS5Shell

UPDATE_HOSTS = [
    "update.playstation.com",
    "dl.playstation.com",
]
PUP_PATH = "/update/PS5UPDATE.PUP"
BACKUP_SUFFIX = ".fwpin.bak"
BLOCKED_MAJOR_VERSIONS = {"14"}
VERSION_FILES = (
    "/system_ex/version.txt",
    "/system/version.txt",
    "/dev/nfs/system/version.txt",
    "/etc/version.txt",
    "/system_data/settings/version.txt",
)
HOSTS_FILES = ("/dev/nfs/etc/hosts", "/etc/hosts")


def detect_firmware(shell: PS5Shell) -> str | None:
    """Return the firmware version string, or None if no known file has it."""
    for path in VERSION_FILES:
        match = re.search(r"\d+\.\d+(?:\.\d+)?", shell.run(f"cat {path}", wait=2.5))
        if match:
            return match.group(0)
    return None


def pending_update_exists(shell: PS5Shell) -> bool:
    listing = shell.run("ls -la /update", wait=4)
    return any(line.split()[-1] == "PS5UPDATE.PUP" for line in listing.splitlines() if line.split())


def remove_pending_update(shell: PS5Shell, dry_run: bool) -> None:
    if not pending_update_exists(shell):
        print("  no pending PS5UPDATE.PUP")
        return
    print(f"  found pending update: {PUP_PATH}")
    if dry_run:
        print("  [dry-run] would delete it")
        return
    shell.run(f"rm {PUP_PATH}", wait=4)
    print("  deleted.")


def pin_hosts(shell: PS5Shell, hosts_path: str, dry_run: bool) -> bool:
    """Point the update servers at 127.0.0.1. Returns False if the change didn't stick."""
    current = shell.run(f"cat {hosts_path}", wait=4)
    if all(hostname in current for hostname in UPDATE_HOSTS):
        print(f"  {hosts_path} already pinned")
        return True
    backup_path = hosts_path + BACKUP_SUFFIX
    if dry_run:
        print(f"  [dry-run] would back up {hosts_path} -> {backup_path}")
        for hostname in UPDATE_HOSTS:
            print(f"  [dry-run] would add: 127.0.0.1   {hostname}")
        return True
    if not shell.exists(backup_path):
        shell.run(f"cp {hosts_path} {backup_path}")
        if not shell.exists(backup_path):
            print(f"  could not create {backup_path}. Leaving {hosts_path} untouched.")
            return False
    print(f"  backed up to {backup_path}")
    missing = [hostname for hostname in UPDATE_HOSTS if hostname not in current]
    entries = "".join(f"127.0.0.1   {hostname}\\n" for hostname in missing)
    shell.run(f'printf "\\n{entries}" >> {hosts_path}')
    pinned = shell.run(f"cat {hosts_path}", wait=4)
    if not all(hostname in pinned for hostname in UPDATE_HOSTS):
        print(f"  writing {hosts_path} failed (read-only mount?). The update servers are NOT blocked.")
        return False
    print("  pinned update hosts")
    return True


def run_pin(shell: PS5Shell, args: argparse.Namespace) -> int:
    firmware = detect_firmware(shell)
    if firmware is None:
        print("firmware: unknown. Check it on the console: Settings > System > System Software.")
    else:
        print(f"firmware: {firmware}")
        if firmware.split(".")[0] in BLOCKED_MAJOR_VERSIONS:
            print("STOP: this console is on 14.x, which the jailbreak may not support.")
            print("Check your exploit's supported firmware list, or see downgrade/README.md.")
            return 1

    print("== floor ==")
    remove_pending_update(shell, args.dry_run)
    if not args.dry_run:
        clean = not pending_update_exists(shell)
        print(f"  /update clean: {clean}")
        if not clean:
            print("  could not delete the pending update. Delete /update/PS5UPDATE.PUP by hand.")
            return 1

    if args.full:
        print("== full: /etc/hosts pin ==")
        hosts_path = next((path for path in HOSTS_FILES if shell.exists(path)), None)
        if hosts_path is None:
            print("  no writable hosts file found (ls /dev/nfs fails in this shell).")
            print("  Load the kstuff app or etaHEN kfs, then re-run with --full.")
            print("  The floor steps above already ran, so the console is still protected.")
            return 1
        print(f"  hosts file: {hosts_path}")
        if not pin_hosts(shell, hosts_path, args.dry_run):
            print("  The floor steps above already ran, so the console is still protected.")
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pin a jailbroken PS5 to its current firmware.")
    parser.add_argument("--host", required=True,
                        help="PS5 IP address (Settings > Network > Connection Status)")
    parser.add_argument("--port", type=int, default=2323, help="shsrv port (default 2323)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--floor", action="store_true",
                      help="default: check firmware, delete any pending update")
    mode.add_argument("--full", action="store_true",
                      help="floor + block the update servers in /etc/hosts (needs /dev/nfs)")
    parser.add_argument("--dry-run", action="store_true", help="show changes without making them")
    args = parser.parse_args()

    print("== ps5-fw-pin ==")
    print(f"target: {args.host}:{args.port}  mode: {'full' if args.full else 'floor'}"
          f"{'  (dry-run)' if args.dry_run else ''}")

    try:
        shell = PS5Shell(args.host, args.port)
    except OSError as error:
        print(f"cannot reach shsrv at {args.host}:{args.port}: {error}")
        print("Is the jailbreak active and the shsrv payload loaded?")
        return 2

    with shell:
        status = run_pin(shell, args)
    if status != 0:
        return status

    print()
    print("done. Reminders:")
    print("  - Automatic Downloads must be Off (Settings > System > System Software and Updates)")
    print("  - Update prompt: press X to dismiss. Stuck on an update screen: hold power 10s.")
    print("  - To undo: python3 pin/ps5-fw-unpin.py --host <PS5 IP>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
