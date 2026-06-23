#!/usr/bin/env python3
import sys
import os
import subprocess
import logging

LOG_PATH = os.path.expanduser("~/.local/share/jiopc/hibernate/trigger.log")

def main():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    
    with open(LOG_PATH, "a") as f:
        f.write("Save trigger daemon started. Monitoring DBus for LXQt pre-logout...\n")
        
    # Listen to all signals on the session bus. We use dbus-monitor because 
    # it doesn't crash if a specific destination isn't perfectly matched.
    process = subprocess.Popen(
        ["stdbuf", "-oL", "dbus-monitor", "type='signal'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    try:
        for line in iter(process.stdout.readline, ''):
            if "AboutToLeave" in line or "Logout" in line:
                with open(LOG_PATH, "a") as f:
                    f.write("Caught DBus pre-logout signal. Running capture synchronously...\n")
                
                # Execute the capture script BEFORE the session tears down
                subprocess.run(
                    ["python3", "-m", "save.save_service"], 
                    cwd="/usr/lib/jiopc-hibernate", 
                    timeout=5
                )
                
                with open(LOG_PATH, "a") as f:
                    f.write("Pre-logout capture completed successfully.\n")
                
                # Break to allow the script to exit gracefully
                break
                
    except Exception as e:
        with open(LOG_PATH, "a") as f:
            f.write(f"Daemon crashed: {e}\n")
    finally:
        process.terminate()

if __name__ == "__main__":
    main()
