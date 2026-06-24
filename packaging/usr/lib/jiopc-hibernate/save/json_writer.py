"""JSON writer module for the save pipeline.

This module is responsible for explicitly serializing a SessionState object,
enriching it via handlers, and persisting it atomically to a JSON file.
"""

import json
import logging
import os
import socket
from datetime import datetime, timezone

from . import SessionState, SessionEntry, WindowInfo, ProcessInfo
from .constants import SCHEMA_VERSION, DEFAULT_TRIGGER
from ..restore import apply_handlers

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
        "win_id": window.window_id,
        "app_name": window.title,
        "geometry": {
            "x": window.x,
            "y": window.y,
            "width": window.width,
            "height": window.height
        },
        "desktop": str(window.desktop),
        "has_unsaved": "*" in window.title
    }


def _process_to_dict(process: ProcessInfo) -> dict:
    """Serializes a ProcessInfo object to a dictionary.

    Args:
        process: The ProcessInfo object.

    Returns:
        A dictionary representation of the ProcessInfo object.
    """
    exec_path = process.executable or None

    return {
        "exec": exec_path,
        "cmdline": process.cmdline,
        "cwd": process.cwd if process.cwd else None,
        "pid": process.pid if process.pid else None
    }


def _entry_to_dict(entry: SessionEntry) -> dict:
    """Serializes a SessionEntry object to a dictionary.

    Args:
        entry: The SessionEntry object.

    Returns:
        A dictionary representation of the SessionEntry object with
        pre-initialized handler fields.
    """
    window_dict = _window_to_dict(entry.window)
    process_dict = _process_to_dict(entry.process)
    
    return {
        "win_id": window_dict["win_id"],
        "app_name": window_dict["app_name"],
        "exec": process_dict["exec"],
        "cmdline": process_dict["cmdline"],
        "handler": None,
        "restore_args": [],
        "geometry": window_dict["geometry"],
        "restore_supported": False,
        "cwd": process_dict["cwd"],
        "has_unsaved": window_dict["has_unsaved"],
        "pid": process_dict["pid"],
        "desktop": window_dict["desktop"]
    }


def _session_to_dict(session: SessionState) -> dict:
    """Serializes a SessionState object to a dictionary and enriches it.

    Args:
        session: The SessionState object.

    Returns:
        A dictionary representation of the SessionState object.

    Raises:
        JsonWriterError: If handler enrichment fails.
    """
    raw_windows = []
    for entry in session.entries:
        if str(entry.window.desktop) == "-1":
            continue
        raw_windows.append(_entry_to_dict(entry))
        
    try:
        enriched_windows = apply_handlers.enrich_windows(raw_windows)
    except Exception as e:
        raise JsonWriterError(f"Handler enrichment failed: {e}") from e
        
    saved_at = session.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return {
        "schema_version": SCHEMA_VERSION,
        "saved_at": saved_at,
        "trigger": DEFAULT_TRIGGER,
        "windows": enriched_windows,
        "meta": {
            "total_windows": len(enriched_windows),
            "restored_count": None,
            "hostname": socket.gethostname(),
            "display": os.environ.get("DISPLAY", "")
        }
    }


def write_session(session: SessionState, path: str, save_duration_ms: int = 0) -> None:
    """Serializes and writes a SessionState object to a JSON file atomically.

    Args:
        session: The SessionState object to serialize.
        path: The file path where the JSON data will be written.
        save_duration_ms: The duration taken to capture the session state.

    Raises:
        JsonWriterError: If an error occurs during serialization or file writing.
    """
    logger.debug(f"Starting serialization for SessionState with {len(session.entries)} entries.")
    
    try:
        data = _session_to_dict(session)
        final_data = {
            "schema_version": data["schema_version"],
            "saved_at": data["saved_at"],
            "trigger": data["trigger"],
            "save_duration_ms": save_duration_ms,
            "windows": data["windows"],
            "meta": data["meta"]
        }
    except JsonWriterError:
        raise JsonWriterError(f"Failed to serialize session state: {e}") from e
    except Exception as e:
        logger.error(f"Failed to serialize session state: {e}")
        raise JsonWriterError(f"Failed to serialize session state: {e}") from e

    logger.debug(f"Starting atomic write to {path}.")
    temp_path = f"{path}.tmp"
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
            
        def _rotate_history(base_path: str) -> None:
            try:
                dir_name = os.path.dirname(base_path)
                base_name = os.path.basename(base_path)
                name, ext = os.path.splitext(base_name)
                path_1 = os.path.join(dir_name, f"{name}-1{ext}")
                path_2 = os.path.join(dir_name, f"{name}-2{ext}")
                
                if os.path.exists(path_1):
                    os.replace(path_1, path_2)
                if os.path.exists(base_path):
                    os.replace(base_path, path_1)
            except Exception as e:
                logger.warning(f"Failed to rotate session history: {e}")
                
        _rotate_history(path)
        os.replace(temp_path, path)
        logger.info(f"Successfully wrote session state to {path}.")
    except OSError as e:
        logger.error(f"Failed to write session state to {path}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise JsonWriterError(f"Failed to write session state to {path}: {e}") from e
    except TypeError as e:
        logger.error(f"Failed to serialize JSON data for {path}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise JsonWriterError(f"Failed to serialize JSON data for {path}: {e}") from e


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

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
        write_session(sample_session, test_path, 150)
    except JsonWriterError as e:
        logger.error(f"Test failed: {e}")
