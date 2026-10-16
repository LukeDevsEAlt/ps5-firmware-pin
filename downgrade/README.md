# downgrade

Install a specific PS5 firmware (for example go back from 14.00 to 13.60)
from a USB stick.

## Can you downgrade a PS5?

Yes, while Sony's **keyset 0** is still active. As of October 2026 no rollback
lock has shipped. When Sony retires a signing key, firmware signed with it
stops installing for everyone, permanently. Until then, any official firmware
file installs in either direction.

What changing firmware does:

- ❌ removes the **jailbreak** (you run your exploit again afterwards)
- ✅ keeps your **games and saves**
- ShadowMount-style tools re-mount game dumps once you re-jailbreak

## Step 1: Get the firmware file

The firmware comes as one file named `PS5UPDATE.PUP` (a "PUP"). Run from the
repo root:

```bash
# From Sony's servers. If your region gives a 404, try us or asia.
python3 downgrade/ps5-fw-downgrade.py 13.60.007 --region europe

# From any mirror (e.g. PSXHAX)
python3 downgrade/ps5-fw-downgrade.py --url https://mirror.example/PS5UPDATE.PUP

# Check a PUP you already have
python3 downgrade/ps5-fw-downgrade.py --verify /path/to/PS5UPDATE.PUP

# Print its MD5 to compare with the checksum a mirror publishes
python3 downgrade/ps5-fw-downgrade.py --verify /path/to/PS5UPDATE.PUP --md5
```

A real PUP is **2 to 7 GB**. If you get a file of a few KB or MB, it's an error
page, not firmware, and `--verify` says so. The download saves to
`PS5UPDATE.PUP` in the current folder (change it with `-o`).

## Step 2: Prepare the USB stick

1. Format the stick as **exFAT** (FAT32 also works).
2. Create this layout at the root of the stick:

   ```
   PS5/
     UPDATE/
       PS5UPDATE.PUP
   ```

   Folder names are in capitals, and the file must be named exactly
   `PS5UPDATE.PUP`. Rename it if it came with a different name.

## Step 3: Install it on the console

1. Plug the stick into the PS5.
2. Settings > System > System Software and Updates > **Install Update from
   USB Drive**.
3. Wait for it to install and reboot (about 10 minutes). Don't turn the
   console off while it installs.

If the console warns that the update is *"older than the current system
software"*, that's expected for a downgrade. Go ahead.

## Step 4: Jailbreak again

The firmware change removed the jailbreak. After the reboot:

1. Run your exploit (Relapse: open the Relapse Installer app).
2. Load your payloads (ftpsrv, shsrv, ShadowMountPlus, ...).
3. Check your game dumps are back on the home screen. ShadowMount re-mounts
   them; relaunch it if they're missing.
4. Pin the firmware so this doesn't happen again:

   ```bash
   python3 pin/ps5-fw-pin.py --host 192.168.1.42
   ```

   and set **Automatic Downloads** to **Off** in Settings. See
   [pin/README.md](../pin/README.md).
