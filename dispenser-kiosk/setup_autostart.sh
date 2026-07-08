#!/bin/bash
# ==============================================================================
# SMD Kiosk — Autostart Setup Script
# ==============================================================================
# Run this script ONCE on your Raspberry Pi to configure the kiosk application
# to launch automatically on every boot.
#
# Usage:  ./setup_autostart.sh
# ==============================================================================

set -e

# Detect the absolute path of the executable
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXEC_PATH="$SCRIPT_DIR/dist/smd_kiosk"

# Check if the executable exists
if [ ! -f "$EXEC_PATH" ]; then
    echo "ERROR: Executable not found at $EXEC_PATH"
    echo "Please run ./build_pi.sh first to compile the application."
    exit 1
fi

# Make sure the executable has correct permissions
chmod +x "$EXEC_PATH"

# Create autostart directory
mkdir -p ~/.config/autostart

# Write the desktop entry file
cat > ~/.config/autostart/smd-kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=SMD Kiosk
Comment=Smart Medicine Dispenser Kiosk Application
Exec=$EXEC_PATH
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "=================================================="
echo "SUCCESS: Autostart configured!"
echo "Executable: $EXEC_PATH"
echo "Autostart file: ~/.config/autostart/smd-kiosk.desktop"
echo ""
echo "The kiosk will launch automatically on next reboot."
echo "To test now, reboot with:  sudo reboot"
echo "=================================================="
