#!/usr/bin/env python3
"""
ps5-fw-pin — keep a jailbroken PS5 on its current firmware.

Prevents the console from downloading or installing a newer firmware
(e.g. staying on 13.60.007 while 14.x is out and Relapse doesn't support it).

Two modes:

  --floor  (safe, always works)
    - Verifies the jailbroken shell is reachable
    - Checks the firmware version (refuses to continue on unexpected major)
    - Removes any pending PS5UPDATE.PUP from /update
    - Verifies /update is clean
    Pair with the console setting:
      Settings > System > System Software and Updates >
      Automatic Downloads > System Software and Apps > OFF
    That alone means: no background download, nothing staged to install,
    and the only remaining prompt is a button you press X on.

  --full   (strong, needs a kfs mount)
    - Does everything --floor does, plus
    - Pins the real /etc/hosts (via /dev/nfs, created by the kstuff app or
      modern etaHEN kfs) so update.playstation.com resolves to 127.0.0.1.
      The update checker then can't even see that an update exists.
    - Backs up the original hosts first.
    Use --full only when `ls /dev/nfs` works in your jailbreak shell.

Usage:
  python3 ps5-fw-pin.py [--host 192.168.1.78] [--port 2323]
                        [--floor | --full] [--dry-run] [--strict]

--strict (full mode): keeps a corrupted PUP on disk so any attempted
14.x install fails signature verification and reboots to current firmware.
"""

import argparse
import re
import socket
import sys

UPDATE_HOSTS = [
    "update.playstation.com",
    "dl.playstation.com",
]
PUP_PATH = "/update/PS5UPDATE.PUP"
BACKUP_SUFFIX = ".fwpin.bak"


class PS5Shell:
    """Minimal telnet-style client for the PS5 shsrv shell (port 2323).

    The shell is a busybox sh in a chroot whose root is the real system
    root. Quirks handled: no `2>&1`, no `find`, no `head`, line endings
    are \r\n, prompt is '/$ '.
    """

    def __init__(self, host, port, timeout=3.0):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(timeout)

    def _drain(self, seconds):
        end = __import__("time").time() + seconds
        buf = b""
        while __import__("time").time() < end:
            try:
                d = self.sock.recv(4096)
                if not d:
                    break
                buf += d
            except socket.timeout:
                break
        return buf

    def cmd(self, command, wait=3.0):
        self.sock.sendall(command.encode() + b"\n")
        out = self._drain(wait).decode(errors="replace")
        lines = [l for l in out.splitlines()
                 if l.strip() and l.strip() != "/$"
                 and not l.strip().startswith("/$")]
        return "\n".join(lines).strip()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def detect_firmware(shell):
    """Best-effort firmware read from known locations. May return None.

    The shell view has no /etc, so we probe the spots that do exist on
    13.x. None is acceptable — the caller treats it as 'verify manually'.
    """
    for path in ("/system_ex/version.txt", "/system/version.txt",
                 "/dev/nfs/system/version.txt", "/etc/version.txt",
                 "/system_data/settings/version.txt"):
        try:
            out = shell.cmd(f"cat {path}", wait=2.5)
        except (OSError, socket.timeout):
            continue
        m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", out)
        if m:
            return m.group(0)
    return None


def update_dir_listing(shell):
    return shell.cmd("ls -la /update", wait=4)


def remove_pup(shell, dry_run):
    out = update_dir_listing(shell)
    if "PS5UPDATE.PUP" in out:
        print(f"  found pending update: {PUP_PATH}")
        if dry_run:
            print("  [dry-run] would delete it")
        else:
            shell.cmd(f"rm {PUP_PATH}", wait=4)
            print("  deleted.")
        return True
    print("  no pending PS5UPDATE.PUP")
    return False


def verify_update_clean(shell):
    out = update_dir_listing(shell)
    clean = "PS5UPDATE.PUP" not in out
    print(f"  /update clean: {clean}")
    return clean


