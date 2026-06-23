#!/bin/bash
# Natively triggers session state capture when the screen idles/locks
# Triggered by xss-lock (Inactivity Timeout)

cd /usr/lib/jiopc-hibernate && python3 -m save.save_service

# Sleep forever so xss-lock thinks the session is "locked".
# If the user wakes the computer, xss-lock sends SIGTERM and cleanly kills this.
# If the broker disconnects, the session teardown cleanly kills this.
sleep infinity
