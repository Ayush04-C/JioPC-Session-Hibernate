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
