# jiopc-session-hibernate
Cross-VM session restore system for JioPC Linux DaaS platform.

## Architecture

```text
[Disconnect Event] 
        │
        ▼
[Component A: Hook] ──► [Component B: Capture (wmctrl)] 
                                │
                                ▼
                       [Component C: Enrich] ◄──► [Handler Registry]
                                │
                                ▼
              [Component D: Write JSON to NFS]
                                │
                          (VM Destroyed)
                                │
                          (New VM Spawned)
                                │
                                ▼
[Component E: Restore Service (XDG Autostart)] ──► [Zenity Dialog]
                                │
                                ▼
                       [Relaunch Apps]
```

## Components
- **Component A (Session-end hook):** Captures disconnect event. (Owner: Daksh)
- **Component B (Window capture):** Gathers X11/wmctrl and process data. (Owner: Daksh)
- **Component C (Apply handlers):** Enriches raw data with restore instructions. (Owner: Ayush)
- **Component D (JSON writer):** Saves the final state to disk. (Owner: Daksh)
- **Component E (Restore service):** Prompts user and relaunches apps on login. (Owner: Ayush)

## Quick Start
*Placeholder instructions on how to start using the project.*

## Benchmark Results
| Test | Save Time | Restore Time | Success Rate |
|---|---|---|---|
| Chrome + Terminal | TBD | TBD | TBD |

## Known Limitations
*Placeholder for current edge cases and limitations.*
