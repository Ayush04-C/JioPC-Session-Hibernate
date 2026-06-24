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
# `session-state.json` Schema Contract

**Status: FROZEN (Version 1.0)**  
*This document represents the immutable contract between the capture hook and the restore service. Any field name or type changes require agreement from both teammates.*

## Complete JSON Example

Here is a full payload containing four supported applications (`chrome`, `terminal`, `filemanager`, `libreoffice`):

```json
{
  "schema_version": "1.0",
  "saved_at": "2026-06-22T10:30:00Z",
  "trigger": "user_disconnect",
  "save_duration_ms": 3421,
  "windows": [
    {
      "win_id": "0x04800003",
      "app_name": "Google Chrome",
      "exec": "/usr/bin/google-chrome",
      "cmdline": ["/usr/bin/google-chrome"],
      "handler": "chrome",
      "restore_args": ["--restore-last-session"],
      "geometry": {"x": 0, "y": 0, "width": 1280, "height": 720},
      "restore_supported": true,
      "cwd": "/home/user",
      "has_unsaved": false,
      "pid": 3821,
      "desktop": "0"
    },
    {
      "win_id": "0x03200001",
      "app_name": "LXTerminal",
      "exec": "/usr/bin/lxterminal",
      "cmdline": ["/usr/bin/lxterminal"],
      "handler": "terminal",
      "restore_args": ["--working-directory=/home/user/projects/jiopc"],
      "geometry": {"x": 100, "y": 100, "width": 800, "height": 500},
      "restore_supported": true,
      "cwd": "/home/user/projects/jiopc",
      "has_unsaved": false,
      "pid": 4102,
      "desktop": "0"
    },
    {
      "win_id": "0x05100002",
      "app_name": "PCManFM-Qt",
      "exec": "/usr/bin/pcmanfm-qt",
      "cmdline": ["/usr/bin/pcmanfm-qt"],
      "handler": "filemanager",
      "restore_args": ["/home/user/Documents"],
      "geometry": {"x": 200, "y": 150, "width": 900, "height": 600},
      "restore_supported": true,
      "cwd": "/home/user",
      "has_unsaved": false,
      "pid": 4230,
      "desktop": "0"
    },
    {
      "win_id": "0x06200004",
      "app_name": "design.md - libreoffice",
      "exec": "/usr/bin/libreoffice",
      "cmdline": ["/usr/bin/libreoffice", "/home/user/projects/jiopc/design.md"],
      "handler": "libreoffice",
      "restore_args": ["/home/user/projects/jiopc/design.md"],
      "geometry": {"x": 300, "y": 200, "width": 750, "height": 550},
      "restore_supported": true,
      "cwd": "/home/user/projects/jiopc",
      "has_unsaved": true,
      "pid": 4401,
      "desktop": "0"
    }
  ],
  "meta": {
    "total_windows": 4,
    "restored_count": null,
    "hostname": "jiopc-vm-07",
    "display": ":0"
  }
}
```

## Top-Level Fields

| Field | Type | Written by | Description | Example |
|-------|------|------------|-------------|---------|
| `schema_version` | string | Daksh | Version of this schema for forward compatibility. | `"1.0"` |
| `saved_at` | string | Daksh | ISO 8601 UTC timestamp of session capture. | `"2026-06-22T10:30:00Z"` |
| `trigger` | string | Daksh | Enum defining the event that initiated the save. | `"user_disconnect"` |
| `save_duration_ms` | integer | Daksh | Milliseconds taken to serialize the state. | `3421` |
| `windows` | array | Daksh/Ayush | List of captured X11 windows and handler enrichment. | `[...]` |
| `meta` | object | Daksh/Ayush | Metadata block for debugging and telemetry. | `{...}` |

## Per-Window Fields

