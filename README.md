# JioPC Session Hibernate

A lightweight, cross-VM session capture and restore system designed for JioPC Desktop-as-a-Service, ensuring users never lose their workflow across VM reassignments.

## Architecture

```text
[User Disconnect] 
       │
       ▼
[Session Hook] ───► [Window Capture (wmctrl + /proc)] ───► [Handler Enrichment]
                                                                  │
                                                                  ▼
[New VM Login] ◄─── [NFS Home Directory] ◄─── [~/.local/.../session-state.json]
       │
       ▼
[XDG Autostart] ──► [Restore Service] ──► [Zenity Dialog] ──► [App Relaunch]
```

## Components

| Component | Description | Key Files |
|-----------|-------------|-----------|
| **A: Session Hook** | Hooks into LxQt logout and xss-lock inactivity triggers to initiate save. | `capture_and_apply_handlers.py` (Daksh) |
| **B: Window Capture** | Enumerates open windows via `wmctrl` and extracts executable paths/args via `/proc`. | `capture_and_apply_handlers.py` (Daksh) |
| **C: Handler Registry** | Matches apps to strategies and builds intelligent restore arguments. | `apply_handlers.py`, `handlers.yaml` (Ayush) |
| **D: State Storage** | Defines the JSON schema and saves the payload safely. | `session-state.json`, `docs/session-state-schema.md` |
| **E: Restore Service** | Checks staleness, prompts user, and executes non-blocking relaunches. | `restore_service.py`, `jiopc-restore.desktop` (Ayush) |

## Quick Start

```bash
# Build the package
dpkg-deb --build packaging/ jiopc-session-hibernate.deb

# Install
sudo dpkg -i jiopc-session-hibernate.deb
```
Log out and log back in, or test manually by running `python3 /usr/lib/jiopc-hibernate/restore_service.py`.

## How It Works

JioPC assigns users a random virtual machine from a pool every time they log in. While their `/home/user` directory persists across these machines via an NFS mount, all running applications and GUI state are typically lost on disconnect. This project bridges that gap by acting as a seamless bridge across VMs.

When a user disconnects or an inactivity timeout is reached, the capture hook instantly enumerates all running X11 windows using `wmctrl`. It inspects the `/proc` filesystem to grab absolute execution paths, command-line arguments, and current working directories for each window. This data is passed through our Handler Registry, which dynamically builds specific flags to restore in-app state, writing the final payload to a JSON file on the persisted NFS drive.

Upon logging into a new JioPC VM, the LxQt desktop environment triggers an XDG autostart entry. Our restore service wakes up, checks the JSON file for staleness (default 24 hours), and prompts the user with a native Zenity dialog. If approved, the service rapidly relaunches all applications non-blockingly, attempting to restore window geometry, tabs, directories, and documents.

## Supported Apps

| App | Restore Type | What Gets Restored |
|-----|--------------|--------------------|
| **Google Chrome** | Flag (`--restore-last-session`) | Full tab history and active session |
| **LXTerminal** | CWD (`--working-directory=`) | The exact terminal working directory |
| **PCManFM-Qt** | Argument (`<path>`) | The active folder being viewed |
| **LibreOffice** | Argument (`<path>`) | The active document being edited |
| *(Any other app)* | Generic (`exec` + `cmdline`) | Relaunched fresh at default state |

## Benchmark Results

| Test | Save Time | Restore Time | Apps Restored | Success Rate |
|------|-----------|--------------|---------------|--------------|
| *Placeholder* | *TBD* | *TBD* | *TBD* | *TBD* |

## Known Limitations

1. **Resolution Mismatches**: Window geometry restoration (`wmctrl`) is best-effort. If the user logs into a VM with a smaller monitor resolution than the saved session, windows may render off-screen or resize unpredictably.
2. **Generic Applications**: Applications without an explicitly defined handler in `handlers.yaml` are relaunched from a fresh state using their base executable; internal states (like unsaved text in Mousepad) cannot be restored.
3. **Staleness Window**: Sessions older than 24 hours are automatically discarded silently to prevent launching deeply outdated environments.

[GitHub Repository: Ayush04-C/jiopc-session-hibernate](https://github.com/Ayush04-C/jiopc-session-hibernate)
