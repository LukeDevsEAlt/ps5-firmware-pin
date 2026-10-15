# ps5-firmware-pin

Keep a jailbroken PS5 on the firmware you want. No more "the PS5 needs an
update before it can be turned on" at the worst possible moment.

Tested on **fw 13.60.007** (Relapse jailbreak). The point: stay on a
jailbreak-supported version until the exploit adds the next one — 14.00+
currently breaks Relapse.

## Why you need this

Relapse (and the PS5 jailbreak scene in general) only works on specific
firmware. The moment Sony ships a version the exploit doesn't support, the
console will want to update — and a *forced* update screen can't be dismissed
with a button press. If the console downloads the update and tries to install
it, you lose the jailbreak (and, for some tools, your dumped games until you
re-jailbreak).

This tool makes sure the console **never has an update staged to install**,
and (optionally) can't even **see** that one exists.

## What it does — two modes

### `--floor` (safe, default, always works)

- Checks the firmware version and **refuses to continue if it reads 14.x**
  (you'd want to check the exploit's supported list first)
- Deletes any pending `PS5UPDATE.PUP` from `/update`
- Verifies `/update` is clean

Pair it with **one console setting** (5 seconds, you do this once):

> Settings → System → System Software and Updates →
> **Automatic Downloads** → System Software and Apps → **Off**

That's the whole protection. No background download, nothing staged, and the
only thing left is a prompt screen — press **X** to dismiss. If you ever hit
the full-screen "must update to boot" (rare, only after a download landed),
**hold the console's power button 10 seconds** to skip it.

### `--full` (stronger, needs a kernel-filesystem mount)

Does everything `--floor` does, **plus** pins the real `/etc/hosts` so
`update.playstation.com` resolves to `127.0.0.1` — the update checker
connects to itself and finds nothing. No prompt at all.

This needs `/dev/nfs` to exist in your jailbreak shell. That's created by the
**kstuff app** or a modern **etaHEN** kfs mount — *not* by the old `kstuff-lite`
payload (that's the FW 6–10 build). If `ls /dev/nfs` works in your shell,
`--full` works. If not, `--floor` still fully protects you.

Add `--strict` in full mode to also leave a **corrupted PUP** on disk, so if
the console *ever* tries to install a 14.x, signature verification fails
cleanly and it reboots to your current firmware.

## Quick start

You need the jailbreak active with the **shsrv** payload loaded (the telnet
shell, port 2323).

```bash
# 1. The safe floor — verify fw, delete any pending update, confirm clean
python3 ps5-fw-pin.py --floor

# 2. See what it would do without changing anything
python3 ps5-fw-pin.py --floor --dry-run

# 3. If you have /dev/nfs (kstuff app / etaHEN kfs), the strong pin
python3 ps5-fw-pin.py --full
python3 ps5-fw-pin.py --full --strict   # + the corrupted-PUP tripwire

# Reverse it when you're ready to update (day the exploit supports 14.x)
python3 ps5-fw-unpin.py
```

Custom IP/port if yours differs:

```bash
python3 ps5-fw-pin.py --host 192.168.1.50 --port 2323 --floor
```

No dependencies — stdlib only (Python 3.8+).

## The one rule to remember

**The ✕ on the update screen is the only update button on the console.**
Press ✕ to dismiss. Never press the "Update" / confirm button. If you're ever
caught on a screen that won't let you back out, the physical **power button
held for 10 seconds** always wins.

## Downgrading (e.g. 14.00 → 13.60)

The pin keeps you from *needing* this, but if you ended up on an
unsupported version, you can go back — while Sony's keyset 0 is active
(as of Oct 2026, no rollback lock has shipped). Any firmware change is an
official PUP install over USB; it wipes the jailbreak, not your games or
saves.

```bash
# Download the firmware you want (official Sony CDN, region varies)
python3 ps5-fw-downgrade.py 13.60.007 --region europe

# Explicit mirror URL if your region 404s (e.g. PSXHAX)
python3 ps5-fw-downgrade.py --url https://mirror.example/PS5UPDATE.PUP

# Check a PUP you already have
python3 ps5-fw-downgrade.py --verify /path/to/PS5UPDATE.PUP
```

Then the console does the rest:

1. USB stick (exFAT or FAT32), file at **`PS5/UPDATE/PS5UPDATE.PUP`** on the
   stick root
2. PS5: Settings → System → System Software and Updates →
   **Install Update from USB Drive**
3. After reboot, **re-jailbreak** (run your exploit, reload payloads).
   ShadowMount-style tools re-mount game dumps automatically

An "older than current system software" warning on the install screen is
normal for a downgrade — proceed anyway.

## What this is NOT

- Not a brick-proof against *everything*. A power cut mid-real-install is
  still a power cut mid-real-install. This prevents the console from
  *reaching* that point.
- The pin doesn't touch your games, saves, or the jailbreak itself.
  (Downgrading wipes the jailbreak but keeps games and saves.)

## Files

| File | What it does |
|---|---|
| `ps5-fw-pin.py` | Pin: `--floor` (safe) or `--full` (hosts), `--dry-run`, `--strict`, fw gate |
| `ps5-fw-unpin.py` | Restore: put `/etc/hosts` back, remove tripwire PUP |
| `ps5-fw-downgrade.py` | Download + verify a PUP, stage USB install, print re-jailbreak checklist |
