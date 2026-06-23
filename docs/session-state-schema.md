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