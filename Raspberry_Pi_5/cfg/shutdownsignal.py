#!/usr/bin/env python3
import psutil
import time
import smbus
import os
from pathlib import Path

class RPiSystemMonitor:
    def __init__(self):
        # Initialize I2C bus
        self.bus = smbus.SMBus(0)  # Use I2C-0
        self.i2c_address = 0x2D    # I2C slave address

    def check_shutdown_signal(self):
        """Check if shutdown signal is received via I2C"""
        try:
            # Read one byte from I2C device with command 0xFF
            status = self.bus.read_byte_data(self.i2c_address, 0xFF)
            return status == 0
        except Exception as e:
            print(f"Check shutdown signal error: {e}")
            return False

    def system_shutdown(self):
        """Perform system shutdown"""
        try:
            print("Shutdown signal received, sending confirmation...")
            # Send clear screen and shutdown confirmation signal
            self.bus.write_i2c_block_data(self.i2c_address, 0x00, [0xFF, 0xFF])
            time.sleep(0.1)  # Wait a bit to ensure the signal is sent
            self.bus.write_i2c_block_data(self.i2c_address, 0x00, [0xFF, 0xFE])
            time.sleep(0.1)  # Wait a bit to ensure the signal is sent

            print("System will shutdown now...")
            import subprocess
            subprocess.run(["sudo", "shutdown", "-h", "now"])
        except Exception as e:
            print(f"System shutdown error: {e}")

    def run(self):
        while True:
            try:
                # Check shutdown signal first
                if self.check_shutdown_signal():
                    self.system_shutdown()
                    break  # Exit the loop after initiating shutdown

            except Exception as e:
                print(f"Runtime error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    monitor = RPiSystemMonitor()
    monitor.run()
