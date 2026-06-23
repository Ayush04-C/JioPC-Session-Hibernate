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
        # The Problem Statement explicitly recommends using notify-send for this prompt
        cmd = [
            "notify-send",
            "--urgency=critical",
            "--action=yes=Restore",
            "--action=no=Dismiss",
            "JioPC Session Restore",
            f"Restore your previous session?\nSaved: {saved_at_str}\nApps: {window_count}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # notify-send outputs the chosen action key (e.g. "yes")
        if result.stdout.strip() == "yes":
            return True
        elif result.stdout.strip() == "no":
            return False
            
        # If notify-send didn't block or return an action, fallback to zenity
        zenity_cmd = [
            "zenity", "--question",
            "--title=JioPC Session Restore",
            f"--text=Restore your previous session?\n\nSaved: {saved_at_str}\nApps: {window_count}",
            "--ok-label=Restore",
            "--cancel-label=Dismiss",
            "--width=400"
        ]
        zenity_result = subprocess.run(zenity_cmd, capture_output=True)
        return zenity_result.returncode == 0
    except Exception as e:
        logging.warning(f"Error showing dialog: {e}")
        return False

def _restore_geometry(app_name: str, geometry: dict) -> None:
    if not geometry or not app_name:
        return
        
    try:
        x = geometry.get("x", 0)
        y = geometry.get("y", 0)
        w = geometry.get("width", 800)
        h = geometry.get("height", 600)
        
        geom_str = f"0,{x},{y},{w},{h}"
        cmd = ["wmctrl", "-r", app_name, "-e", geom_str]
        
        time.sleep(GEOMETRY_DELAY_SECONDS)
        subprocess.run(cmd, capture_output=True)
    except Exception as e:
        logging.warning(f"Geometry restore failed for '{app_name}': {e}")

def _relaunch_app(window: dict) -> bool:
    try:
        exec_path = window.get("exec")
        if not exec_path:
            logging.error("No executable path found for window")
            return False
            
        handler = window.get("handler")
        restore_args = window.get("restore_args", [])
        
        if handler is None:
            cmdline = window.get("cmdline", [])
            if len(cmdline) > 1:
                cmd = [exec_path] + cmdline[1:]
            else:
                cmd = [exec_path]
        else:
            cmd = [exec_path] + restore_args
            
        logging.info(f"Relaunching: {' '.join(cmd)}")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        
        _restore_geometry(window.get("app_name"), window.get("geometry"))
        return True
    except Exception as e:
        logging.error(f"Failed to relaunch app {window.get('exec')}: {e}")
        return False

def _rename_state_file() -> None:
    try:
        if SESSION_STATE_PATH.exists():
            SESSION_STATE_PATH.rename(SESSION_STATE_LAST_PATH)
    except Exception as e:
        logging.error(f"Failed to rename state file: {e}")

def _write_restored_count(count: int) -> None:
    try:
        if not SESSION_STATE_PATH.exists():
            return
            
        with open(SESSION_STATE_PATH, 'r') as f:
            data = json.load(f)
            
        if "meta" not in data:
            data["meta"] = {}
        data["meta"]["restored_count"] = count
        
        with open(SESSION_STATE_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to update restored_count: {e}")

def main() -> None:
    logging.info("Step 1: Waiting for desktop to load...")
    time.sleep(DESKTOP_WAIT_SECONDS)
    
    if not SESSION_STATE_PATH.exists():
        logging.info("No session state found, nothing to restore")
        sys.exit(0)
        
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
    
    if _is_stale(saved_at):
        logging.info("Session state is stale, discarding silently")
        try:
            SESSION_STATE_PATH.unlink()
        except Exception as e:
            logging.error(f"Failed to delete stale state file: {e}")
        sys.exit(0)
        
    confirmed = _show_restore_dialog(saved_at, len(windows))
    if not confirmed:
        _rename_state_file()
        sys.exit(0)
        
    restored_count = 0
    unsaved_apps = []
    
    for window in windows:
        try:
            success = _relaunch_app(window)
            if success:
                restored_count += 1
            if window.get("has_unsaved"):
                app_name = window.get("app_name") or window.get("exec", "Unknown")
                unsaved_apps.append(app_name)
        except Exception as e:
            logging.error(f"Critical per-app error: {e}")
            
    _write_restored_count(restored_count)
    _rename_state_file()
    logging.info(f"Restore complete: {restored_count} of {len(windows)} apps relaunched")
    
    if unsaved_apps:
        try:
            apps_str = ", ".join(unsaved_apps)
            cmd = ["notify-send", "JioPC Restore", f"Note: some apps had unsaved work: {apps_str}"]
            subprocess.run(cmd, capture_output=True)
        except Exception as e:
            logging.error(f"Failed to send unsaved apps notification: {e}")

if __name__ == "__main__":
    main()