| Field | Type | Written by | Description | Example |
|-------|------|------------|-------------|---------|
| `win_id` | string | Daksh | Hexadecimal X11 window ID. | `"0x04800003"` |
| `app_name` | string | Daksh | Human-readable window title from `wmctrl`. | `"Google Chrome"` |
| `exec` | string | Daksh | Absolute path to binary execution. | `"/usr/bin/google-chrome"` |
| `cmdline` | array | Daksh | Array of execution arguments from `/proc/PID/cmdline`. | `["/usr/bin/google-chrome"]` |
| `handler` | string | Ayush | Matched handler identifier. | `"chrome"` |
| `restore_args` | array | Ayush | Calculated CLI arguments for relaunching the app. | `["--restore-last-session"]` |
| `geometry` | object | Daksh | X11 bounding box definition. | `{...}` |
| `restore_supported` | boolean | Ayush | True if deep state is restorable via handler. | `true` |
| `cwd` | string | Daksh | Current working directory from `/proc/PID/cwd`. | `"/home/user"` |
| `has_unsaved` | boolean | Daksh | True if window title implies unsaved work (e.g. `*`). | `false` |
| `pid` | integer | Daksh | Process ID at the time of capture. | `3821` |
| `desktop` | string | Daksh | Virtual desktop ID. | `"0"` |

## Geometry Fields

| Field | Type | Written by | Description | Example |
|-------|------|------------|-------------|---------|
| `x` | integer | Daksh | X-coordinate of top-left corner | `0` |
| `y` | integer | Daksh | Y-coordinate of top-left corner | `0` |
| `width` | integer | Daksh | Width in pixels | `1280` |
| `height` | integer | Daksh | Height in pixels | `720` |

## Valid Enum Values

**`trigger`**
- `"user_disconnect"`
- `"inactivity_timeout"`

**`handler`**
- `"chrome"`
- `"terminal"`
- `"filemanager"`
- `"libreoffice"`
- `null`

## Rules for Capture Side (Writing)
1. `desktop == "-1"` → Skip that window entirely.
2. `exec` MUST always be an absolute path starting with `/`.
3. `saved_at` MUST always be UTC (appended with `Z`).
4. If `/proc/PID/cwd` is unreadable → write `null`, not an empty string.
5. If PID lookup fails → write `null` for both `pid` and `cwd`.
6. `save_duration_ms` is written last, immediately before syncing the file.

## Rules for Restore Side (Reading)
1. Always check `schema_version` first — warn if not `"1.0"` but attempt to continue gracefully.
2. Always check `saved_at` staleness before doing anything else (discard if > 24 hours).
3. If `handler` is `null` → still attempt relaunch using `exec` + `cmdline[1:]`.
4. If `restore_supported` is `false` → relaunch fresh, with no in-app state arguments.
5. If `has_unsaved` is `true` → include this app name in the final `notify-send` warning.
6. NEVER modify the file during restore execution — only rename to `session-state-last.json` when fully done.
7. Write `restored_count` into the renamed `session-state-last.json` after the restore sequence completes.
# Application State Restoration Experiments

This document records the experiments performed to determine how different applications can be restored after a session restart.

---

# Experiment 1 — Google Chrome

## 1. Session File Generation

### Action
Opened multiple tabs and closed Chrome cleanly using:

```
File → Exit
```

### Observation
Checking:

```bash
~/.config/google-chrome/Default/Sessions/
```

revealed newly created files prefixed with:

- `Session_`
- `Tabs_`

### Conclusion

Chrome successfully saves session information to disk, but the browser must exit cleanly. Forcefully killing the process may prevent session files from being written.

---

## 2. Session Restoration

### Question

Does `--restore-last-session` work?

### Result

Yes, but additional flags are required in our environment.

### Observation

Running:

```bash
google-chrome --restore-last-session
```

opened a blank tab instead of restoring the previous session.

Terminal logs showed GPU initialization failures:

```
Failed to send GpuControl.CreateCommandBuffer
```

indicating Chrome was crashing during startup before session restoration occurred.

### Working Command

```bash
google-chrome --no-sandbox --disable-gpu --restore-last-session
```

### Handler Logic Takeaway

Chrome session restoration is supported, but the launcher should use:

```bash
google-chrome --no-sandbox --disable-gpu --restore-last-session
```

to avoid environment-specific GPU and sandbox issues.

---

# Experiment 2 — LXTerminal

## 1. Working Directory Inspection

### Action

1. Opened LXTerminal.
2. Changed directory inside the shell:

```bash
cd ~/Documents
```

3. Examined:

```bash
/proc/PID/cwd
```

for the LXTerminal process.

### Observation

The symbolic link pointed to:

```text
/home/user
```

instead of:

```text
/home/user/Documents
```

which was the shell's current directory.

### Conclusion

`/proc/PID/cwd` represents the terminal emulator's startup directory rather than the shell's active directory.

Therefore, it is unreliable for restoring terminal state.

---

