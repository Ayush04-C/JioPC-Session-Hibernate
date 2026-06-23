"""Window discovery module for the save pipeline.

This module is responsible for discovering currently open windows from the
Linux desktop using the `wmctrl` utility.
"""

import logging
import subprocess
from typing import Optional

from . import WindowInfo
from .constants import WMCTRL_COMMAND

logger = logging.getLogger(__name__)


class WindowDiscoveryError(Exception):
    """Exception raised when window discovery fails."""
    pass


def _run_wmctrl() -> str:
    """Executes the wmctrl utility to get window information.

    Returns:
        The standard output of the wmctrl command as a string.

    Raises:
        WindowDiscoveryError: If the wmctrl command fails or is not found.
    """
    try:
        result = subprocess.run(
            WMCTRL_COMMAND,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.warning(f"wmctrl returned non-zero exit code (some windows may have closed during query): {result.stderr.strip()}")
        # Always return stdout, even if there was an error, because wmctrl often
        # outputs partial window lists before failing on a BadWindow error.
        return result.stdout
    except FileNotFoundError as e:
        raise WindowDiscoveryError("wmctrl utility not found. Please install it.") from e
    except Exception as e:
        raise WindowDiscoveryError(f"An unexpected error occurred while running wmctrl: {e}") from e


def _parse_line(line: str) -> Optional[WindowInfo]:
    """Parses a single line of wmctrl output into a WindowInfo object.

    Args:
        line: A single line of output from wmctrl -lpG.

    Returns:
        A WindowInfo object if the line was parsed successfully, or None
        if the line was malformed.
    """
    parts = line.split(maxsplit=8)
    if len(parts) < 9:
        logger.warning(f"Malformed wmctrl output line (expected at least 9 parts): {line!r}")
        return None

    try:
        window_id = parts[0]
        desktop = int(parts[1])
        pid = int(parts[2])
        x = int(parts[3])
        y = int(parts[4])
        width = int(parts[5])
        height = int(parts[6])
        hostname = parts[7]
        title = parts[8]

        return WindowInfo(
            window_id=window_id,
            desktop=desktop,
            x=x,
            y=y,
            width=width,
            height=height,
            hostname=hostname,
            title=title,
            pid=pid
        )
    except ValueError as e:
        logger.warning(f"Failed to parse numeric values in wmctrl output line: {line!r} - Error: {e}")
        return None


def _parse_output(output: str) -> list[WindowInfo]:
    """Parses the full multi-line output of wmctrl.

    Args:
        output: The complete standard output from wmctrl.

    Returns:
        A list of WindowInfo objects successfully parsed from the output.
    """
    windows: list[WindowInfo] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        window_info = _parse_line(line)
        if window_info is not None:
            windows.append(window_info)

    return windows


def discover_windows() -> list[WindowInfo]:
    """Discovers currently open windows from the Linux desktop.

    Returns:
        A list of WindowInfo objects representing the currently open windows.

    Raises:
        WindowDiscoveryError: If the underlying window discovery mechanism fails.
    """
    logger.debug("Starting window discovery using wmctrl.")
    output = _run_wmctrl()
    windows = _parse_output(output)
    logger.debug(f"Discovered {len(windows)} windows.")
    return windows


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        discovered_windows = discover_windows()
        for window in discovered_windows:
            logger.info(f"Discovered window: {window}")
    except WindowDiscoveryError as e:
        logger.error(f"Window discovery failed: {e}")
