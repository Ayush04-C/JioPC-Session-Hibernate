#!/usr/bin/env python3
"""
Component E: Restore Flow on Login
d
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

def _get_available_sessions():
    sessions = []
    paths = [
        SESSION_STATE_PATH,
        SESSION_STATE_PATH.with_name(SESSION_STATE_PATH.stem + "-1.json"),
        SESSION_STATE_PATH.with_name(SESSION_STATE_PATH.stem + "-2.json")
    ]
    for p in paths:
        if p.exists():
            try:
                with open(p, 'r') as f:
                    state = json.load(f)
                    if not _is_stale(state.get("saved_at", "")):
                        sessions.append((p, state))
            except Exception as e:
                logging.warning(f"Failed to load session file {p}: {e}")
    return sessions

def _show_restore_dialog(sessions):
    try:
        if not sessions:
            return None
            
        cmd = [
            "notify-send",
            "-a", "JioPC Restore",
            "--urgency=critical",
            "-t", "0",
            "-w"
        ]
        
        if len(sessions) == 1:
            state = sessions[0][1]
            apps = len(state.get("windows", []))
            saved_at = state.get("saved_at", "Unknown")
            body_text = f"Restore your previous session?\nSaved: {saved_at}\nApps: {apps}"
            cmd.extend([
                "--action=0=Restore", 
                "--action=dismiss=Skip",
                "JioPC Session Restore", body_text
            ])
        else:
            body_lines = ["Multiple saved sessions found. Which one would you like to restore?\n"]
            for i, (path, state) in enumerate(sessions):
                saved_at = state.get("saved_at", "Unknown")
                windows = state.get("windows", [])
                apps = len(windows)
                
                # Extract unique app names for the description
                app_names = []
                for w in windows:
                    name = w.get("app_name") or w.get("title") or "Unknown"
                    if name not in app_names:
                        app_names.append(name)
                        
                app_list = ", ".join(app_names)
                if len(app_list) > 40:
                    app_list = app_list[:37] + "..."
                
                try:
                    dt = datetime.fromisoformat(saved_at.replace("Z", "+00:00"))
                    formatted = dt.astimezone().strftime("%m-%d %H:%M")
                except:
                    formatted = saved_at
                    
                label = f"#{i+1}"
                cmd.append(f"--action={i}={label}")
                body_lines.append(f"• Option {i+1} [{formatted}]: {apps} apps ({app_list})")
                
            cmd.append("--action=dismiss=Skip")
            cmd.append("JioPC Session Restore")
            cmd.append("\n".join(body_lines))
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = result.stdout.strip()
        
        if out == "dismiss" or not out:
            return None
            
        try:
            idx = int(out)
            return sessions[idx][0]
        except ValueError:
            return None
    except Exception as e:
        logging.warning(f"Error showing dialog: {e}")
        return None

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

def _write_restored_count(chosen_path, count):
    try:
        if not chosen_path.exists():
            return
            
        with open(chosen_path, 'r') as f:
            data = json.load(f)
            
        if "meta" not in data:
            data["meta"] = {}
        data["meta"]["restored_count"] = count
        
        with open(chosen_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to update restored_count: {e}")

def main() -> None:
    logging.info("Step 1: Waiting for desktop to load...")
    time.sleep(DESKTOP_WAIT_SECONDS)
    
    sessions = _get_available_sessions()
    if not sessions:
        logging.info("No valid session states found, nothing to restore")
        sys.exit(0)
        
    chosen_path = _show_restore_dialog(sessions)
    if not chosen_path:
        sys.exit(0)
        
    try:
        with open(chosen_path, 'r') as f:
            state = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read chosen session state JSON: {e}")
        sys.exit(1)
        
    schema_version = state.get("schema_version")
    if schema_version != "1.0":
        logging.warning(f"Unsupported schema_version: {schema_version}, continuing anyway.")
        
    windows = state.get("windows", [])
        
    restored_apps = []
    failed_apps = []
    unsaved_apps = []
    
    for window in windows:
        exec_path = window.get("exec")
        if exec_path:
            app_name = os.path.basename(exec_path).capitalize()
        else:
            app_name = window.get("app_name") or window.get("title") or "Unknown App"
            
        try:
            success = _relaunch_app(window)
            if success:
                restored_apps.append(app_name)
            else:
                failed_apps.append(app_name)
                
            if window.get("has_unsaved"):
                unsaved_apps.append(app_name)
        except Exception as e:
            logging.error(f"Critical per-app error: {e}")
            failed_apps.append(app_name)
            
    _write_restored_count(chosen_path, len(restored_apps))
    logging.info(f"Restore complete: {len(restored_apps)} of {len(windows)} apps relaunched")
    
    try:
        report_lines = []
        if restored_apps:
            unique_restored = sorted(list(set(restored_apps)))
            report_lines.append(f"Restored: {', '.join(unique_restored)}")
        if failed_apps:
            unique_failed = sorted(list(set(failed_apps)))
            report_lines.append(f"Failed: {', '.join(unique_failed)}")
        if unsaved_apps:
            unique_unsaved = sorted(list(set(unsaved_apps)))
            report_lines.append(f"Unsaved work: {', '.join(unique_unsaved)}")
            
        if report_lines:
            report_body = "\n".join(report_lines)
            cmd = ["notify-send", "-a", "JioPC Restore", "-t", "5000", "--urgency=normal", "Restore Summary", report_body]
            subprocess.run(cmd, capture_output=True)
    except Exception as e:
        logging.error(f"Failed to send restore summary notification: {e}")

if __name__ == "__main__":
    main()
