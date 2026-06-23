"""Shared constants for the save pipeline.

This module contains configuration values, command definitions, and other
constants used throughout the session capture process.
"""

# Command to discover open windows
WMCTRL_COMMAND = ("wmctrl", "-lG")

# Command to get the PID of a specific window
XDOTOOL_GET_PID_COMMAND = ("xdotool", "getwindowpid")

# Root directory for the proc filesystem
PROC_ROOT = "/proc"

# Default filename for saving the session state
SESSION_FILENAME = "session-state.json"

# Default name for the logger used in the save pipeline
DEFAULT_LOGGER_NAME = "save_pipeline"
