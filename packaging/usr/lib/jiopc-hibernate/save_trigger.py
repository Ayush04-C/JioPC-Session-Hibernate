#!/usr/bin/env python3
import signal
import sys
import subprocess
import time
import logging
import os

LOG_PATH = os.path.expanduser("~/.local/share/jiopc/hibernate/trigger.log")

def handle_sigterm(signum, frame):
    with open(LOG_PATH, "a") as f:
        f.write("Caught SIGTERM from LXQt session teardown. Running capture...\n")
    
    # Run the save service instantly before X11 dies
    try:
        subprocess.run(["python3", "-m", "save.save_service"], cwd="/usr/lib/jiopc-hibernate", timeout=5)
        with open(LOG_PATH, "a") as f:
            f.write("Capture completed successfully.\n")
    except Exception as e:
        with open(LOG_PATH, "a") as f:
            f.write(f"Capture failed: {e}\n")
            
    sys.exit(0)

def main():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write("Save trigger daemon started. Waiting for LXQt SIGTERM...\n")
        
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Sleep endlessly
    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()
