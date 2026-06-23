"""Data models for the save pipeline."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WindowInfo:
    """Information about a captured window.

    Attributes:
        window_id: The unique identifier of the window.
        desktop: The desktop number where the window is located.
        x: The X coordinate of the window's top-left corner.
        y: The Y coordinate of the window's top-left corner.
        width: The width of the window.
        height: The height of the window.
        hostname: The hostname of the machine where the window is running.
        title: The title of the window.
    """
    window_id: str
    desktop: int
    x: int
    y: int
    width: int
    height: int
    hostname: str
    title: str
    pid: int = 0


@dataclass(frozen=True)
class ProcessInfo:
    """Information about a process associated with a window.

    Attributes:
        pid: The process ID.
        executable: The path to the executable file.
        cwd: The current working directory of the process.
        cmdline: The command line arguments used to start the process.
    """
    pid: int
    executable: str
    cwd: str
    cmdline: list[str]


@dataclass(frozen=True)
class SessionEntry:
    """A single entry in a saved session, linking a window to its process.

    Attributes:
        window: The window information.
        process: The process information.
    """
    window: WindowInfo
    process: ProcessInfo


@dataclass(frozen=True)
class SessionState:
    """The complete state of a captured session.

    Attributes:
        timestamp: The time when the session was captured.
        entries: A list of session entries.
    """
    timestamp: datetime
    entries: list[SessionEntry]
