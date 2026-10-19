#!/usr/bin/python3

import logging
import subprocess
import smbus
import time
from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
import time

address = 0x2D
bus = smbus.SMBus(0)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/pi_power_manager.log'),
        logging.StreamHandler()  
    ]
)

def get_systemd_target():
    try:
        result = subprocess.run(
            ["systemctl", "list-jobs", "--no-pager", "--plain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logging.error(f"systemctl command error: {result.stderr}")
            return "unknown"
            
        output = result.stdout
        
        if "reboot.target" in output and "start" in output:
            return "reboot"
        elif "poweroff.target" in output and "start" in output:
            return "poweroff"
        elif "halt.target" in output and "start" in output:
            return "halt"
        else:
            return "unknown"
            
    except subprocess.TimeoutExpired:
        logging.error("systemctl command timeout")
        return "unknown"
    except Exception as e:
        logging.error(f"Test failed: {e}")
        return "unknown"

def send_i2c_poweroff_signal():
    try:
        logging.info("Send the shutdown signal to the power management chip...")
        bus.write_i2c_block_data(address, 0x00, [0xFF, 0xFF])
        time.sleep(0.1)
        bus.write_i2c_block_data(address, 0x00, [0xFF, 0xFE])
        time.sleep(0.1)
        logging.info("power-off signal transmission completed")
    except Exception as e:
        logging.error(f"I2C communication failed: {e}")

def send_i2c_reboot_signal():
    try:
        logging.info("Send a restart signal to the power management chip...")
        bus.write_i2c_block_data(address, 0x00, [0xFF, 0xFF])
        time.sleep(0.1)
        bus.write_i2c_block_data(address, 0x00, [0xFF, 0xF8])
        time.sleep(0.1)
        logging.info("reboot signal transmission completed")
        
    except Exception as e:
        logging.error(f"I2C communication failed: {e}")


def main():
    target = get_systemd_target()
    logging.info(f"System target detected: {target}")
    
    if target == "reboot":
        strip = WS2812SpiDriver(spi_bus=1, spi_device=0, led_count=35).get_strip()
        strip.clear()
        strip.show()
        logging.info("the system is restarting.")
        send_i2c_reboot_signal()
    elif target in ["poweroff", "halt"]:
        strip = WS2812SpiDriver(spi_bus=1, spi_device=0, led_count=35).get_strip()
        strip.clear()
        strip.show()
        logging.info("the system is shutting down.")
        send_i2c_poweroff_signal()
    else:
        strip = WS2812SpiDriver(spi_bus=1, spi_device=0, led_count=35).get_strip()
        strip.clear()
        strip.show()
        logging.warning("unable to determine the system status. proceed with caution: do not perform the operation.")

if __name__ == "__main__":
    main()

