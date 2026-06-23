"""Shared constants for the save pipeline.

This module contains configuration values, command definitions, and other
constants used throughout the session capture process.
"""

import os

# Command to discover open windows
WMCTRL_COMMAND = ("wmctrl", "-lG")

# Command to get the PID of a specific window
XDOTOOL_GET_PID_COMMAND = ("xdotool", "getwindowpid")

# Root directory for the proc filesystem
PROC_ROOT = "/proc"

# Schema version for the session-state.json
SCHEMA_VERSION = "1.0"

# Default trigger reason for session save
DEFAULT_TRIGGER = "user_disconnect"

# Directory where session files are stored
SESSION_DIRECTORY = os.path.expanduser("~/.local/share/jiopc/hibernate")

# Default filename for saving the session state
SESSION_FILENAME = "session-state.json"

# Full path to the default session file
DEFAULT_SESSION_PATH = os.path.join(SESSION_DIRECTORY, SESSION_FILENAME)

# Default name for the logger used in the save pipeline
DEFAULT_LOGGER_NAME = "save_pipeline"
