# PiTower Gen2

PiTower Gen2 is a Raspberry Pi 5 case-control solution for the LCD, RGB lighting, and safe-shutdown button. This repository contains the Python control programs, systemd service files, and Raspberry Pi configuration files required to operate the hardware.

## Just want to use the case? (Recommended)

If you only want to use PiTower Gen2, do **not** run the custom-image configuration commands below. Download the pre-configured full image, flash it to a microSD card, and boot the Raspberry Pi 5.

### Download and flash the official full image

[Download the PiTower Gen2 full image (Google Drive)](https://drive.google.com/drive/folders/1KoCKDflZ5MS2dmKSYOx2GHqjXR7aUxpp?usp=sharing)

We provide full images for both the **Bookworm** and **Trixie** versions.

The image includes the project files, Python dependencies, systemd services, and boot configuration. Use Raspberry Pi Imager, balenaEtcher, or a similar tool to flash it:

1. Insert a microSD card into your computer.
2. Select the downloaded image and the correct microSD card in the flashing tool.
3. Start the flash and wait for verification to finish.
4. Insert the microSD card into the Raspberry Pi 5, connect PiTower Gen2, and power it on.

After the first boot, the LCD, RGB lighting, shutdown button, and safe-shutdown services should start automatically. If the hardware is connected but does not respond, see [Troubleshooting](#troubleshooting).

> **Important:** Flashing overwrites the data on the target microSD card. Confirm that the correct disk is selected before starting.

## Using your own Raspberry Pi image

Follow this section only if you are installing PiTower Gen2 on your own [Raspberry Pi OS image](https://www.raspberrypi.com/software/operating-systems/) instead of using the official full image. Run the commands in the Raspberry Pi **Terminal**. The commands use `$HOME` to find the current user's home directory, so they work with usernames other than `pi`. The application itself is installed under `/opt/pitower-gen2`, avoiding user-specific paths in system services.

### Requirements

- Raspberry Pi 5
- Raspberry Pi OS 64-bit (Bookworm recommended)
- PiTower Gen2 LCD, RGB module, and shutdown button connected and powered correctly
- An Internet connection for the Terminal

### 0. Create the installation directory

On a fresh custom image, `/opt/pitower-gen2` may not exist. Before copying any project files, run the following command in the Raspberry Pi Terminal:

```bash
sudo mkdir -p /opt/pitower-gen2/Pictures
```

This creates both `/opt/pitower-gen2` and its `Pictures` subdirectory. It is safe to run again if the directories already exist. Continue with the steps below to copy the programs, drivers, and images into the installation directory.

### 1. Get the project files

Run the following commands in the Terminal. `$HOME` is automatically set to the home directory of the account currently logged in:

```bash
sudo git clone https://github.com/Elecrow-RD/PiTower_Gen2.git "$HOME/PiTowerGen2"
cd "$HOME/PiTowerGen2"
sudo cp -a "$HOME/PiTowerGen2/." /opt/pitower-gen2/
```

If the project is already downloaded to `$HOME/PiTowerGen2`, skip the `git clone` command and run the remaining commands from that project directory. If it is stored elsewhere, replace `$HOME/PiTowerGen2` in these commands with its actual path:

```bash
sudo cp -a "$HOME/PiTowerGen2/." /opt/pitower-gen2/
cd "$HOME/PiTowerGen2"
```

### 2. Install the LCD module, images, and service

First, in the **same Terminal session**, determine the site-packages directory for `/usr/bin/python3`, which is the interpreter used by the systemd services. The directory is computed from the Python version installed on the user's system; no Python minor version is hard-coded. Keep using this Terminal session for the remaining installation commands.

```bash
PYTHON_BIN="/usr/bin/python3"
PYTHON_SITE_PACKAGES="$($PYTHON_BIN -c 'import sysconfig; print(sysconfig.get_path("purelib"))')"
echo "Using $PYTHON_BIN"
echo "Installing Python modules into $PYTHON_SITE_PACKAGES"
```

Then run:

```bash
sudo install -m 0644 LCD_Module_RPI_code/RaspberryPi/python/lib/LCD_2inch8.py "$PYTHON_SITE_PACKAGES/LCD_2inch8.py"
sudo install -m 0644 LCD_Module_RPI_code/RaspberryPi/python/lib/lcdconfig.py "$PYTHON_SITE_PACKAGES/lcdconfig.py"
sudo install -m 0755 lcd_display.py /opt/pitower-gen2/lcd_display.py
sudo mkdir -p /opt/pitower-gen2/Pictures
sudo cp -a Pictures/. /opt/pitower-gen2/Pictures/
sudo install -m 0644 cfg/lcd_script.service /etc/systemd/system/lcd_script.service
```

The `Pictures` directory must be copied to `/opt/pitower-gen2/Pictures`, next to the installed `lcd_display.py`. Run the copy command above from the downloaded project directory, which must contain `Pictures/`.

The current LCD program uses these image locations:

- Background: `/opt/pitower-gen2/Pictures/bj-03.png`. If this image is missing, the program uses a solid-color background.
- Startup image: `/opt/pitower-gen2/LCD_Module_RPI_code/RaspberryPi/python/pic/LCD_2inch8.png`. This file is included in the LCD module directory copied in Step 1 and is required at startup.

The program resolves both locations relative to its own script file. The LCD service must therefore run `/opt/pitower-gen2/lcd_display.py`. Running a separate copy at `/opt/lcd_display.py` makes it look for the images under `/opt` instead.

### 3. Install the RGB module and service

Run the following commands in the Terminal:

```bash
sudo cp -a RGB_Module_RPI_code/rpi5_ws2812 "$PYTHON_SITE_PACKAGES/"
sudo cp -a RGB_Module_RPI_code/rpi5_ws2812-0.1.2.dist-info "$PYTHON_SITE_PACKAGES/"
sudo install -m 0755 rgb_control.py /opt/pitower-gen2/rgb_control.py
sudo install -m 0644 cfg/rgb_control.service /etc/systemd/system/rgb_control.service
```

### 4. Install the shutdown and safe-shutdown services

Run the following commands in the Terminal:

```bash
sudo install -m 0755 cfg/rc.shutdown /etc/rc.shutdown
sudo install -m 0755 cfg/rcshutdown.service /etc/systemd/system/rcshutdown.service
sudo install -m 0755 cfg/shutdown.py /usr/local/bin/shutdown.py
sudo install -m 0755 cfg/shutdown.service /etc/systemd/system/shutdown.service
sudo install -m 0755 cfg/shutdownsignal.py /usr/local/bin/shutdownsignal.py
```

### 5. Install dependencies and enable the services

Run the following commands in the Terminal:

```bash
sudo apt-get update
sudo apt-get install -y python3-psutil python3-smbus
sudo systemctl daemon-reload
sudo systemctl enable --now lcd_script.service
sudo systemctl enable --now rgb_control.service
sudo systemctl enable --now rcshutdown.service
sudo systemctl enable --now shutdown.service
```

### 6. Enable I2C and reboot

Open the Raspberry Pi firmware configuration file in the Terminal:

```bash
sudo nano /boot/firmware/config.txt
```

Add this line at the end of the file:

```ini
dtoverlay=i2c0
dtparam=spi=on
dtoverlay=spi1-3cs
dtoverlay=w1-gpio
dtparam=pciex1
```

Save and exit `nano` by pressing `Ctrl+O`, Enter, and then `Ctrl+X`. Reboot from the Terminal:

```bash
sudo reboot
```

### 7. Verify the service status

After the reboot, run these commands in the Terminal:

```bash
sudo systemctl --no-pager --full status lcd_script.service
sudo systemctl --no-pager --full status rgb_control.service
sudo systemctl --no-pager --full status rcshutdown.service
sudo systemctl --no-pager --full status shutdown.service
```

Check the installed LCD and RGB service paths:

```bash
sudo systemctl cat lcd_script.service rgb_control.service
```

The LCD service should use `ExecStart=/usr/bin/python3 /opt/pitower-gen2/lcd_display.py`, and the RGB service should use `ExecStart=/usr/bin/python3 /opt/pitower-gen2/rgb_control.py`. Both should use `WorkingDirectory=/opt/pitower-gen2`.

To view recent logs:

```bash
sudo journalctl -u lcd_script.service -u rgb_control.service -u rcshutdown.service -u shutdown.service -n 100 --no-pager
```

## Features

- **LCD display:** `lcd_display.py` drives the 2.8-inch LCD module.
- **RGB lighting:** `rgb_control.py` controls the Raspberry Pi 5 WS2812 LEDs.
- **Safe shutdown:** The shutdown button and `shutdownsignal.py` request an orderly system shutdown, reducing the risk of filesystem damage caused by unplugging the power.
- **Automatic startup:** systemd services start the control programs during boot, so they do not need to be launched manually.

## Project structure

```text
PiTowerGen2/
├── LCD_Module_RPI_code/       # LCD driver and Python libraries
├── RGB_Module_RPI_code/       # RGB/WS2812 driver and Python libraries
├── Pictures/                  # LCD images; copy to /opt/pitower-gen2/Pictures
├── cfg/                       # systemd, shutdown, and boot configuration
├── lcd_display.py             # LCD control program
└── rgb_control.py             # RGB control program
```

## Troubleshooting

### The LCD does not display anything

Confirm that `Pictures/` and `LCD_Module_RPI_code/` are installed under `/opt/pitower-gen2`, and that the service starts the script in that same directory. Verify the expected image files in the Terminal:

```bash
sudo ls -l /opt/pitower-gen2/Pictures/bj-03.png
sudo ls -l /opt/pitower-gen2/LCD_Module_RPI_code/RaspberryPi/python/pic/LCD_2inch8.png
```

Check the LCD cable and power connection, then run these commands in the Terminal:

```bash
sudo systemctl restart lcd_script.service
sudo journalctl -u lcd_script.service -n 50 --no-pager
```

### The RGB LEDs are off or show incorrect colors

Check the RGB module's power, data, and ground connections, then run:

```bash
sudo systemctl restart rgb_control.service
sudo journalctl -u rgb_control.service -n 50 --no-pager
```

### The shutdown button does not work

Confirm that `/boot/firmware/config.txt` contains `dtoverlay=i2c0` and that the Raspberry Pi has been rebooted. Then run:

```bash
sudo systemctl restart rcshutdown.service
sudo systemctl restart shutdown.service
sudo journalctl -u rcshutdown.service -u shutdown.service -n 50 --no-pager
```

### Python modules cannot be imported

Make sure you ran the installation commands from the project directory and kept the same Terminal session after setting `PYTHON_SITE_PACKAGES`. Verify the installation with the system's active `python3`:

```bash
sudo /usr/bin/python3 -c "import LCD_2inch8, lcdconfig; print('LCD modules: OK')"
sudo /usr/bin/python3 -c "import rpi5_ws2812; print('RGB module: OK')"
```

## Safety notes

- Double-check paths and filenames before modifying `/etc`, `/usr/local`, `/boot/firmware`, or systemd configuration files.
- Use the shutdown service to power off the Raspberry Pi safely. Do not unplug the power while the system is running.
- After changing a service file, run `sudo systemctl daemon-reload` and restart the affected service.
- Flashing an image erases the selected microSD card. Back up any data before flashing.

## Contributing

Issues and pull requests are welcome for hardware compatibility reports, installation improvements, and display or lighting enhancements. When reporting a problem, include the Raspberry Pi model, Raspberry Pi OS version, wiring details, and relevant `journalctl` output.