## 2. Argument Restore Test

### Question

What flag sets the startup directory?

### Result

```bash
--working-directory=DIRECTORY
```

### Observation

Running:

```bash
lxterminal --help
```

confirmed support for:

```bash
--working-directory
```

Example:

```bash
lxterminal --working-directory=/home/user/Documents
```

opens the terminal directly in that folder.

### Handler Logic Takeaway

Restoration is possible once the shell's current directory is known. Determining that directory requires inspecting the child shell process rather than the terminal process itself.

---

# Experiment 3 — PCManFM-Qt

## 1. Window Title Inspection

### Action

1. Opened PCManFM-Qt.
2. Navigated to `Documents`.
3. Queried window titles using:

```bash
wmctrl -l
```

### Observation

The window title dynamically changed to:

```
Documents
```

matching the currently open folder.

### Conclusion

The current directory can be inferred from the window title.

This avoids relying on process metadata.

---

## 2. Argument Restore Test

### Question

Does path-as-argument work?

### Result

Yes.

### Observation

Running:

```bash
pcmanfm-qt ~/Documents/
```

opens the file manager directly in that directory.

### Handler Logic Takeaway

State restoration is straightforward:

1. Extract the folder from the window title.
2. Relaunch:

```bash
pcmanfm-qt <saved-path>
```

---

# Experiment 4 — LibreOffice

## 1. Command-Line Inspection

### Question

Is the opened document path visible in the process command line?

### Result

No.

### Observation

When a document is created or opened from within an already-running LibreOffice instance, the document path does not appear in:

```bash
cat /proc/PID/cmdline
```

Example output:

```text
/usr/lib/libreoffice/program/soffice.bin --splash-pipe=5
```

Only the base executable and internal flags are present.

### Conclusion

The active document cannot be determined through process command-line inspection.

---

## 2. Argument Restore Test

### Question

Can a document be restored via command-line arguments?

### Result

Yes.

### Observation

Launching:

```bash
libreoffice /path/to/document.odt
```

opens the specified document successfully.

### Handler Logic Takeaway

Document restoration is supported, but recovering the currently open document requires another mechanism because the process metadata does not expose it.

---

# Experiment 5 — XDG Autostart

## 1. Global Autostart Execution

### Action

Created:

```text
/etc/xdg/autostart/test-notify.desktop
```

containing a simple command and re-logged into the LXQt session.

### Observation

The `.desktop` file was automatically executed during login, confirming that the XDG autostart mechanism functions correctly within the LXQt environment.

### Result

✅ Successful

### Conclusion

The system correctly reads and executes `.desktop` files placed in:

```text
/etc/xdg/autostart/
```

during user login.

---

## Handler Logic Takeaway

The XDG autostart mechanism can be used to automatically launch the application restoration service after a user logs in.

Example `.desktop` file:

```ini
[Desktop Entry]
Type=Application
Name=Session Restore Service
Exec=/path/to/restore_script.sh
X-GNOME-Autostart-enabled=true
```

Both global:

```text
/etc/xdg/autostart/
```

and user-specific:

```text
~/.config/autostart/
```

locations are suitable for registering the restore service.

---

# Summary

| Application | State Discovery | Restoration Method | Feasibility |
|-------------|----------------|-------------------|-------------|
| Google Chrome | Session files under `~/.config/google-chrome/Default/Sessions/` | `google-chrome --no-sandbox --disable-gpu --restore-last-session` | ✅ |
| LXTerminal | `/proc/PID/cwd` unreliable | `lxterminal --working-directory=<dir>` | ⚠ Requires shell inspection |
| PCManFM-Qt | Window title via `wmctrl` | `pcmanfm-qt <path>` | ✅ |
| LibreOffice | Active document not visible in cmdline | `libreoffice <document>` | ⚠ Need alternate document tracking |
| XDG Autostart | `.desktop` execution confirmed | Launch restore script on login | ✅ |

# Overall Conclusion

- Chrome supports session restoration through saved session files.
- PCManFM-Qt is straightforward to restore because its active directory can be inferred and passed as an argument.
- LXTerminal supports restoration, though discovering the shell's current directory requires deeper process inspection.
- LibreOffice can reopen documents when provided with a file path, but determining the currently open document requires an alternate tracking mechanism.
- XDG Autostart provides a reliable mechanism for automatically starting the session restoration service when the user logs in.
