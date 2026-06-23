"""Proc reader module for the save pipeline.

This module is responsible for reading process metadata from the Linux
/proc filesystem given a valid Process ID (PID).
"""

import logging
import os

from . import ProcessInfo
from .constants import PROC_ROOT

logger = logging.getLogger(__name__)


class ProcReaderError(Exception):
    """Exception raised for invalid API usage or severe environment failures."""
    pass


def _validate_pid(pid: int) -> None:
    """Validates that a PID is a positive integer.

    Args:
        pid: The Process ID to validate.

    Raises:
        ProcReaderError: If the PID is not an integer or is <= 0.
    """
    if not isinstance(pid, int):
        raise ProcReaderError(f"PID must be an integer, got {type(pid).__name__}")
    if pid <= 0:
        raise ProcReaderError(f"PID must be greater than 0, got {pid}")


def _read_executable(pid: int) -> str:
    """Reads the executable path for a process.

    Args:
        pid: The Process ID.

    Returns:
        The path to the executable file, or an empty string if reading fails.
    """
    path = os.path.join(PROC_ROOT, str(pid), "exe")
    try:
        return os.readlink(path)
    except FileNotFoundError:
        logger.warning(f"Executable path not found for PID {pid} (process may have terminated).")
        return ""
    except PermissionError:
        logger.warning(f"Permission denied reading executable path for PID {pid}.")
        return ""
    except OSError as e:
        logger.warning(f"OS error reading executable path for PID {pid}: {e}")
        return ""


def _read_cwd(pid: int) -> str:
    """Reads the current working directory for a process.

    Args:
        pid: The Process ID.

    Returns:
        The current working directory, or an empty string if reading fails.
    """
    path = os.path.join(PROC_ROOT, str(pid), "cwd")
    try:
        return os.readlink(path)
    except FileNotFoundError:
        logger.warning(f"CWD not found for PID {pid} (process may have terminated).")
        return ""
    except PermissionError:
        logger.warning(f"Permission denied reading CWD for PID {pid}.")
        return ""
    except OSError as e:
        logger.warning(f"OS error reading CWD for PID {pid}: {e}")
        return ""


def _read_cmdline(pid: int) -> list[str]:
    """Reads the command-line arguments used to start a process.

    Args:
        pid: The Process ID.

    Returns:
        A list of command-line arguments, or an empty list if reading fails.
    """
    path = os.path.join(PROC_ROOT, str(pid), "cmdline")
    try:
        with open(path, "rb") as f:
            data = f.read()
        
        if not data:
            return []
            
        decoded = data.decode("utf-8", errors="replace")
        parts = decoded.split("\0")
        
        if parts and parts[-1] == "":
            parts.pop()
            
        return parts
    except FileNotFoundError:
        logger.warning(f"Cmdline not found for PID {pid} (process may have terminated).")
        return []
    except PermissionError:
        logger.warning(f"Permission denied reading cmdline for PID {pid}.")
        return []
    except OSError as e:
        logger.warning(f"OS error reading cmdline for PID {pid}: {e}")
        return []


def read_process(pid: int) -> ProcessInfo:
    """Reads process metadata from the Linux /proc filesystem.

    This function attempts to gather the executable path, current working
    directory, and command-line arguments for a given PID. It gracefully handles
    failures such as the process terminating during reading.

    Args:
        pid: The Process ID to read.

    Returns:
        A ProcessInfo object containing the available metadata.
    """
    logger.debug(f"Reading process metadata for PID: {pid}")
    _validate_pid(pid)
    
    executable = _read_executable(pid)
    cwd = _read_cwd(pid)
    cmdline = _read_cmdline(pid)
    
    return ProcessInfo(
        pid=pid,
        executable=executable,
        cwd=cwd,
        cmdline=cmdline
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        user_input = input("Enter a PID to read: ")
        test_pid = int(user_input.strip())
        
        logger.info(f"Reading process info for PID: {test_pid}")
        process_info = read_process(test_pid)
        logger.info(f"Successfully read process info: {process_info}")
        
    except ValueError:
        logger.error("Invalid input. Please enter a numeric PID.")
    except ProcReaderError as e:
        logger.error(f"Process reader error: {e}")
