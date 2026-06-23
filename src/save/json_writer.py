"""JSON writer module for the save pipeline.

This module is responsible for explicitly serializing a SessionState object
and persisting it to a JSON file.
"""

import json
import logging
from datetime import datetime

from . import SessionState, SessionEntry, WindowInfo, ProcessInfo

logger = logging.getLogger(__name__)


class JsonWriterError(Exception):
    """Exception raised when writing the session state to a file fails."""
    pass


def _window_to_dict(window: WindowInfo) -> dict:
    """Serializes a WindowInfo object to a dictionary.

    Args:
        window: The WindowInfo object.

    Returns:
        A dictionary representation of the WindowInfo object.
    """
    return {
        "window_id": window.window_id,
        "desktop": window.desktop,
        "x": window.x,
        "y": window.y,
        "width": window.width,
        "height": window.height,
        "hostname": window.hostname,
        "title": window.title,
    }


def _process_to_dict(process: ProcessInfo) -> dict:
    """Serializes a ProcessInfo object to a dictionary.

    Args:
        process: The ProcessInfo object.

    Returns:
        A dictionary representation of the ProcessInfo object.
    """
    return {
        "pid": process.pid,
        "executable": process.executable,
        "cwd": process.cwd,
        "cmdline": process.cmdline,
    }


def _entry_to_dict(entry: SessionEntry) -> dict:
    """Serializes a SessionEntry object to a dictionary.

    Args:
        entry: The SessionEntry object.

    Returns:
        A dictionary representation of the SessionEntry object.
    """
    return {
        "window": _window_to_dict(entry.window),
        "process": _process_to_dict(entry.process),
    }


def _session_to_dict(session: SessionState) -> dict:
    """Serializes a SessionState object to a dictionary.

    Args:
        session: The SessionState object.

    Returns:
        A dictionary representation of the SessionState object.
    """
    return {
        "timestamp": session.timestamp.isoformat(),
        "entries": [_entry_to_dict(entry) for entry in session.entries],
    }


def write_session(session: SessionState, path: str) -> None:
    """Serializes and writes a SessionState object to a JSON file.

    Args:
        session: The SessionState object to serialize.
        path: The file path where the JSON data will be written.

    Raises:
        JsonWriterError: If an error occurs during file writing.
    """
    logger.debug(f"Starting serialization for SessionState with {len(session.entries)} entries.")
    
    try:
        data = _session_to_dict(session)
    except Exception as e:
        logger.error(f"Failed to serialize session state: {e}")
        raise JsonWriterError(f"Failed to serialize session state: {e}") from e

    logger.debug(f"Starting write to {path}.")
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Successfully wrote session state to {path}.")
    except OSError as e:
        logger.error(f"Failed to write session state to {path}: {e}")
        raise JsonWriterError(f"Failed to write session state to {path}: {e}") from e
    except TypeError as e:
        logger.error(f"Failed to serialize JSON data for {path}: {e}")
        raise JsonWriterError(f"Failed to serialize JSON data for {path}: {e}") from e


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Construct a sample session in memory
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
    
    sample_process = ProcessInfo(
        pid=1234,
        executable="/usr/bin/sample",
        cwd="/home/user",
        cmdline=["/usr/bin/sample", "--test"]
    )
    
    sample_entry = SessionEntry(
        window=sample_window,
        process=sample_process
    )
    
    sample_session = SessionState(
        timestamp=datetime.now(),
        entries=[sample_entry]
    )
    
    test_path = "sample_session.json"
    
    try:
        write_session(sample_session, test_path)
    except JsonWriterError as e:
        logger.error(f"Test failed: {e}")
