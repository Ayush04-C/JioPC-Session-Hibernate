"""Window discovery module for the save pipeline.

This module is responsible for discovering currently open windows from the
Linux desktop using the `wmctrl` utility.
"""

import logging
import subprocess
from typing import Optional

from .models import WindowInfo

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
            text=True,
            check=True
        )
        return result.stdout
    except FileNotFoundError as e:
        raise WindowDiscoveryError("wmctrl utility not found. Please install it.") from e
    except subprocess.CalledProcessError as e:
        raise WindowDiscoveryError(f"wmctrl command failed with exit code {e.returncode}: {e.stderr}") from e
    except Exception as e:
        raise WindowDiscoveryError(f"An unexpected error occurred while running wmctrl: {e}") from e


def _parse_line(line: str) -> Optional[WindowInfo]:
    """Parses a single line of wmctrl output into a WindowInfo object.

    Args:
        line: A single line of output from wmctrl -lG.

    Returns:
        A WindowInfo object if the line was parsed successfully, or None
        if the line was malformed.
    """
    parts = line.split(maxsplit=7)
    if len(parts) < 8:
        logger.warning(f"Malformed wmctrl output line (expected at least 8 parts): {line!r}")
        return None

    try:
        window_id = parts[0]
        desktop = int(parts[1])
        x = int(parts[2])
        y = int(parts[3])
        width = int(parts[4])
        height = int(parts[5])
        hostname = parts[6]
        title = parts[7]

        return WindowInfo(
            window_id=window_id,
            desktop=desktop,
            x=x,
            y=y,
            width=width,
            height=height,
            hostname=hostname,
            title=title
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
    windows = []
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
            logging.info(f"Discovered window: {window}")
    except WindowDiscoveryError as e:
        logging.error(f"Window discovery failed: {e}")
