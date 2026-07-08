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

echo "Setting up autostart using multiple methods for compatibility..."

# ---- Method 1: LXDE Autostart (Most reliable on Raspberry Pi OS) ----
LXDE_AUTOSTART="$HOME/.config/lxsession/LXDE-pi/autostart"
mkdir -p "$(dirname "$LXDE_AUTOSTART")"

# Check if it already exists in the file, if not add it
if [ -f "$LXDE_AUTOSTART" ]; then
    # Remove old entry if present
    grep -v "smd_kiosk" "$LXDE_AUTOSTART" > /tmp/lxde_autostart_tmp || true
    cp /tmp/lxde_autostart_tmp "$LXDE_AUTOSTART"
fi

# Append the kiosk launch command
echo "@$EXEC_PATH" >> "$LXDE_AUTOSTART"
echo "[OK] LXDE autostart configured: $LXDE_AUTOSTART"

# ---- Method 2: XDG Desktop Autostart (Backup) ----
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/smd-kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=SMD Kiosk
Comment=Smart Medicine Dispenser Kiosk Application
Exec=$EXEC_PATH
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
echo "[OK] XDG desktop autostart configured: ~/.config/autostart/smd-kiosk.desktop"

# ---- Method 3: Cron @reboot (Fallback for headless setups) ----
# Remove old cron entry if present, then add new one
(crontab -l 2>/dev/null | grep -v "smd_kiosk" ; echo "@reboot sleep 10 && DISPLAY=:0 $EXEC_PATH &") | crontab -
echo "[OK] Cron @reboot configured as fallback"

echo ""
echo "=================================================="
echo "SUCCESS: Autostart configured (3 methods)!"
echo ""
echo "  Executable : $EXEC_PATH"
echo "  LXDE       : $LXDE_AUTOSTART"
echo "  XDG Desktop: ~/.config/autostart/smd-kiosk.desktop"
echo "  Cron       : @reboot (with 10s delay)"
echo ""
echo "Reboot now to test:  sudo reboot"
echo "=================================================="
