#!/usr/bin/env python3
"""
ps5-fw-downgrade: install a specific PS5 firmware from a PUP file.

Downloads a firmware PUP, verifies it, and prepares it for USB installation.
After the console installs it, this prints the re-jailbreak checklist.

PS5 downgrades work while Sony's keyset 0 is active (as of Oct 2026 it is,
no rollback lock has shipped). Any firmware change wipes the jailbreak:
you re-run your exploit and reload payloads afterward. Your games and saves
are not touched.

The official PUP URL pattern is below. If your region 404s, try another
region or grab the file from a PS5 homebrew mirror like PSXHAX:

  https://downloader.playstation.com/<europe|us|asia>/ps5os/<VERSION>/PS5UPDATE.PUP

Download the 13.60.007 file (for a downgrade from 14.x):

  python3 downgrade/ps5-fw-downgrade.py 13.60.007 --region europe
  python3 downgrade/ps5-fw-downgrade.py --url https://mirror.example/PS5UPDATE.PUP

Verify a PUP you already have:

  python3 downgrade/ps5-fw-downgrade.py --verify /path/to/PS5UPDATE.PUP

USB install (you do this, ~15 minutes):
  1. Format a USB stick as **exFAT** (or FAT32, PUPs fit under 4 GB)
  2. Put the file at this exact path on the stick:
         USB:/PS5/UPDATE/PS5UPDATE.PUP
  3. PS5: Settings > System > System Software and Updates >
         Install Update from USB Drive
  4. After install + reboot: re-jailbreak, reload payloads, done.

No dependencies, stdlib only (Python 3.8+).
"""

import argparse
import hashlib
import os
import sys
import time
import urllib.request

MIN_PUP_BYTES = 2 * 1024 * 1024 * 1024

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


def build_url(version, region):
    return f"https://downloader.playstation.com/{region}/ps5os/{version}/PS5UPDATE.PUP"


def verify_pup(path):
    """Check a PUP is sane. Returns (ok, reason)."""
    if not os.path.isfile(path):
        return False, f"no such file: {path}"
    size = os.path.getsize(path)
    if size < MIN_PUP_BYTES:
        return False, (f"only {size:,} bytes, a real PUP is 2-7 GB "
                       f"(this looks like a stub or an error page)")
    with open(path, "rb") as pup_file:
        head = pup_file.read(64).lstrip().lower()
    if head.startswith((b"http", b"<!do", b"<htm")):
        return False, "file starts with HTML: the server returned a web page, not the PUP"
    return True, f"{size:,} bytes"


def md5_of(path):
    digest = hashlib.md5()
    with open(path, "rb") as pup_file:
        for chunk in iter(lambda: pup_file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, dest):
    print(f"downloading {url}")
    print(f"          -> {dest}")
    partial_path = dest + ".part"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    start = time.time()
    with urllib.request.urlopen(request, timeout=30) as response, open(partial_path, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            got += len(chunk)
            rate = got / (time.time() - start) / 1024 / 1024
            if total:
                print(f"\r  {got/1024**3:6.2f} / {total/1024**3:.2f} GB  @ {rate:.1f} MB/s",
                      end="", flush=True)
            else:
                print(f"\r  {got/1024**3:6.2f} GB  @ {rate:.1f} MB/s", end="", flush=True)
    print()
    os.replace(partial_path, dest)
    print(f"downloaded {os.path.getsize(dest):,} bytes in {time.time()-start:.0f}s")


def main():
    parser = argparse.ArgumentParser(description="Download and stage a PS5 firmware PUP for USB install.")
    parser.add_argument("version", nargs="?", help="firmware version, e.g. 13.60.007")
    parser.add_argument("--region", default="europe", choices=["europe", "us", "asia"],
                    help="Sony CDN region (default: europe)")
    parser.add_argument("--url", help="explicit PUP URL (overrides version/region)")
    parser.add_argument("--verify", metavar="PATH", help="verify an existing PUP and exit")
    parser.add_argument("--md5", action="store_true", help="print the MD5 of the PUP (cross-check vs mirrors)")
    parser.add_argument("-o", "--out", default="PS5UPDATE.PUP", help="output filename (default: PS5UPDATE.PUP)")
    args = parser.parse_args()

    if args.verify:
        ok, reason = verify_pup(args.verify)
        print(("OK  " if ok else "FAIL") + f" {args.verify}: {reason}")
        if ok and args.md5:
            print("md5:", md5_of(args.verify))
        return 0 if ok else 1

    if args.url:
        url = args.url
    elif args.version:
        url = build_url(args.version, args.region)
    else:
        parser.error("give a version (e.g. 13.60.007) or --url, or --verify PATH")

    dest = args.out
    if os.path.exists(dest):
        ok, reason = verify_pup(dest)
        if ok:
            print(f"{dest} already present and looks valid ({reason}). Skipping download.")
            if args.md5:
                print("md5:", md5_of(dest))
            print(usb_instructions(dest))
            print(REJAILBREAK_CHECKLIST)
            return 0
        print(f"{dest} exists but fails the check ({reason}). Downloading it again.")

    try:
        download(url, dest)
    except Exception as error:
        print(f"\ndownload failed: {error}")
        print("If this is a 404, the region is wrong or the version has no direct CDN path.")
        print("grab the PUP from a PS5 homebrew mirror (PSXHAX) and use --url or --verify.")
        return 1

    ok, reason = verify_pup(dest)
    if not ok:
        print(f"FAIL: downloaded file looks wrong: {reason}")
        return 1
    print(f"OK: {reason}")
    if args.md5:
        print("md5:", md5_of(dest))
    print(usb_instructions(dest))
    print(REJAILBREAK_CHECKLIST)
    return 0


def usb_instructions(pup):
    return f"""
== Install on the PS5 ==
  1. USB stick formatted as exFAT, folder at the stick ROOT:
         PS5/UPDATE/PS5UPDATE.PUP
     (rename your file to PS5UPDATE.PUP if needed)
  2. PS5: Settings > System > System Software and Updates
         > Install Update from USB Drive
  3. Reboot, then re-jailbreak (below)

NOTE: if the console says the update is "older than the current
system software", that's normal for a downgrade and the option still
installs it (keyset 0 is active as of Oct 2026).
"""


if __name__ == "__main__":
    sys.exit(main())
