# Smart Medicine Dispenser (SMD) -- Kiosk Software

Native GUI kiosk application for the Smart Medicine Dispenser, built with **CustomTkinter** for Raspberry Pi (Raspbian/Ubuntu).

## Features

- **Barcode Scan Flow**: Scan prescription barcode -> Verify patient -> Auto-dispense medications
- **Manual Dispense Flow**: Browse medicines -> Select quantity -> Dispense
- **Firebase Integration**: Connects to the same Firebase Realtime DB as the Doctor's Dashboard
- **Hardware Abstraction**: Works with real GPIO/servo motors on RPi or simulates on dev machines
- **Touchscreen Optimized**: Large touch targets, fullscreen kiosk mode, auto-return to home
- **Native GUI**: No browser needed -- runs directly as a desktop application

## Quick Start

### 1. Install Dependencies

```bash
cd dispenser-kiosk
pip install -r requirements.txt
```

On Raspberry Pi, also install:
```bash
sudo apt-get install python3-tk
pip install RPi.GPIO
```

### 2. Run the Application

```bash
python3 main.py
```

The app launches in fullscreen on Linux (Raspbian/Ubuntu) and maximized window on Windows.

## Raspberry Pi Auto-Start (Kiosk Mode)

### Option A: Desktop autostart

Create `~/.config/autostart/smd-kiosk.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=SMD Kiosk
Exec=python3 /home/pi/dispenser-kiosk/main.py
X-GNOME-Autostart-enabled=true
```

### Option B: Systemd service

Create `/etc/systemd/system/smd-kiosk.service`:

```ini
[Unit]
Description=Smart Medicine Dispenser Kiosk
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/dispenser-kiosk
ExecStart=/usr/bin/python3 /home/pi/dispenser-kiosk/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

Then enable:
```bash
sudo systemctl enable smd-kiosk
sudo systemctl start smd-kiosk
```

## Hardware Wiring (Servo Motors)

| Slot | GPIO Pin (BCM) | Description     |
|------|----------------|-----------------|
| 0    | GPIO 17        | Medicine slot 1 |
| 1    | GPIO 27        | Medicine slot 2 |
| 2    | GPIO 22        | Medicine slot 3 |
| 3    | GPIO 23        | Medicine slot 4 |
| 4    | GPIO 24        | Medicine slot 5 |
| 5    | GPIO 25        | Medicine slot 6 |

Connect each servo:
- **Red wire** -> 5V external power supply
- **Brown wire** -> GND (shared with Pi GND)
- **Orange wire** -> Corresponding GPIO pin

## USB Barcode Scanner

Most USB barcode scanners work as HID keyboard devices. Simply plug it in -- no driver needed. The kiosk captures rapid keystrokes and processes the barcode automatically.

## Project Structure

```
dispenser-kiosk/
  main.py              # GUI application (CustomTkinter)
  hardware.py          # GPIO/servo controller
  config.py            # Configuration constants
  requirements.txt     # Python dependencies
  README.md            # This file
```

## Keyboard Shortcuts (Dev)

| Key    | Action              |
|--------|---------------------|
| Escape | Exit fullscreen     |
| F11    | Enter fullscreen    |
| Enter  | Submit barcode scan |

## Configuration

Edit `config.py` to customize:
- Firebase URL
- GPIO pin mapping
- Dispensing timing
- Quantity limits (min/max)
- Auto-return timeout
