#!/usr/bin/env python3
import sys
import os
import subprocess
from gi.repository import GLib
import dbus
from dbus.mainloop.glib import DBusGMainLoop

LOG_PATH = os.path.expanduser("~/.local/share/jiopc/hibernate/trigger.log")

def log_msg(msg):
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def trigger_capture():
    log_msg("Caught DBus pre-logout event! Running capture synchronously...")
    try:
        subprocess.run(
            ["python3", "-m", "save.save_service"], 
            cwd="/usr/lib/jiopc-hibernate", 
            timeout=10
        )
        log_msg("Pre-logout capture completed successfully.")
    except Exception as e:
        log_msg(f"Capture failed: {e}")

def signal_handler(*args, **kwargs):
    trigger_capture()
    sys.exit(0)

def message_filter(bus, message):
    if message.get_type() == dbus.Message.MESSAGE_TYPE_METHOD_CALL:
        if message.get_member() == 'logout':
            trigger_capture()
            sys.exit(0)
    return dbus.HANDLER_RESULT_NOT_YET_HANDLED

def main():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    log_msg("Save trigger daemon started. Native Python DBus monitoring active...")

    DBusGMainLoop(set_as_default=True)
    
    try:
        bus = dbus.SessionBus()
        
        # 1. Listen for the native LXQt pre-logout signal (case-sensitive!)
        bus.add_signal_receiver(
            signal_handler,
            signal_name="aboutToLeave",
            dbus_interface="org.lxqt.session"
        )
        
        # 2. Add global match for logout method calls (for lxqt-leave dialog)
        # eavesdrop=true is required to intercept method calls not addressed to us
        bus.add_match_string("eavesdrop='true',type='method_call',member='logout'")
        bus.add_message_filter(message_filter)
        
        loop = GLib.MainLoop()
        loop.run()
    except Exception as e:
        log_msg(f"Daemon crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
