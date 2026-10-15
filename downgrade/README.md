# downgrade

Install a specific PS5 firmware (e.g. go back from 14.00 to 13.60) from a
PUP file, over USB.

## Can you downgrade a PS5?

Yes — **while Sony's keyset 0 is active** (as of Oct 2026, no rollback lock
has shipped). PS5 rollback protection works by Sony retiring the signing key
for older firmware; once that happens, downgrades below the locked version
stop working for everyone, forever. As long as keyset 0 is alive, any
official firmware PUP can be installed in either direction.

**What a firmware change does:**
- ❌ wipes the **jailbreak** (all payloads gone — re-run your exploit)
- ✅ keeps your **games and saves**
- ShadowMount-style tools re-mount game dumps automatically after re-jailbreak

## How it works, step by step

### 1. Get the PUP

```bash
# Official Sony CDN (region varies — try another if yours 404s)
python3 downgrade/ps5-fw-downgrade.py 13.60.007 --region europe

# Any mirror (e.g. PSXHAX) via explicit URL
python3 downgrade/ps5-fw-downgrade.py --url https://mirror.example/PS5UPDATE.PUP

# Already have a PUP? Verify it (size + header checks catch stubs
# and HTML error pages that fool naive downloaders)
python3 downgrade/ps5-fw-downgrade.py --verify /path/to/PS5UPDATE.PUP

# Cross-check a file against a mirror's published checksum
python3 downgrade/ps5-fw-downgrade.py --verify PS5UPDATE.PUP --md5
```

A real PUP is **2–7 GB**. If you get a file that's a few MB, it's a stub or
an error page — the `--verify` check will tell you.

### 2. Stage the USB stick

- Format the stick as **exFAT** (FAT32 also works — PUPs fit under 4 GB)
- Create this exact layout at the **stick root**:

```
PS5/
  UPDATE/
    PS5UPDATE.PUP
```

(The folder is literally named `UPDATE`, and the file must be named exactly
`PS5UPDATE.PUP` — rename it if the download gave it a different name.)

### 3. Install on the console

1. Plug the stick in, console **off**
2. PS5: Settings → System → System Software and Updates →
   **Install Update from USB Drive**
3. Let it install (~10 min) and reboot

If the console warns the update is *"older than the current system
software"* — that's **normal for a downgrade**, proceed anyway.

### 4. Re-jailbreak (the part everyone forgets)

The firmware install wiped the jailbreak. After reboot:

1. Run your exploit (Relapse: launch the Relapse Installer app)
2. Load your payloads (ftpsrv, shsrv, ShadowMountPlus, …)
3. Verify your game dumps are back on the home screen (ShadowMount re-mounts
   automatically; relaunch it if not)
4. Re-pin if you use it:
   ```bash
   python3 pin/ps5-fw-pin.py --floor
   ```
   …and flip **Automatic Downloads** back to **Off** in Settings.

## No-dependencies

Stdlib only, Python 3.8+. The script downloads with streaming (progress +
speed), verifies before you waste the USB step, and never overwrites a file
that already passes verification.
