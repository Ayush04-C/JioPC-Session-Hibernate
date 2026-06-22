#!/usr/bin/env python3
"""
Component E: Restore Flow on Login
Owner: Ayush
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# ==========================================
# CONFIG
# ==========================================
SESSION_STATE_PATH = Path.home() / ".local/share/jiopc/hibernate/session-state.json"
SESSION_STATE_LAST_PATH = Path.home() / ".local/share/jiopc/hibernate/session-state-last.json"
STALENESS_HOURS = 24
DESKTOP_WAIT_SECONDS = 5
GEOMETRY_DELAY_SECONDS = 2
LOG_PATH = Path.home() / ".local/share/jiopc/hibernate/restore.log"

# ==========================================
# LOGGING SETUP
# ==========================================
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_PATH)),
        logging.StreamHandler(sys.stdout)
    ]
)

def _is_stale(saved_at_str: str) -> bool:
    try:
        time_str = saved_at_str.replace("Z", "+00:00")
        saved_at = datetime.fromisoformat(time_str)
        now = datetime.now(timezone.utc)
        diff_hours = (now - saved_at).total_seconds() / 3600
        return diff_hours > STALENESS_HOURS
    except Exception as e:
        logging.warning(f"Failed to parse saved_at '{saved_at_str}': {e}")
        return False

def _show_restore_dialog(saved_at_str: str, window_count: int) -> bool:
    try:
        cmd = [
            "zenity", "--question",
            "--title=JioPC Session Restore",
            f"--text=Restore your previous session?\n\nSaved: {saved_at_str}\nApps: {window_count}",
            "--ok-label=Restore",
            "--cancel-label=Dismiss",
            "--width=400"
        ]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        logging.warning("zenity not found, proceeding without confirmation.")
        return True
    except Exception as e:
        logging.warning(f"Error showing zenity dialog: {e}")
        return False

def _rename_state_file() -> None:
    try:
        if SESSION_STATE_PATH.exists():
            SESSION_STATE_PATH.rename(SESSION_STATE_LAST_PATH)
    except Exception as e:
        logging.error(f"Failed to rename state file: {e}")

def main() -> None:
    # Step 1
    logging.info("Step 1: Waiting for desktop to load...")
    time.sleep(DESKTOP_WAIT_SECONDS)
    
    # Step 2
    if not SESSION_STATE_PATH.exists():
        logging.info("No session state found, nothing to restore")
        sys.exit(0)
        
    # Step 3
    try:
        with open(SESSION_STATE_PATH, 'r') as f:
            state = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read session state JSON: {e}")
        sys.exit(1)
        
    schema_version = state.get("schema_version")
    if schema_version != "1.0":
        logging.warning(f"Unsupported schema_version: {schema_version}, continuing anyway.")
        
    saved_at = state.get("saved_at")
    if not saved_at:
        logging.error("Missing saved_at field in session state, cannot proceed safely.")
        sys.exit(1)
        
    windows = state.get("windows", [])
    
    # Step 4
    if _is_stale(saved_at):
        logging.info("Session state is stale, discarding silently")
        try:
            SESSION_STATE_PATH.unlink()
        except Exception as e:
            logging.error(f"Failed to delete stale state file: {e}")
        sys.exit(0)
        
    # Step 5
    confirmed = _show_restore_dialog(saved_at, len(windows))
    if not confirmed:
        _rename_state_file()
        sys.exit(0)

if __name__ == "__main__":
    main()
