# Installation Guide

## Preparing for Build
Before building the package, ensure your packaging scripts have the correct permissions:
```bash
chmod +x packaging/DEBIAN/postinst
chmod +x packaging/DEBIAN/prerm
```

## Step-by-Step Installation
1. Build the Debian package (or obtain the `.deb` file).
   ```bash
   dpkg-deb --build packaging jiopc-session-hibernate.deb
   ```
2. Install the package using dpkg:
   ```bash
   sudo dpkg -i jiopc-session-hibernate.deb
   ```

## Verify Installation
1. Ensure the Python scripts in `/usr/lib/jiopc-hibernate/` have executable permissions.
2. Check that `~/.local/share/jiopc/hibernate/` directory exists for your user.
3. Verify that `/usr/share/autostart/jiopc-restore.desktop` exists.

## Manual Testing
You can manually trigger the restore service without logging out to test it:
```bash
/usr/lib/jiopc-hibernate/restore_service.py
```

## Uninstallation
To cleanly remove the package from the system:
```bash
sudo dpkg -r jiopc-session-hibernate
```
