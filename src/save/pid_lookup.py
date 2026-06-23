"""PID lookup module for the save pipeline.

This module provides functionality to determine the Process ID (PID)
associated with a specific window using the `xdotool` utility.
"""

import logging
import subprocess

from . import WindowInfo
from .constants import XDOTOOL_GET_PID_COMMAND

logger = logging.getLogger(__name__)


class PidLookupError(Exception):
    """Exception raised when PID lookup using xdotool fails."""
    pass


def _run_xdotool(window: WindowInfo) -> subprocess.CompletedProcess[str]:
    """Executes the xdotool utility to find the PID for a window.

    Args:
        window: The WindowInfo object containing the window_id.

    Returns:
        The CompletedProcess object from the subprocess execution.

    Raises:
        PidLookupError: If xdotool is not installed or execution fails.
    """
    command = list(XDOTOOL_GET_PID_COMMAND) + [window.window_id]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.debug(f"xdotool returned exit code {result.returncode} for {window.window_id}: {result.stderr.strip()}")
            return None
        return result
    except FileNotFoundError as e:
        raise PidLookupError("xdotool utility not found. Please install it.") from e
    except Exception as e:
        raise PidLookupError(f"An unexpected error occurred while running xdotool: {e}") from e


def _parse_pid(output: str) -> int | None:
    """Parses the output of xdotool into a numeric PID.

    Args:
        output: The standard output from the xdotool command.

    Returns:
        The integer PID if successfully parsed, or None if the output is
        empty, zero, or cannot be parsed.
    """
    cleaned_output = output.strip()
    if not cleaned_output:
        logger.warning("xdotool returned empty output.")
        return None

    try:
        pid = int(cleaned_output)
        if pid == 0:
            logger.warning("xdotool returned a PID of 0, which is invalid.")
            return None
        return pid
    except ValueError as e:
        logger.warning(f"Failed to parse PID from xdotool output: {cleaned_output!r} - Error: {e}")
        return None


def lookup_pid(window: WindowInfo) -> int | None:
    """Determines the PID of the process owning the given window.

    Args:
        window: The WindowInfo object representing the target window.

    Returns:
        The integer PID of the owning process, or None if it could not
        be determined.
    """
    if window.pid > 0:
        logger.debug(f"Using wmctrl-provided PID {window.pid} for window: {window.window_id}")
        return window.pid
        
    logger.debug(f"wmctrl PID is 0. Falling back to xdotool for window: {window.window_id} ({window.title})")
    process = _run_xdotool(window)
    if process is None:
        return None
        
    pid = _parse_pid(process.stdout)
    
    if pid is not None:
        logger.debug(f"Found PID {pid} for window {window.window_id}")
    else:
        logger.debug(f"Could not find valid PID for window {window.window_id}")
        
    return pid


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Construct a sample WindowInfo object for testing
    sample_window = WindowInfo(
        window_id="0x0500000a",
        desktop=0,
        x=100,
        y=100,
        width=800,
        height=600,
        hostname="localhost",
        title="Sample Window"
    )

    try:
        logger.info(f"Testing PID lookup for sample window: {sample_window.window_id}")
        pid_result = lookup_pid(sample_window)
        if pid_result is not None:
            logger.info(f"Successfully found PID: {pid_result}")
        else:
            logger.info("PID lookup returned None.")
    except PidLookupError as e:
        logger.error(f"PID lookup failed: {e}")
