#!/usr/bin/env python3
"""
Component C: Handler Registry & Per-App Logic
Owner: Ayush
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
    if not exec_path:
        return None
        
    for handler in handlers:
        pattern = handler.get('match_pattern', '')
        if pattern and re.search(pattern, exec_path):
            return handler
            
    return None
def _build_restore_args(handler: dict, window: dict) -> list[str]:
    try:
        strategy = handler.get('restore_strategy')
        
        if strategy == 'flag':
            flag = handler.get('restore_flag', '')
            return [flag] if flag else []
            
        elif strategy == 'cwd':
            cwd = window.get('cwd')
            if cwd is not None:
                return [f"--working-directory={cwd}"]
            return []
            
        elif strategy == 'cmdline_arg':
            cmdline = window.get('cmdline', [])
            if cmdline and isinstance(cmdline, list) and len(cmdline) > 1:
                return [cmdline[1]]
            return []
            
        else:
            logging.warning(f"Unknown restore_strategy '{strategy}'.")
            return []
            
    except Exception as e:
        logging.warning(f"Error building restore args: {e}")
        return []
