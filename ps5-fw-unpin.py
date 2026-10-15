#!/usr/bin/env python3
"""
ps5-fw-unpin — restore a pinned PS5 to normal update behavior.

Reverse of ps5-fw-pin.py:
  - Restores /etc/hosts from the .fwpin.bak backup (full mode)
  - Removes any corrupted tripwire PUP (strict mode)
  - Re-enables checking (Auto Downloads is a console setting you flip back
    in Settings if you want it on again)

Usage:
  python3 ps5-fw-unpin.py [--host 192.168.1.78] [--port 2323] [--dry-run]
"""

import argparse
import socket
import sys
import time

BACKUP_SUFFIX = ".fwpin.bak"


class PS5Shell:
    def __init__(self, host, port, timeout=3.0):
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(timeout)

    def _drain(self, seconds):
        end = time.time() + seconds
        buf = b""
        while time.time() < end:
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


def main():
    ap = argparse.ArgumentParser(description="Unpin a PS5 firmware pin.")
    ap.add_argument("--host", default="192.168.1.78")
    ap.add_argument("--port", type=int, default=2323)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("== ps5-fw-unpin ==")
    try:
        shell = PS5Shell(args.host, args.port)
    except OSError as e:
        print(f"cannot reach shsrv at {args.host}:{args.port}: {e}")
        return 2
    shell._drain(2)

    restored = False
    for hosts in ("/dev/nfs/etc/hosts", "/etc/hosts"):
        out = shell.cmd(f"ls {hosts}{BACKUP_SUFFIX}", wait=3)
        if "No such file" not in out and "cannot access" not in out.lower():
            print(f"backup found: {hosts}{BACKUP_SUFFIX}")
            if args.dry_run:
                print(f"[dry-run] would restore it over {hosts}")
            else:
                shell.cmd(f"cp {hosts}{BACKUP_SUFFIX} {hosts}", wait=3)
                shell.cmd(f"rm {hosts}{BACKUP_SUFFIX}", wait=3)
                print(f"restored {hosts} from backup")
            restored = True
            break
    if not restored:
        print("no hosts backup found — nothing was pinned in full mode (or it was already unpinned).")

    for f in ("/update/PS5UPDATE.PUP", "/update/PS5UPDATE.PUP.fwpin-trunc"):
        out = shell.cmd(f"ls {f}", wait=3)
        if "No such file" not in out:
            print(f"removing tripwire: {f}")
            if not args.dry_run:
                shell.cmd(f"rm {f}", wait=3)

    shell.close()
    print()
    print("unpinned. If you want automatic update downloads again:")
    print("  Settings > System > System Software and Updates > Automatic Downloads > ON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
