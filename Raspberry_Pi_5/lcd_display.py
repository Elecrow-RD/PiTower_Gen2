#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import sys
import time
import logging
import spidev as SPI
import LCD_2inch8
from PIL import Image, ImageDraw, ImageFont
import psutil
from datetime import datetime
import smbus

logging.basicConfig(level=logging.DEBUG)


address = 0x2D
bus = smbus.SMBus(0)

# ANSI color definitions
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'
ORANGE = '\033[38;2;255;187;51m'

USED_COLOR = (255, 136, 0)   
FREE_COLOR = (0, 51, 51)    
TEXT_COLOR = (255, 255, 255)  
TITLE_COLOR = (255, 187, 51) 

def get_cpu_info():
    """Get CPU information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0)
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            cpu_temp = int(f.read()) / 1000.0
        try:
            with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r") as f:
                cpu_freq = int(f.read()) / 1000
        except FileNotFoundError:
            cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else "N/A"
        return {
            "usage": round(cpu_percent, 1),
            "temp": round(cpu_temp, 1),
            "freq": round(cpu_freq, 1) if isinstance(cpu_freq, (int, float)) else cpu_freq
            }
    except Exception as e:
        print(f"[ERROR]: {e}")
        return {"usage": "N/A", "temp": "N/A", "freq": "N/A"}

def get_memory_info():
    """Get RAM memory information"""
    try:
        mem = psutil.virtual_memory()
        return {
            "percent": round(mem.percent, 1),
            "used": round(mem.used / 1024 / 1024 / 1024, 1),
            "available": round(mem.available / 1024 / 1024 / 1024, 1),  # 新增可用内存
            "total": round(mem.total / 1024 / 1024/ 1024, 1)
        }
    except Exception as e:
        print(f"[ERROR] Failed to get memory info: {e}")
        return {"percent": "N/A", "used": "N/A", "available": "N/A", "total": "N/A"}

def get_disk_info(path='/'):
    """Get disk space information"""
    try:
        disk = psutil.disk_usage(path)
        return {
            "percent": round(disk.percent, 1),
            "free": round(disk.free / 1024 / 1024 / 1024, 1),
            "total": round(disk.total / 1024 / 1024 / 1024, 1)
        }
    except Exception as e:
        print(f"[ERROR] Failed to get disk space: {e}")
        return {"percent": "N/A", "free": "N/A", "total": "N/A"}

# Global variables for network speed calculation
_last_net_stats = None
_last_net_time = 0

def init_network_speed():
    """Initialize network speed statistics"""
    global _last_net_stats, _last_net_time
    try:
        _last_net_stats = psutil.net_io_counters(pernic=True)
        _last_net_time = time.time()
    except:
        _last_net_stats = None

def get_network_speed():
    """Get network speed (non-blocking)"""
    global _last_net_stats, _last_net_time
    try:
        current_stats = psutil.net_io_counters(pernic=True)
        current_time = time.time()
        
        if _last_net_stats is None:
            init_network_speed()
            return {"upload": 0, "download": 0, "interface": "N/A"}
        
        time_delta = current_time - _last_net_time
        if time_delta <= 0.1:
            time_delta = 0.1
        
        speeds = []
        for iface in current_stats:
            if iface == 'lo':
                continue
            if iface in _last_net_stats:
                bytes_sent = current_stats[iface].bytes_sent - _last_net_stats[iface].bytes_sent
                bytes_recv = current_stats[iface].bytes_recv - _last_net_stats[iface].bytes_recv
                
                upload_speed = bytes_sent / time_delta
                download_speed = bytes_recv / time_delta
                
                if upload_speed > 0 or download_speed > 0:
                    speeds.append({
                        "interface": iface,
                        "upload": upload_speed,
                        "download": download_speed
                    })
        
        _last_net_stats = current_stats
        _last_net_time = current_time
        
        if not speeds:
            return {"upload": 0, "download": 0, "interface": "idle"}
        
        return max(speeds, key=lambda x: x['upload'] + x['download'])
        
    except Exception as e:
        print(f"[ERROR] Failed to get network speed: {e}")
        return {"upload": 0, "download": 0, "interface": "N/A"}

def format_network_speed(speed_dict):
    """Format network speed to readable string and return parts separately"""
    def format_speed(bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f}", "B"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec/1024:.1f}", "K"
        else:
            return f"{bytes_per_sec/1024/1024:.1f}", "M"
    
    upload_value, upload_unit = format_speed(speed_dict.get('upload', 0))
    download_value, download_unit = format_speed(speed_dict.get('download', 0))
    
    return {
        'upload_speed': f"↑{upload_value}",
        'upload_unit': upload_unit,
        'download_speed': f"↓{download_value}",
        'download_unit': download_unit
    }

def print_system_info(cpu_data, mem_data, disk_data, net_speed):
    """Print complete system information to terminal"""
    os.system('clear')
    
    print("\n" + "="*55)
    print(f"{BLUE}Raspberry Pi System Monitor (Refresh every 3s){RESET}")
    print("="*55)
    
    usage = cpu_data["usage"]
    usage_color = GREEN if usage < 50 else YELLOW if usage < 80 else RED
    print(f"【CPU】Usage: {usage_color}{usage:>6}% | Temp: {cpu_data['temp']:>5}°C | Freq: {cpu_data['freq']:>5}MHz{RESET}")
    
    mem_percent = mem_data["percent"]
    mem_color = GREEN if mem_percent < 50 else YELLOW if mem_percent < 80 else RED
    print(f"【RAM】Usage: {mem_color}{mem_percent:>6}% | Used: {mem_data['used']:>6.1f}/{mem_data['total']:>6.1f}MB{RESET}")
    
    disk_percent = disk_data["percent"]
    disk_color = GREEN if disk_percent < 70 else YELLOW if disk_percent < 85 else RED
    print(f"【DISK】Usage: {disk_color}{disk_percent:>6}% | Free: {disk_data['free']:>5.1f}/{disk_data['total']:>6.1f}GB{RESET}")
    
    # Get separated speed info for terminal display
    speed_info = format_network_speed(net_speed)
    print(f"【NET】{CYAN}{speed_info['upload_speed']}{speed_info['upload_unit']} {speed_info['download_speed']}{speed_info['download_unit']}{RESET}")
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"【TIME】{MAGENTA}{current_time}{RESET}")
    
    print("="*55)
    print(f"{YELLOW}Press Ctrl+C to exit{RESET}\n")

def draw_progress_bar(draw, x, y, width, height, used_percent, used_color, free_color):
    """Draw a progress bar with used/free sections"""
    try:
        # Calculate used width
        used_width = int(used_percent * width)
        
        # Draw background (free space)
        draw.rectangle((x, y, x + width, y + height), fill=free_color)
        
        # Draw foreground (used space)
        if used_width > 0:
            draw.rectangle((x, y, x + used_width, y + height), fill=used_color)
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to draw progress bar: {e}")
        return False

def draw_circular_progress_bar(draw, center_x, center_y, radius, line_width, percent, 
                               used_color, free_color):
    """Draw a circular progress bar at specified coordinates"""
    try:
        # Bounding box for the circle
        bbox = (center_x - radius, center_y - radius, 
                center_x + radius, center_y + radius)
        
        # Background circle (free space)
        draw.arc(bbox, start=-90, end=270, fill=free_color, width=line_width)
        
        # Foreground arc (used space) - clockwise from -90 degrees
        if percent > 0:
            end_angle = -90 + (3.6 * percent)  # 360 degrees / 100% = 3.6 per percent
            draw.arc(bbox, start=-90, end=end_angle, fill=used_color, width=line_width)
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to draw circular progress bar: {e}")
        return False
    
def draw_text_overlay(draw, cpu_data, mem_data, disk_data, net_speed):
    """Draw text and progress bars directly on background"""
    try:
        cpu_percent = float(cpu_data['usage']) if cpu_data['usage'] != 'N/A' else 0
        draw_circular_progress_bar(
            draw=draw,
            center_x=70,
            center_y=63,
            radius=40,      
            line_width=4,   
            percent=cpu_percent,
            used_color=USED_COLOR,
            free_color=FREE_COLOR
        )
        # Font definitions
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_time = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        font_date = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        
        # === Draw RAM Progress Bar (Extended) ===
        # RAM bar position: below RAM text with extended width
        ram_bar_x = 15
        ram_bar_y = 175
        ram_bar_width = 200  # Extended from 100 to 150
        ram_bar_height = 8
        
        # Calculate used percentage
        ram_used_percent = mem_data['percent'] / 100.0
        
        # Draw RAM progress bar
        draw_progress_bar(draw, ram_bar_x, ram_bar_y, ram_bar_width, ram_bar_height, 
                         ram_used_percent, USED_COLOR, FREE_COLOR)
        
        # === Draw ROM Progress Bar (Extended) ===
        # ROM bar position: below ROM text with extended width
        rom_bar_x = 15
        rom_bar_y = 205
        rom_bar_width = 200  # Extended from 100 to 150
        rom_bar_height = 8
        
        # Calculate used percentage
        rom_used_percent = disk_data['percent'] / 100.0
        
        # Draw ROM progress bar
        draw_progress_bar(draw, rom_bar_x, rom_bar_y, rom_bar_width, rom_bar_height, 
                         rom_used_percent, USED_COLOR, FREE_COLOR)
        
        # === Draw System Info Text ===
        # CPU Usage - coordinates (159, 44)
        cpu_usage_text = f"{cpu_data['usage']}%"
        draw.text((159, 40), cpu_usage_text, fill=TEXT_COLOR, font=font_small)
        
        cpu_usage_text_big = f"{cpu_data['usage']}%"
        draw.text((49, 51), cpu_usage_text_big, fill="ORANGE", font=font_date)
        cpu_usage_text_big = f"cpu"
        draw.text((60, 71), cpu_usage_text_big, fill="ORANGE", font=font_small)
        
        # CPU Temperature - coordinates (160, 72)
        cpu_temp_text = f"{cpu_data['temp']}°C"
        draw.text((160, 68), cpu_temp_text, fill=TEXT_COLOR, font=font_small)
        
        # CPU Frequency - coordinates (160, 100)
        cpu_freq_text = f"{cpu_data['freq']}MHz"
        draw.text((160, 96), cpu_freq_text, fill=TEXT_COLOR, font=font_small)
        
        # Memory Usage Title - coordinates (15, 160)
        mem_title_text = f"RAM:"
        draw.text((15, 160), mem_title_text, fill=TITLE_COLOR, font=font_time)
        mem_text = f"Available:{mem_data['available']:.1f}GB Total:{mem_data['total']:.1f}GB"
        draw.text((42, 160), mem_text, fill=TEXT_COLOR, font=font_time)

        # Disk Usage Title - coordinates (15, 190)
        disk_title_text = f"ROM:"
        draw.text((15, 190), disk_title_text, fill=TITLE_COLOR, font=font_time)
        disk_text = f"Available:{disk_data['free']:.1f}GB Total:{disk_data['total']:.1f}GB"
        draw.text((42, 190), disk_text, fill=TEXT_COLOR, font=font_time)
        
        # Network Speed - coordinates for values and units
        speed_info = format_network_speed(net_speed)
        draw.text((40, 284), speed_info['upload_speed'], fill=TEXT_COLOR, font=font_small)
        draw.text((50, 298), speed_info['upload_unit'], fill=TEXT_COLOR, font=font_small)
        draw.text((105, 284), speed_info['download_speed'], fill=TEXT_COLOR, font=font_small)
        draw.text((115, 298), speed_info['download_unit'], fill=TEXT_COLOR, font=font_small)
        
        # Time and Date Display - coordinates (180, 277) and (164, 294)
        now = datetime.now()
        time_text = now.strftime("%H:%M")
        date_text = now.strftime("%Y/%m/%d")
        draw.text((180, 277), time_text, fill=TEXT_COLOR, font=font_small)
        draw.text((164, 294), date_text, fill=TEXT_COLOR, font=font_small)
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to draw overlay: {e}")
        return False

def load_and_fit_image(image_path, target_size):
    """Load and resize image"""
    try:
        if not os.path.exists(image_path):
            print(f"{RED}[WARNING] Image file not found: {image_path}{RESET}")
            return None
        
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        return img
    except Exception as e:
        print(f"{RED}[ERROR] Image loading failed: {e}{RESET}")
        return None

def main():
    global disp
    
    # Image path configuration
    IMAGE_PATH = '/home/pi/Pictures/bj-03.png'
    bg_image = load_and_fit_image(IMAGE_PATH, (240, 320))
    
    if bg_image:
        print(f"{GREEN}[OK] Background image loaded successfully{RESET}")
    else:
        print(f"{YELLOW}[INFO] No background image, using solid color{RESET}")
    
    try:
        print(f"{CYAN}Starting Raspberry Pi System Monitor...{RESET}")
        

        
        # Initialize LCD
        disp = LCD_2inch8.LCD_2inch8()
        disp.Init()
        #disp.clear()
        image = Image.open('/home/pi/Pictures/LCD_2inch8.png')
        disp.ShowImage(image)
        # Initialize network statistics
        init_network_speed()
        #time.sleep(1)
        bus.write_i2c_block_data(address, 0x00, [0xFF, 0xFF])
        time.sleep(0.1)
        bus.write_i2c_block_data(address, 0x00, [0xFF, 0xF9])
        time.sleep(0.1)
        # Main monitoring loop
        while True:
            # Collect system data
            cpu_data = get_cpu_info()
            mem_data = get_memory_info()
            disk_data = get_disk_info('/')
            net_speed = get_network_speed()
            
            # Print to terminal
            print_system_info(cpu_data, mem_data, disk_data, net_speed)
            
            # LCD display: copy background image as drawing base
            if bg_image:
                image1 = bg_image.copy()
            else:
                image1 = Image.new("RGB", (disp.width, disp.height), "BLACK")
            
            draw = ImageDraw.Draw(image1)
            
            # Draw text and progress bars
            if not draw_text_overlay(draw, cpu_data, mem_data, disk_data, net_speed):
                print(f"{RED}[ERROR] Failed to draw overlay{RESET}")
            
            # Display to LCD
            disp.ShowImage(image1)
            
            # Wait 3 seconds
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n{YELLOW}User interrupted monitoring, exiting...{RESET}")
    finally:
        try:
            disp.module_exit()
            logging.info("LCD resources released")
        except:
            pass
        logging.info("Monitor program exited")

if __name__ == "__main__":
    main()


