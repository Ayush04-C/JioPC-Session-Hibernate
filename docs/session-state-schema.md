# Session State Schema

**Status: FROZEN**
Any schema change needs both teammates to agree.

## Overview
This document defines the schema for `session-state.json`.

## Field Explanations

| Name | Type | Owner | Description | Example Value |
|---|---|---|---|---|
| `saved_at` | string | Daksh | ISO timestamp of when the session was captured. | `"2026-06-22T14:44:19+05:30"` |
| `windows` | array | Daksh | List of all captured application windows. | `[...]` |
| `window_id` | string | Daksh | The X11 Window ID (from wmctrl). | `"0x03a00003"` |
| `pid` | integer | Daksh | Process ID associated with the window. | `1234` |
| `executable` | string | Daksh | Path to the executable. | `"/usr/bin/google-chrome"` |
| `geometry` | object | Daksh | X, Y, Width, Height of the window. | `{"x": 0, "y": 0, "w": 800, "h": 600}` |
| `handler_name` | string | Ayush | Name of the matched handler. | `"chrome"` |
| `restore_supported` | boolean | Ayush | Whether the app can be reliably restored. | `true` |
| `restore_args` | array | Ayush | Command-line arguments for relaunch. | `["--restore-last-session"]` |

## Rules Daksh must follow when writing
1. Must capture all visible windows on the desktop.
2. Must populate `window_id`, `pid`, `executable`, and `geometry` before calling Ayush's enrichment method.
3. Must write valid JSON to `~/.local/share/jiopc/hibernate/session-state.json` with proper file locking/atomic moves.

## Rules Ayush must follow when reading
1. Must handle missing fields gracefully if a window was partially captured.
2. Must validate the `saved_at` timestamp for staleness.
3. Must skip launching windows where `restore_supported` is `false`.

## JSON Example

```json
{
  "saved_at": "2026-06-22T14:44:19+05:30",
  "windows": [
    {
      "window_id": "0x03a00003",
      "pid": 4512,
      "executable": "/usr/bin/google-chrome",
      "geometry": { "x": 0, "y": 0, "w": 1920, "h": 1080 },
      "handler_name": "chrome",
      "restore_supported": true,
      "restore_args": ["--restore-last-session"]
    },
    {
      "window_id": "0x03a00004",
      "pid": 5621,
      "executable": "/usr/bin/lxterminal",
      "geometry": { "x": 100, "y": 100, "w": 800, "h": 600 },
      "handler_name": "terminal",
      "restore_supported": true,
      "restore_args": ["--working-directory=/home/user/projects"]
    },
    {
      "window_id": "0x03a00005",
      "pid": 5890,
      "executable": "/usr/bin/pcmanfm-qt",
      "geometry": { "x": 200, "y": 200, "w": 800, "h": 600 },
      "handler_name": "filemanager",
      "restore_supported": true,
      "restore_args": ["-d", "/home/user/Downloads"]
    },
    {
      "window_id": "0x03a00006",
      "pid": 6012,
      "executable": "/usr/bin/soffice.bin",
      "geometry": { "x": 50, "y": 50, "w": 1280, "h": 720 },
      "handler_name": "libreoffice",
      "restore_supported": true,
      "restore_args": ["/home/user/Documents/report.odt"]
    }
  ]
}
```
