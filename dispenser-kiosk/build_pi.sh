#!/bin/bash
# ==============================================================================
# Smart Medicine Dispenser (SMD) Kiosk -- Raspberry Pi Build Script
# ==============================================================================
# This script installs all necessary system and Python dependencies and uses
# PyInstaller to compile the CustomTkinter GUI application into a standalone
# executable for Raspbian OS / Ubuntu (ARM architecture).
# ==============================================================================

# Exit on error
set -e

echo "=================================================="
echo "Starting SMD Kiosk Build for Raspberry Pi"
echo "=================================================="

# 1. Update package list and install system dependencies for Tkinter/Pillow
echo "[1/4] Installing system dependencies (Tkinter, Pi GPIO, etc.)..."
sudo apt-get update
sudo apt-get install -y python3-tk python3-pip python3-pil python3-pil.imagetk RPi.GPIO

# 2. Install Python dependencies
echo "[2/4] Installing Python requirements..."
# Use --break-system-packages to allow global installs on modern Raspberry Pi OS (Debian Bookworm)
pip3 install --break-system-packages --upgrade pip || true
pip3 install --break-system-packages -r requirements.txt
pip3 install --break-system-packages pyinstaller

# 3. Compile the application
echo "[3/4] Compiling main.py to standalone executable..."
# We use --collect-all customtkinter to ensure its assets, themes, and json configs are bundled.
# We run via 'python3 -m PyInstaller' to avoid PATH command-not-found issues.
python3 -m PyInstaller --onefile --noconsole --name "smd_kiosk" --collect-all customtkinter main.py

# 4. Verify output
echo "[4/4] Verifying build output..."
if [ -f "dist/smd_kiosk" ]; then
    echo "=================================================="
    echo "SUCCESS: Standalone executable created successfully!"
    echo "Location: $(pwd)/dist/smd_kiosk"
    echo "You can copy this file to your desktop or start it from terminal."
    echo "=================================================="
else
    echo "ERROR: Compilation finished but executable was not found."
    exit 1
fi
