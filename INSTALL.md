# Installation Guide

Step-by-step instructions for installing and verifying the JioPC Session Hibernate system on a fresh Ubuntu 24.04 LTS + LxQt virtual machine.

## 1. Install System Dependencies

Before proceeding, ensure all necessary core packages, tools, and build dependencies are installed:
```bash
sudo apt update
sudo apt install -y \
  wmctrl \
  xdotool \
  libnotify-bin \
  zenity \
  xss-lock \
  python3 \
  python3-yaml \
  git \
  curl \
  dpkg-dev \
  python3-pip
```

## 2. Install LxQt (The actual JioPC desktop)

Run this in the terminal:
```bash
sudo apt install lxqt sddm -y
```
When it asks which display manager to use — select `sddm`.

Reboot:
```bash
sudo reboot
```
At the login screen — look for a gear icon or session selector (bottom-right or top-right depending on sddm theme). Click it, choose **LxQt**. Log in.

## 3. Install Test Applications (Chrome & LXTerminal)

Install LXTerminal and Google Chrome to use for testing the session restore:
```bash
sudo apt install -y lxterminal
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt --fix-broken install -y
```

## 4. Clone the Repo

Clone the repository inside the VM:
```bash
cd ~
git clone https://github.com/Ayush04-C/jiopc-session-hibernate.git
cd jiopc-session-hibernate
git checkout -b feature/handlers-restore
```

## 5. Build and Install

Build and install the Debian package directly from the repository source:
```bash
# From the project root
dpkg-deb --build packaging/ jiopc-session-hibernate.deb
sudo dpkg -i jiopc-session-hibernate.deb
```

## 6. Verify Installation

Check that the files were placed correctly and permissions were granted:
```bash
dpkg -l | grep jiopc
ls -la /usr/lib/jiopc-hibernate/
ls -la /etc/xdg/autostart/jiopc-restore.desktop
```

## 7. Test Manually (Without Logging Out)

Generate a dummy `session-state.json` file (see schema documentation), and run the restore service directly to verify the Zenity dialog and app relaunch:
```bash
python3 /usr/lib/jiopc-hibernate/restore_service.py
```

## 8. Test Full Flow

1. Open several applications (e.g., Google Chrome, LXTerminal).
2. Run the capture script manually to simulate a disconnect event.
3. Verify that `~/.local/share/jiopc/hibernate/session-state.json` was created.
4. Log out of the LxQt desktop session completely.
5. Log back in.
6. The Zenity prompt should appear automatically. Click "Restore" and watch your apps reopen.

## 9. Uninstall

To completely remove the package and autostart entries:
```bash
sudo dpkg -r jiopc-session-hibernate
```
*(Note: User session state files in `~/.local/share/jiopc/` are intentionally preserved.)*

## 10. Troubleshooting

- **Logs**: All restore activities are logged to `~/.local/share/jiopc/hibernate/restore.log`. Check here if apps fail to launch.
- **Autostart Not Firing**: Ensure the `.desktop` file is correctly located in `/etc/xdg/autostart/` and that the system is running LXQt (enforced by `OnlyShowIn=LXQt;`).
- **No Dialog Shown**: Check if the `session-state.json` is older than 24 hours. The service silently discards stale sessions.
