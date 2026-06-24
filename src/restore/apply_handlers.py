#!/usr/bin/env python3
"""
Component C: Handler Registry & Per-App Logic
Owner: Ayush

This module enriches raw window data with application-specific restore instructions
based on predefined handler configurations.
"""

import os
import sys
import re
import yaml
import logging
from pathlib import Path

# ==========================================
# CONFIG
# ==========================================
HANDLERS_CONFIG_PATH = "/usr/lib/jiopc-hibernate/handlers/handlers.yaml"
DEV_HANDLERS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "handlers", "handlers.yaml")
LOG_PATH = os.path.expanduser("~/.local/share/jiopc/hibernate/apply_handlers.log")

# ==========================================
# LOGGING SETUP
# ==========================================
# Ensure directory exists before setting up FileHandler
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)

def _load_handlers() -> list:
    """
    Loads handlers.yaml. Tries HANDLERS_CONFIG_PATH first, falls back to DEV_HANDLERS_PATH.
    Returns an empty list if neither exists and logs an error.
    """
    path_to_load = None
    if os.path.exists(HANDLERS_CONFIG_PATH):
        path_to_load = HANDLERS_CONFIG_PATH
    elif os.path.exists(DEV_HANDLERS_PATH):
        path_to_load = DEV_HANDLERS_PATH
        
    if not path_to_load:
        logging.error("Handler configuration file not found at either CONFIG or DEV paths.")
        return []
        
    try:
        with open(path_to_load, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('handlers', [])
    except Exception as e:
        logging.error(f"Failed to load handlers from {path_to_load}: {e}")
        return []

def _match_handler(exec_path: str, handlers: list) -> dict | None:
    """
    Iterates handlers and uses re.search() to find the first match against exec_path.
    """
    if not exec_path:
        return None
        
    for handler in handlers:
        pattern = handler.get('match_pattern', '')
        if pattern and re.search(pattern, exec_path):
            return handler
            
    return None

def _get_shell_cwd(terminal_pid: int | None) -> str | None:
    """
    Given a terminal emulator's PID, find its child shell process
    and return that shell's current working directory.
    """
    if terminal_pid is None:
        return None
        
    try:
        import subprocess
        result = subprocess.run(['pgrep', '-P', str(terminal_pid)], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            child_pids = result.stdout.strip().split('\n')
            for child_pid in child_pids:
                try:
                    cwd = os.readlink(f"/proc/{child_pid}/cwd")
                    if cwd:
                        return cwd
                except Exception:
                    continue
    except Exception as e:
        logging.warning(f"Error finding child shell cwd for PID {terminal_pid}: {e}")
        
    return None

def _get_libreoffice_doc_path(window_title: str) -> str | None:
    """
    Extract the document path from a LibreOffice window title.
    LibreOffice window title format: "filename.odt - LibreOffice Writer"
    or "filename.ods - LibreOffice Calc" etc.
    """
    if not window_title:
        return None
        
    try:
        if " - LibreOffice" in window_title:
            filename = window_title.split(" - LibreOffice")[0].strip()
            if not filename:
                return None
                
            import subprocess
            result = subprocess.run(
                ["find", "/home/user", "-name", filename, "-type", "f", "-maxdepth", "5"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    return lines[0]
                    
    except Exception as e:
        logging.warning(f"Error finding LibreOffice document for title '{window_title}': {e}")
        
    return None

def _build_restore_args(handler: dict, window: dict) -> list[str]:
    """
    Implements the logic to extract restore arguments based on restore_strategy.
    Never raises an exception — returns [] on any error and logs a warning.
    """
    try:
        strategy = handler.get('restore_strategy')
        
        if strategy == 'flag':
            flag = handler.get('restore_flag', '')
            return flag.split() if flag else []
            
        elif strategy == 'cwd':
            cwd = window.get('cwd')
            if cwd is not None:
                return [f"--working-directory={cwd}"]
            return []
            
        elif strategy == 'shell_cwd':
            pid = window.get('pid')
            cwd = _get_shell_cwd(pid)
            if cwd is None:
                cwd = window.get('cwd')
            if cwd is not None:
                flag = handler.get('restore_flag', '')
                if '{shell_cwd}' in flag:
                    if " " in flag:
                        arg, var = flag.split(" ", 1)
                        return [arg, var.replace('{shell_cwd}', cwd)]
                    else:
                        return [flag.replace('{shell_cwd}', cwd)]
                else:
                    return [f"--working-directory={cwd}"]
            logging.warning(f"Both shell cwd and fallback cwd were None for handler '{handler.get('name')}'.")
            return []
            
        elif strategy == 'cwd_arg':
            cwd = window.get('cwd')
            if cwd is not None:
                return [cwd]
            return []
            
        elif strategy == 'cmdline_arg':
            cmdline = window.get('cmdline', [])
            if cmdline and isinstance(cmdline, list) and len(cmdline) > 1:
                return [cmdline[1]]
            return []
            
        elif strategy == 'window_title_search':
            app_name = window.get('app_name', '')
            doc_path = _get_libreoffice_doc_path(app_name)
            if doc_path:
                return [doc_path]
            logging.warning(f"LibreOffice document path could not be determined for '{app_name}'.")
            window['restore_supported'] = False
            return []
            
        else:
            logging.warning(f"Unknown restore_strategy '{strategy}' for handler '{handler.get('name')}'.")
            return []
            
    except Exception as e:
        logging.warning(f"Error building restore args for handler '{handler.get('name')}': {e}")
        return []

def _apply_single_handler(window: dict, handlers: list) -> dict:
    """
    Returns a new dict without mutating the input. Applies matched handler data.
    """
    enriched = dict(window)
    
    handler = _match_handler(enriched.get('exec', ''), handlers)
    
    if handler:
        enriched['handler'] = handler.get('name')
        enriched['restore_supported'] = handler.get('restore_supported', False)
        enriched['restore_args'] = _build_restore_args(handler, enriched)
    else:
        enriched['handler'] = None
        enriched['restore_args'] = []
        enriched['restore_supported'] = False
        
    return enriched

def enrich_windows(raw_windows: list[dict]) -> list[dict]:
    """
    THE PUBLIC INTERFACE
    Loops through every window, applies the correct handler logic, and wraps
    everything in a try/except block to ensure safe processing.
    """
    handlers = _load_handlers()
    enriched_windows = []
    matched_count = 0
    
    for window in raw_windows:
        try:
            enriched = _apply_single_handler(window, handlers)
            enriched_windows.append(enriched)
            if enriched.get('handler') is not None:
                matched_count += 1
        except Exception as e:
            logging.error(f"Error processing window {window.get('win_id', 'unknown')}: {e}")
            safe_window = dict(window)
            safe_window['handler'] = None
            safe_window['restore_args'] = []
            safe_window['restore_supported'] = False
            enriched_windows.append(safe_window)
            
    logging.info(f"Enriched {len(enriched_windows)} windows, {matched_count} matched handlers.")
    return enriched_windows