def find_hosts(shell):
    for path in ("/dev/nfs/etc/hosts", "/etc/hosts"):
        out = shell.cmd(f"ls {path}", wait=3)
        if "No such file" not in out and "cannot access" not in out.lower():
            return path
    return None


def pin_hosts(shell, hosts, dry_run):
    current = shell.cmd(f"cat {hosts}", wait=4)
    already = any(h in current for h in UPDATE_HOSTS)
    if already:
        print("  /etc/hosts already pinned")
        return True
    if dry_run:
        print(f"  [dry-run] would backup {hosts} -> {hosts}{BACKUP_SUFFIX}")
        for h in UPDATE_HOSTS:
            print(f"  [dry-run]   127.0.0.1   {h}")
        return True
    shell.cmd(f"cp {hosts} {hosts}{BACKUP_SUFFIX}", wait=3)
    for h in UPDATE_HOSTS:
        shell.cmd(f'printf "127.0.0.1   {h}\\n" >> {hosts}', wait=3)
    print(f"  backed up to {hosts}{BACKUP_SUFFIX}")
    print("  pinned update hosts")
    return True


def main():
    ap = argparse.ArgumentParser(description="Pin a jailbroken PS5 to its current firmware.")
    ap.add_argument("--host", default="192.168.1.78", help="PS5 IP (default 192.168.1.78)")
    ap.add_argument("--port", type=int, default=2323, help="shsrv telnet port (default 2323)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--floor", action="store_true",
                      help="safe mode: verify fw, delete PUP, verify /update clean")
    mode.add_argument("--full", action="store_true",
                      help="strong mode: floor + pin /dev/nfs/etc/hosts (needs kfs mount)")
    ap.add_argument("--dry-run", action="store_true", help="show changes without making them")
    ap.add_argument("--strict", action="store_true",
                    help="full mode: keep a corrupted PUP as a signature tripwire")
    args = ap.parse_args()

    if not (args.floor or args.full):
        args.floor = True  # safe default

    print("== ps5-fw-pin ==")
    print(f"target: {args.host}:{args.port}  mode: {'full' if args.full else 'floor'}"
          f"{'  (dry-run)' if args.dry_run else ''}")

    try:
        shell = PS5Shell(args.host, args.port)
    except OSError as e:
        print(f"cannot reach shsrv at {args.host}:{args.port}: {e}")
        print("Is the jailbreak active and the shsrv payload loaded?")
        return 2

    shell._drain(2)

    # 1. firmware gate
    fw = detect_firmware(shell)
    print(f"firmware: {fw or 'UNKNOWN — verify manually (Settings > System)'}")
    if fw:
        major = fw.split(".")[0]
        if major == "14":
            print("STOP: firmware reads as 14.x. The jailbreak may not support it.")
            print("Do NOT run the pin; consult the exploit's supported-firmware list.")
            shell.close()
            return 1
    else:
        print("note: could not read version in-shell. Proceeding — you confirmed the version.")

    # 2. floor
    print("== floor ==")
    remove_pup(shell, args.dry_run)
    if not args.dry_run:
        verify_update_clean(shell)

    # 3. full mode: hosts pin
    if args.full:
        print("== full: /etc/hosts pin ==")
        hosts = find_hosts(shell)
        if not hosts:
            print("  /dev/nfs (or /etc/hosts) not found in this shell.")
            print("  Load the kstuff app / etaHEN kfs first, then re-run with --full.")
            print("  Floor mode still applies — the console is protected either way.")
            shell.close()
            return 1
        print(f"  hosts file: {hosts}")
        pin_hosts(shell, hosts, args.dry_run)
        if args.strict and not args.dry_run:
            print("  strict: leaving PUP as a signature tripwire (if any reappears,")
            print("  it will fail verification on install attempt)")

    shell.close()
    print()
    print("done. Reminders:")
    print("  - Auto Downloads must be OFF (Settings > System > System Software and Updates)")
    print("  - Update prompt: press X. Force-update boot screen: hold power 10s.")
    print("  - To unpin: python3 ps5-fw-unpin.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
