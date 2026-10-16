# pin

Stop a jailbroken PS5 from updating its firmware.

## Requirements

- Python 3.8+ on your computer (no packages needed)
- The console jailbroken, with the **shsrv** payload loaded (port 2323)
- The PS5's IP address: Settings > Network > Connection Status

## Usage

Run these from the repo root. Replace `192.168.1.42` with your PS5's IP.

```bash
# Preview, changes nothing
python3 pin/ps5-fw-pin.py --host 192.168.1.42 --dry-run

# Pin (default mode is --floor)
python3 pin/ps5-fw-pin.py --host 192.168.1.42

# Stronger pin, if `ls /dev/nfs` works in your shell
python3 pin/ps5-fw-pin.py --host 192.168.1.42 --full

# shsrv on a different port
python3 pin/ps5-fw-pin.py --host 192.168.1.42 --port 2324
```

## The two modes

### `--floor` (default)

1. Reads the firmware version. If it's 14.x, stops without changing anything.
2. Deletes any downloaded update waiting in `/update/PS5UPDATE.PUP`.
3. Checks `/update` is clean and fails loudly if it isn't.

Pair it with one console setting, done once:

Settings > System > System Software and Updates > Automatic Downloads >
System Software and Apps > **Off**

With nothing downloaded and auto-downloads off, the console can't install an
update on its own. The most you'll see is a prompt, which you dismiss with ✕.

### `--full`: block the update servers

Does everything `--floor` does, then adds two lines to the console's real
`/etc/hosts` so `update.playstation.com` and `dl.playstation.com` point at
`127.0.0.1`. The update check can't reach Sony, so you don't get a prompt at
all. The original is backed up next to it as `hosts.fwpin.bak` first.

This needs `/dev/nfs` in your jailbreak shell, which the **kstuff app** or a
recent **etaHEN** (kfs) creates. The old `kstuff-lite` payload does not. If
`ls /dev/nfs` fails, use `--floor`; it still protects you.

## Undo the pin

When your exploit supports the newer firmware and you want to update:

```bash
python3 pin/ps5-fw-unpin.py --host 192.168.1.42
```

This restores `/etc/hosts` from the backup if `--full` was used. Then turn
Automatic Downloads back on in Settings. `--floor` doesn't leave anything
behind on the console, so the setting is the only thing to undo.

## What this doesn't do

- It doesn't touch your games, saves, or the jailbreak.
- It can't help once a real install has started. It stops the console from
  getting that far.
- It runs once. If the console downloads a new update later (for example
  because auto-downloads got turned back on), run it again.

## Files

| File | What it does |
|---|---|
| `ps5-fw-pin.py` | Pin: `--floor` or `--full`, plus `--dry-run` |
| `ps5-fw-unpin.py` | Undo `--full`: restore `/etc/hosts` from the backup |
| `ps5shell.py` | Small client for the shsrv shell, used by both scripts |
