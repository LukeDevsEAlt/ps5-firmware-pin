# ps5-firmware-pin

Keep a jailbroken PS5 on the firmware you want — and get back if you end up
somewhere else.

Tested on **fw 13.60.007** (Relapse jailbreak). The problem it solves: Relapse
and the PS5 jailbreak scene only work on specific firmware. Sony ships a new
version, the console wants it, a forced update screen can't be dismissed, and
the jailbreak (and for some tools, the dumped games) is gone. These tools make
that a non-event.

## The full lifecycle

| Stage | Tool | What it does |
|---|---|---|
| **Stay put** | [`pin/`](pin/README.md) | Stop the console from downloading/staging updates so it can't force itself onto an unsupported version |
| **Go back** | [`downgrade/`](downgrade/README.md) | Download, verify, and install a specific firmware over USB (e.g. 14.00 → 13.60), then re-jailbreak |
| **Move on** | [`pin/ps5-fw-unpin.py`](pin/) | The day the exploit supports the next firmware, remove the pin and update normally |

Each folder is self-contained: one or two Python scripts (stdlib only, no
dependencies) + its own README with the full step-by-step.

```
ps5-firmware-pin/
├── pin/
│   ├── README.md
│   ├── ps5-fw-pin.py        # --floor (safe) / --full (hosts) / --dry-run / --strict
│   └── ps5-fw-unpin.py      # reverse of the pin
└── downgrade/
    ├── README.md
    └── ps5-fw-downgrade.py  # PUP download + verification + USB install guide
```

## TL;DR

```bash
# Protect a jailbroken console (needs shsrv payload loaded, port 2323)
python3 pin/ps5-fw-pin.py --floor

# One console setting, done once:
#   Settings > System > System Software and Updates >
#   Automatic Downloads > System Software and Apps > OFF

# If you ended up on 14.x, come home to 13.60:
python3 downgrade/ps5-fw-downgrade.py 13.60.007 --region europe
# → USB stick PS5/UPDATE/PS5UPDATE.PUP → Install Update from USB Drive
# → re-jailbreak → done (games and saves survive)
```

The one rule that matters: **the ✕ on the update screen is the only update
button on the console.** Never press confirm on it; if you're ever trapped on
a full-screen update, hold the physical power button for 10 seconds.
