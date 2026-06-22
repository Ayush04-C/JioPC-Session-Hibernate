# Design Document

## Problem
*Placeholder: Detail the lack of session persistence across VMs in JioPC.*

## Architecture
*Placeholder: Deep dive into the flow.*
```text
[Architecture Diagram Placeholder]
```

## Component Design
*Placeholder: Discuss individual components (A-E) in depth.*

## Technology Choices
- **Python**: Easy standard library (json, subprocess) and rapid prototyping capabilities.
- **wmctrl**: Simple CLI tool to interact with EWMH/NetWM compatible X Window Managers.
- **Zenity**: Native-looking lightweight dialogs for user interaction.
- **XDG Autostart**: Standardized, clean way to start the restore service when the desktop loads on a new VM.

## Constraints
*Placeholder: Discuss system-level constraints (e.g. read-only rootFS areas).*

## Limitations
*Placeholder: Mention apps that do not support session restore.*
