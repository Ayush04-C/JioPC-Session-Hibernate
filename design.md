# System Design

## Problem Statement

JioPC operates as a Desktop-as-a-Service platform utilizing dynamic virtual machine allocation. When a user logs in, they are assigned a random Ubuntu VM from a massive pool. While user data is preserved by mounting their `/home/user` directory via NFS, the actual compute state (running processes, X11 windows, GUI applications) is instantly destroyed whenever a user disconnects or hits an inactivity timeout.

This architecture creates severe workflow friction. A user researching in Chrome with multiple tabs open, while running a compilation in an LXTerminal, loses their entire workspace just by closing their laptop or experiencing a network drop. The JioPC Session Hibernate project was designed to completely eliminate this friction by bridging the volatile memory state of one VM to the fresh boot state of another VM, utilizing the only persistent bridge available: the NFS home directory.

## Architecture

```text
                                           ┌──────────────────────┐
                                           │    NFS Home Drive    │
                                           │ ~/.local/share/jiopc │
                                           └──────────┬───────────┘
                                                      │
[VM 1: Disconnect]                                    │                        [VM 2: New Login]
┌─────────────────────────────────┐                   │                   ┌─────────────────────────────────┐
│ A. Session Hook                 │                   │                   │ E. XDG Autostart                │
│ (Logout / xss-lock)             │                   │                   │ (/etc/xdg/autostart/...)        │
│          │                      │                   │                   │          │                      │
│          ▼                      │             D. JSON State             │          ▼                      │
│ B. Window Capture               │                 File                  │ E. Restore Service              │
│ (wmctrl /proc/PID)              ├───────────────────►───────────────────┤ (restore_service.py)            │
│          │                      │                   │                   │          │                      │
│          ▼                      │                   │                   │          ▼                      │
│ C. Handler Registry             │                   │                   │ E. Zenity Dialog & App Relaunch │
│ (apply_handlers.py)             │                   │                   │ (subprocess.Popen, wmctrl)      │
└─────────────────────────────────┘                   │                   └─────────────────────────────────┘
                                                      │
```

## Component Design

### A. Session Hook
Hooks into the LXQt native logout sequence and `xss-lock` inactivity daemon. Designed to fire rapidly before processes are killed, providing a strict 10-second window for the capture mechanism to perform its work.

### B. Window Capture
Iterates over active X11 windows using `wmctrl -lG`. Instead of relying on unreliable X11 window properties, it maps windows to their underlying PIDs. It heavily interrogates the `/proc/PID` filesystem to pull the exact executable binary (`exe`), the full command array (`cmdline`), and the current working directory (`cwd`).

### C. Handler Registry
A centralized, configuration-driven enrichment engine (`handlers.yaml` + `apply_handlers.py`). Because mapping a raw binary path to a restorable command is highly application-specific, this registry allows the system to pattern-match executables (e.g., `.*google-chrome.*`) and intelligently apply strategies (`flag`, `cwd`, `cmdline_arg`). This abstraction ensures no code changes are required to support new applications in the future.

### D. JSON State Storage
The entire active state is serialized into a rigidly structured `session-state.json` file. Designed with forward-compatibility (`schema_version`), it separates required operational data (`restore_args`) from pure metadata (`hostname`, `save_duration_ms`).

### E. Restore Service
An autonomous daemon that wakes up on login. It validates the schema, aggressively checks for timestamp staleness (preventing 3-day-old sessions from suddenly opening), and uses a blocking Zenity dialog to request permission. Apps are relaunched entirely asynchronously via `subprocess.Popen` to ensure a single crashed app doesn't halt the pipeline.

## Technology Choices

- **Python 3**: Chosen for rapid iteration, excellent built-in JSON/Subprocess handling, and native presence on Ubuntu 24.04. Avoids the overhead of compiling binaries for the JioPC image.
- **wmctrl**: An ultra-lightweight X11 utility that reliably interacts with the LXQt window manager to extract window IDs, titles, and geometries.
- **zenity**: Native GTK dialog provider. It looks native in LXQt, requires zero Python UI dependencies, and executes cleanly from shell subprocesses.
- **XDG Autostart**: By placing a `.desktop` file in `/etc/xdg/autostart`, the service naturally integrates into the LXQt startup lifecycle without requiring complex `systemd` user services or fragile `cron` jobs.
- **YAML handler registry**: Human-readable and highly extensible. Allows non-developers to add support for new applications just by adding three lines of text.
- **JSON state file**: Native to Python, easily readable by any language, and universally safe for high-latency NFS writes without risking database file corruption.

## Constraints

- **No Root Access**: All logic during capture and restore must execute cleanly under standard user permissions.
- **No GPU**: Forced reliance on CPU-only rendering; no GPU-accelerated window managers or compositors can be assumed.
- **10-Second Time Limit**: The entire capture and save sequence must resolve in under 10 seconds before the VM forcibly unmounts the NFS drive.
- **Cross-VM Operation**: Absolutely no reliance on `/tmp`, `/var`, or local disk caching. Everything must flow through `/home/user`.
- **.deb Packaging**: Must package cleanly into a Debian installer for seamless integration into the JioPC Gold Image build process.

## Known Limitations

1. **Geometry Inconsistencies**: Restoring window geometries via `wmctrl` is best-effort. Drastic resolution changes between the old VM and the new VM will cause irregular window placement.
2. **Unsupported Applications**: Any application not explicitly mapped in `handlers.yaml` will launch cleanly, but its in-app state (like an unsaved text document in Mousepad) cannot be restored automatically.
3. **Staleness Deletion**: To prevent massive system stalls, sessions older than 24 hours are silently destroyed. Users returning after a weekend will not be able to restore Friday's session.
