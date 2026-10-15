#!/usr/bin/env python3
"""
ps5-fw-downgrade — install a specific PS5 firmware from a PUP file.

Downloads a firmware PUP, verifies it, and prepares it for USB installation.
After the console installs it, this prints the re-jailbreak checklist.

PS5 downgrades work while Sony's keyset 0 is active (as of Oct 2026 it is —
no rollback lock has shipped). Any firmware change wipes the jailbreak:
you re-run your exploit and reload payloads afterward. Your games and saves
are not touched.

The official PUP lives at (pattern, region varies — if your region 404s,
try another or grab one from a PS5 homebrew mirror like PSXHAX):

  https://downloader.playstation.com/<europe|us|asia>/ps5os/<VERSION>/PS5UPDATE.PUP

Example — download the 13.60.007 file (for a downgrade from 14.x):

  python3 ps5-fw-downgrade.py 13.60.007 --region europe
  python3 ps5-fw-downgrade.py 13.60.007 --url https://mirror.example/PS5UPDATE.PUP

Verify a PUP you already have:

  python3 ps5-fw-downgrade.py --verify /path/to/PS5UPDATE.PUP

USB install (you do this, ~15 minutes):
  1. Format a USB stick as **exFAT** (or FAT32, PUPs fit under 4 GB)
  2. Make a folder `PS5` at the stick root, put PS5UPDATE.PUP inside:
         USB:/PS5/UPDATE/PS5UPDATE.PUP
     (the folder is literally named UPDATE)
  3. PS5: Settings > System > System Software and Updates >
         Install Update from USB Drive
  4. After install + reboot: re-jailbreak, reload payloads, done.

No dependencies — stdlib only (Python 3.8+).
"""

import argparse
import hashlib
import os
import sys
import time
import urllib.request

MIN_PUP_BYTES = 2 * 1024 * 1024 * 1024  # real PUPs are 2–7 GB; anything less is a stub/error page

REPOST_JAILBREAK = """
After the console reboots into the new firmware, the jailbreak is GONE
(firmware changes wipe it). Checklist:

  1. Run your exploit (Relapse: launch the Relapse Installer app)
  2. Load your payloads (ftpsrv, shsrv, ShadowMountPlus, whatever you run)
  3. ShadowMountPlus re-mounts your game dumps automatically — check the
     home screen for your apps
  4. Re-apply the firmware pin if you were using it:
         python3 ps5-fw-pin.py --floor
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
        return False, (f"only {size:,} bytes — a real PUP is 2-7 GB "
                       f"(this looks like a stub or an error page)")
    # PUPs start with a version header; first bytes must not be text/HTML
    with open(path, "rb") as f:
        head = f.read(64)
    if head[:4] in (b"HTTP", b"html", b"<!DO"):
        return False, "file starts with HTML — the server returned a web page, not the PUP"
    return True, f"{size:,} bytes"


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest):
    print(f"downloading {url}")
    print(f"          -> {dest}")
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    start = time.time()
    with urllib.request.urlopen(req, timeout=30) as r, open(tmp, "wb") as out:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(1 << 20)
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
    os.replace(tmp, dest)
    print(f"downloaded {os.path.getsize(dest):,} bytes in {time.time()-start:.0f}s")


def main():
    ap = argparse.ArgumentParser(description="Download and stage a PS5 firmware PUP for USB install.")
    ap.add_argument("version", nargs="?", help="firmware version, e.g. 13.60.007")
    ap.add_argument("--region", default="europe", choices=["europe", "us", "asia"],
                    help="Sony CDN region (default: europe)")
    ap.add_argument("--url", help="explicit PUP URL (overrides version/region)")
    ap.add_argument("--verify", metavar="PATH", help="verify an existing PUP and exit")
    ap.add_argument("--md5", action="store_true", help="print the MD5 of the PUP (cross-check vs mirrors)")
    ap.add_argument("-o", "--out", default="PS5UPDATE.PUP", help="output filename (default: PS5UPDATE.PUP)")
    args = ap.parse_args()

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
        ap.error("give a version (e.g. 13.60.007) or --url, or --verify PATH")

    dest = args.out
    if os.path.exists(dest):
        ok, reason = verify_pup(dest)
        if ok:
            print(f"{dest} already present and looks valid ({reason}). Skipping download.")
            if args.md5:
                print("md5:", md5_of(dest))
            print(usb_instructions(dest))
            return 0
        print(f"{dest} exists but fails the check ({reason}) — re-downloading to {dest}.part")
        dest = dest + ".new"

    try:
        download(url, dest)
    except Exception as e:
        print(f"\ndownload failed: {e}")
        print("If this is a 404, the region is wrong or the version has no direct CDN path —")
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
    print(REPOST_JAILBREAK)
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

NOTE: if the console complains the update is "older than the current
system software" — that's normal for a downgrade and the option still
installs it (keyset 0 is active as of Oct 2026).
"""


if __name__ == "__main__":
    sys.exit(main())
