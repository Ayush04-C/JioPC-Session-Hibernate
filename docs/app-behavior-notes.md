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