#!/usr/bin/env bash
# ==============================================================================
# GHOST-v3 System Installer
#
# Purpose:
#   Installs GHOST-v3 as a native binary and desktop application on local Linux
#   systems (such as Kali Linux, Ubuntu, or Debian).
#
#   1. Creates a global wrapper script in /usr/local/bin/ghost
#   2. Creates a desktop application shortcut in /usr/share/applications/
# ==============================================================================

# Exit immediately on error
set -e

# Ensure the script is run with root privileges since we are writing to /usr/local/bin
if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run this installer as root (e.g., sudo ./install.sh)"
  exit 1
fi

echo "[+] Starting GHOST-v3 Installation..."

# ------------------------------------------------------------------------------
# Phase 1: Determine the Absolute Path of the GHOST directory
# ------------------------------------------------------------------------------
# We need the absolute path of where the GHOST project is currently living so
# the wrapper script knows exactly where to navigate before running python.
# BASH_SOURCE[0] gets the script path reliably even if it was symlinked.
INSTALL_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo "[i] Detected GHOST-v3 installation directory: $INSTALL_DIR"

if [ ! -f "$INSTALL_DIR/src/main.py" ]; then
    echo "[-] Error: src/main.py not found in $INSTALL_DIR/src. Are you running this from the project root?"
    exit 1
fi

# ------------------------------------------------------------------------------
# Phase 2: Create the Global Wrapper Script (/usr/local/bin/ghost)
# ------------------------------------------------------------------------------
# /usr/local/bin is the standard Linux directory for putting user-compiled
# or custom binaries so they are available on the system $PATH for all users.
WRAPPER_PATH="/usr/local/bin/ghost"

echo "[+] Generating global wrapper script at $WRAPPER_PATH"

# We write a small bash script that cd's into the installation directory before
# running the main python script. This ensures relative paths (like docker-compose.yml) work.
cat << EOF > "$WRAPPER_PATH"
#!/usr/bin/env bash
# GHOST-v3 Global Execution Wrapper

# Navigate to the original GHOST installation directory
cd "$INSTALL_DIR" || exit 1

# Execute the orchestrator with sudo privileges
# The orchestrator requires elevated privileges to manage networking and Docker containers.
exec sudo python3 src/main.py "\$@"
EOF

# Make the wrapper script executable
chmod +x "$WRAPPER_PATH"
echo "[+] Successfully created global command 'ghost'."

# ------------------------------------------------------------------------------
# Phase 3: Create the Desktop Application Shortcut (.desktop file)
# ------------------------------------------------------------------------------
# /usr/share/applications/ is the global directory where Linux desktop environments
# (like GNOME, KDE, XFCE) look for Application shortcuts. Placing a .desktop
# file here makes it available in the system application menu/launcher.
DESKTOP_ENTRY_PATH="/usr/share/applications/ghost.desktop"

echo "[+] Generating Desktop Application shortcut at $DESKTOP_ENTRY_PATH"

# We use Terminal=true because the GHOST orchestrator needs an interactive
# terminal interface to capture the CTRL+C SIGINT signal for safe shutdown.
cat << EOF > "$DESKTOP_ENTRY_PATH"
[Desktop Entry]
Version=1.0
Name=GHOST-v3
Comment=Secure Containerized Pentesting Architecture
# The executable command to run
Exec=ghost
# A generic icon. The user can optionally replace this with an absolute path to a .png.
Icon=utilities-terminal
# Must be true to launch a visual terminal window to see output and capture Ctrl+C
Terminal=true
Type=Application
# Put the app in Pentesting and Network categories so it appears alongside Nmap/Burp
Categories=Network;Security;System;
# Set the working path just to be safe
Path=$INSTALL_DIR
EOF

# Ensure appropriate permissions for the desktop file
chmod 644 "$DESKTOP_ENTRY_PATH"
echo "[+] Successfully created Desktop application shortcut."

# ------------------------------------------------------------------------------
# Final touches
# ------------------------------------------------------------------------------
echo "================================================================================"
echo "[+] GHOST-v3 Installation Complete!"
echo ""
echo "You can now launch the application in two ways:"
echo "  1. Type 'ghost' from anywhere in your terminal."
echo "  2. Search for 'GHOST-v3' in your desktop application menu."
echo "================================================================================"

exit 0
