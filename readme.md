**Before configuration, please download the entire PiTowerGen2 file to your local system and place it on your desktop.**

Pi5 Configuration Steps:

step 1:

Move /home/pi/Desktop/PiTowerGen2/LCD_Module_RPI_code/RaspberryPi/python/lib/LCD_2inch8.py to /usr/local/lib/python3.11/dist-packages/

Move /home/pi/Desktop/PiTowerGen2/LCD_Module_RPI_code/RaspberryPi/python/lib/lcdconfig.py to /usr/local/lib/python3.11/dist-packages/

Move /home/pi/Desktop/PiTowerGen2/lcd_display.py to /home/pi/elecrow/

Move /home/pi/Desktop/PiTowerGen2/cfg/lcd_script.service to /etc/systemd/system/

sudo chmod +x /home/pi/elecrow/lcd_display.py

step 2:

Move /home/pi/Desktop/PiTowerGen2/RGB_Module_RPI_code/rpi5_ws2812 to /usr/local/lib/python3.11/dist-packages

Move /home/pi/Desktop/PiTowerGen2/RGB_Module_RPI_code/rpi5_ws2812-0.1.2.dist-info to /usr/local/lib/python3.11/dist-packages

Move /home/pi/Desktop/PiTowerGen2/rgb_control.py to /home/pi/elecrow/

Move /home/pi/Desktop/PiTowerGen2/cfg/rgb_control.service to /etc/systemd/system/

sudo chmod +x /home/pi/elecrow/rgb_control.py

step 3:

Move /home/pi/Desktop/PiTowerGen2/cfg/rc.shutdown to /etc

Move /home/pi/Desktop/PiTowerGen2/cfg/rcshutdown.service to /etc/systemd/system/

Move /home/pi/Desktop/PiTowerGen2/cfg/shutdown.py to /usr/local/bin/

step 4:

Move /home/pi/Desktop/PiTowerGen2/cfg/shutdown.service to /etc/systemd/system/

Move /home/pi/Desktop/PiTowerGen2/cfg/shutdownsignal.py to /usr/local/bin/

Step 5:

sudo apt-get update

sudo apt-get install python3-psutil python3-smbus

sudo systemctl enable lcd_script.service

sudo systemctl start lcd_script.service

sudo systemctl enable rgb_control.service

sudo systemctl start rgb_control.service

sudo systemctl enable rcshutdown.service

sudo systemctl start rcshutdown.service

sudo systemctl enable shutdown.service

sudo systemctl start shutdown.service

Step 6:

Add "dtoverlay=i2c0" to the last line of /boot/firmware/config.txt and then restart the board.

