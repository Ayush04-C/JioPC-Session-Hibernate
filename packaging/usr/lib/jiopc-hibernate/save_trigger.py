#!/usr/bin/env python3
import sys
import os
import subprocess

LOG_PATH = os.path.expanduser("~/.local/share/jiopc/hibernate/trigger.log")

def log_msg(msg):
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def main():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    log_msg("Save trigger daemon started. Monitoring DBus for LXQt pre-logout...")
        
    # Listen to all DBus traffic (including Method Calls, not just Signals)
    # because lxqt-leave might use a method call to trigger the logout.
    process = subprocess.Popen(
        ["stdbuf", "-oL", "dbus-monitor"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    try:
        for line in iter(process.stdout.readline, ''):
            line_lower = line.lower()
            if "abouttoleave" in line_lower or "member=logout" in line_lower:
                log_msg(f"Caught DBus pre-logout event! Line: {line.strip()}")
                log_msg("Running capture synchronously...")
                
                # Execute the capture script BEFORE the session tears down
                subprocess.run(
                    ["python3", "-m", "save.save_service"], 
                    cwd="/usr/lib/jiopc-hibernate", 
                    timeout=10
                )
                
                log_msg("Pre-logout capture completed successfully.")
                
                # Break to allow the script to exit gracefully
                break
                
    except Exception as e:
        log_msg(f"Daemon crashed: {e}")
    finally:
        process.terminate()

if __name__ == "__main__":
    main()
