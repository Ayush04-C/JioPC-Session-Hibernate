"""Save service module for the save pipeline.

This module serves as the top-level orchestration entry point for the session
capture pipeline. It handles environment setup, timing, and coordinates
the building and writing of the session state.
"""

import argparse
import logging
import sys
import time
import signal
from pathlib import Path

from .constants import SESSION_DIRECTORY, DEFAULT_SESSION_PATH
from .session_builder import build_session
from .json_writer import write_session, JsonWriterError

logger = logging.getLogger(__name__)


def _ensure_runtime_directory() -> None:
    """Ensures that the runtime directory exists for saving session files."""
    Path(SESSION_DIRECTORY).mkdir(parents=True, exist_ok=True)


def _setup_logging() -> None:
    """Configures the logging for the save service.

    Sets up both a FileHandler targeting the session directory and a
    StreamHandler for standard output.
    """
    log_file = Path(SESSION_DIRECTORY) / "capture.log"
    
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    
    # Configure the root logger to catch all logs from lower-level modules
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers to avoid duplicates if run multiple times
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)


def _gracefully_close_chrome(session) -> None:
    """
    Sends a clean wmctrl close request to all Chrome windows so they flush their state.
    This prevents the 'Chrome didn't shut down correctly' crash bubble.
    """
    import subprocess
    chrome_found = False
    for entry in session.entries:
        if entry.process and entry.process.executable and "chrome" in entry.process.executable.lower():
            try:
                subprocess.run(["wmctrl", "-i", "-c", entry.window.window_id], timeout=2)
                logger.info(f"Sent clean close signal to Chrome window {entry.window.window_id}")
                chrome_found = True
            except Exception as e:
                logger.warning(f"Failed to cleanly close Chrome: {e}")
                
    if chrome_found:
        logger.info("Waiting 1.5s for Chrome to flush its session state to disk...")
        time.sleep(1.5)

def timeout_handler(signum, frame):
    """Fired if the execution exceeds the strict time budget."""
    sys.stderr.write("Capture routine exceeded 10-second time budget. Aborting safely.\n")
    sys.exit(1)

def main() -> None:
    """Executes the main orchestration flow for session capture.

    Ensures the environment is prepared, times the session building process,
    and writes the final JSON payload safely. Exits with 0 on success or 1
    on failure.
    """
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)  # Enforce strict 10-second time budget

    _ensure_runtime_directory()
    _setup_logging()
    
    logger.info("Starting session capture.")
    
    parser = argparse.ArgumentParser(description="JioPC Session Capture Service")
    parser.add_argument("--trigger", type=str, default="user_disconnect", 
                        help="The event that triggered the capture (e.g. user_disconnect, inactivity_timeout)")
    args = parser.parse_args()
    
    try:
        logger.info("Building session state.")
        start_time = time.perf_counter()
        
        session = build_session()
        
        end_time = time.perf_counter()
        save_duration_ms = int((end_time - start_time) * 1000)
        
        logger.info(f"Writing session state (trigger: {args.trigger}).")
        write_session(session, DEFAULT_SESSION_PATH, save_duration_ms, trigger=args.trigger)
        
        # Give Chrome a chance to write its session to disk
        _gracefully_close_chrome(session)
        
        logger.info("Capture completed successfully.")
        signal.alarm(0)  # Cancel the alarm on success
        sys.exit(0)
        
    except JsonWriterError:
        logger.exception("Capture failed due to serialization or I/O error.")
        sys.exit(1)
    except Exception:
        logger.exception("Capture failed due to an unexpected error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
