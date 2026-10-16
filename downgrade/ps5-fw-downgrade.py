#!/usr/bin/env python3
"""
ps5-fw-downgrade: download and check a PS5 firmware file (PUP) for a USB install.

PS5 downgrades work while Sony's keyset 0 is active (as of Oct 2026 it is,
no rollback lock has shipped). Any firmware change wipes the jailbreak:
you re-run your exploit and reload payloads afterward. Your games and saves
are not touched.

Sony only links the latest firmware, so older versions come from a PS5
homebrew mirror (e.g. PSXHAX). Download it with this script, or download it
yourself and check it:

  python3 downgrade/ps5-fw-downgrade.py --url https://mirror.example/PS5UPDATE.PUP
  python3 downgrade/ps5-fw-downgrade.py --verify /path/to/PS5UPDATE.PUP --md5

USB install:
  1. Format a USB stick as exFAT or FAT32
  2. Put the file at this exact path on the stick:
         USB:/PS5/UPDATE/PS5UPDATE.PUP
  3. PS5: Settings > System > System Software and Updates >
         Install Update from USB Drive
  4. After install + reboot: re-jailbreak, reload payloads, done.

No dependencies, stdlib only (Python 3.8+).
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import os
import sys
import time
import urllib.request

MIN_PUP_BYTES = 512 * 1024 * 1024

REJAILBREAK_CHECKLIST = """
After the console reboots into the new firmware, the jailbreak is GONE
(firmware changes wipe it). Checklist:

  1. Run your exploit (Relapse: launch the Relapse Installer app)
  2. Load your payloads (ftpsrv, shsrv, ShadowMountPlus, whatever you run)
  3. ShadowMountPlus re-mounts your game dumps automatically. Check the
     home screen for your apps
  4. Re-apply the firmware pin if you were using it:
         python3 pin/ps5-fw-pin.py --host <PS5 IP>
     (and flip Automatic Downloads back to Off in Settings)
"""

USB_INSTRUCTIONS = """
== Install on the PS5 ==
  1. USB stick formatted as exFAT or FAT32, file at this path from the stick root:
         PS5/UPDATE/PS5UPDATE.PUP
     (rename your file to PS5UPDATE.PUP if needed)
  2. PS5: Settings > System > System Software and Updates
         > Install Update from USB Drive
  3. Don't turn the console off while it installs. It reboots by itself.

NOTE: if the console says the update is "older than the current
system software", that's normal for a downgrade and the option still
installs it (keyset 0 is active as of Oct 2026).
"""


def verify_pup(path: str) -> tuple[bool, str]:
    """Catch the usual bad downloads (stubs, HTML error pages). Returns (ok, reason)."""
    if not os.path.isfile(path):
        return False, f"no such file: {path}"
    size = os.path.getsize(path)
    if size < MIN_PUP_BYTES:
        return False, (f"only {size:,} bytes, a real PUP is about 1 GB "
                       f"(this looks like a stub or an error page)")
    with open(path, "rb") as pup_file:
        head = pup_file.read(64).lstrip().lower()
    if head.startswith((b"http", b"<!do", b"<htm")):
        return False, "file starts with HTML: the server returned a web page, not the PUP"
    return True, f"{size:,} bytes"


def md5_of(path: str) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as pup_file:
        for chunk in iter(lambda: pup_file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: str) -> None:
    print(f"downloading {url}")
    print(f"          -> {dest}")
    partial_path = dest + ".part"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    start = time.time()
    with urllib.request.urlopen(request, timeout=30) as response, open(partial_path, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            received += len(chunk)
            rate = received / max(time.time() - start, 0.001) / 1024 / 1024
            progress = f"{received/1024**3:6.2f} / {total/1024**3:.2f} GB" if total else f"{received/1024**3:6.2f} GB"
            print(f"\r  {progress}  @ {rate:.1f} MB/s", end="", flush=True)
    print()
    if total and received != total:
        raise OSError(f"connection dropped after {received:,} of {total:,} bytes")
    os.replace(partial_path, dest)
    print(f"downloaded {received:,} bytes in {time.time()-start:.0f}s")


def finish(path: str, show_md5: bool) -> None:
    if show_md5:
        print("md5:", md5_of(path))
    print(USB_INSTRUCTIONS)
    print(REJAILBREAK_CHECKLIST)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and check a PS5 firmware PUP for USB install.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="PUP download link, from a PS5 homebrew mirror")
    source.add_argument("--verify", metavar="PATH", help="check a PUP you already have and exit")
    parser.add_argument("--md5", action="store_true", help="print the MD5 to compare with the mirror's checksum")
    parser.add_argument("-o", "--out", default="PS5UPDATE.PUP", help="output filename (default: PS5UPDATE.PUP)")
    args = parser.parse_args()

    if args.verify:
        ok, reason = verify_pup(args.verify)
        print(("OK  " if ok else "FAIL") + f" {args.verify}: {reason}")
        if not ok:
            return 1
        finish(args.verify, args.md5)
        return 0

    dest = args.out
    if os.path.exists(dest):
        ok, reason = verify_pup(dest)
        if ok:
            print(f"{dest} already present and looks valid ({reason}). Skipping download.")
            finish(dest, args.md5)
            return 0
        print(f"{dest} exists but fails the check ({reason}). Downloading it again.")

    try:
        download(args.url, dest)
    except (OSError, http.client.HTTPException) as error:
        print(f"\ndownload failed: {error}")
        print("Check the link in a browser. Mirrors move files often; try another one.")
        return 1

    ok, reason = verify_pup(dest)
    if not ok:
        print(f"FAIL: downloaded file looks wrong: {reason}")
        return 1
    print(f"OK: {reason}")
    finish(dest, args.md5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
