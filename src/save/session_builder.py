"""Session builder module for the save pipeline.

This module is responsible for orchestrating the capture pipeline by discovering
windows, looking up their PIDs, reading process metadata, and assembling the
final session state.
"""

import logging
from datetime import datetime

from . import WindowInfo, SessionEntry, SessionState
from .window_discovery import discover_windows
from .pid_lookup import lookup_pid, PidLookupError
from .proc_reader import read_process

logger = logging.getLogger(__name__)


def _build_entry(window: WindowInfo) -> SessionEntry | None:
    """Builds a SessionEntry for a given window.

    This involves looking up the PID for the window and reading the associated
    process metadata.

    Args:
        window: The WindowInfo object representing the target window.

    Returns:
        A SessionEntry object if the process could be successfully mapped, or
        None if the PID could not be determined.

    Raises:
        PidLookupError: If an environment error occurs during PID lookup.
    """
    logger.debug(f"Building session entry for window: {window.window_id}")
    
    pid = lookup_pid(window)
    if pid is None:
        logger.warning(f"Skipping window {window.window_id} ({window.title}): PID not found.")
        return None
        
    process_info = read_process(pid)
    
    return SessionEntry(
        window=window,
        process=process_info
    )


def build_session() -> SessionState:
    """Orchestrates the capture pipeline to build a complete session state.

    Returns:
        A SessionState object containing all successfully captured session entries
        and the timestamp of the capture.
    """
    logger.info("Starting session capture pipeline.")
    
    windows = discover_windows()
    entries: list[SessionEntry] = []
    
    for window in windows:
        entry = _build_entry(window)
        if entry is not None:
            entries.append(entry)
            
    timestamp = datetime.now()
    
    logger.info(f"Session capture complete. Successfully captured {len(entries)} entries.")
    
    return SessionState(
        timestamp=timestamp,
        entries=entries
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("Running session builder standalone test.")
    try:
        session = build_session()
        logger.info(f"Session timestamp: {session.timestamp}")
        logger.info(f"Total captured entries: {len(session.entries)}")
    except Exception as e:
        logger.error(f"Failed to build session: {e}")
