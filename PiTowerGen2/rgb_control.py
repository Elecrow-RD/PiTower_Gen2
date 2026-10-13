from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
import time
import colorsys
import signal
import sys
from enum import Enum, auto
from typing import Callable, List


class AnimationMode(Enum):
    """Enumeration of supported animation modes"""
    RAINBOW_GRADIENT = auto()      # All LEDs synchronized smooth gradient
    FLOW_FORWARD = auto()          # Rainbow gradient wave flowing forward from first LED
    FLOW_BACKWARD = auto()         # Rainbow gradient wave flowing backward from last LED
    TRAIL_FORWARD = auto()         # Color trail dragging forward on black background
    TRAIL_FORWARD_ON = auto()      # Static rainbow background + forward trail movement
    TRAIL_BACKWARD_ON = auto()     # Static rainbow background + backward trail movement
    GREEN_BASE_FORWARD = auto()    # Green background with blue flowing forward from first LED (interval 5)
    GREEN_BASE_BACKWARD = auto()   # Green background with blue flowing backward from last LED (interval 5)
    COLOR_RUN = auto()             # Rainbow color run: all LEDs on, discrete rainbow flowing
    GRB_FILL = auto()              # Green-Red-Blue color fill wave (cumulative lighting)
    BREATHING_RAINBOW = auto()     # Rainbow breathing: 7 colors cycle, each fades max→min→max


class LedAnimator:
    """WS2812 LED Animation Controller with multi-mode support"""
    
    def __init__(self, led_count: int = 34, spi_bus: int = 1, spi_device: int = 0):
        """Initialize LED strip and animation parameters"""
        self.led_count = led_count
        self.strip = WS2812SpiDriver(
            spi_bus=spi_bus, 
            spi_device=spi_device, 
            led_count=led_count
        ).get_strip()
        
        # Core animation parameters
        self.animation_speed = 0.05
        self.brightness = 205
        
        # Mode 1: Smooth gradient
        self.hue_offset = 0.0
        self.hue_increment = 0.03
        
        # Modes 2-11: Flow/Trail/Breathing parameters
        self.flow_offset = 0.0
        self.trail_speed = 1.0
        
        # GRB fill parameters
        self.grb_colors = [
            Color(0, 5, 0),   # Green
            Color(5, 0, 0),   # Red
            Color(0, 0, 5),   # Blue
        ]
        self.grb_color_index = 0
        self.grb_position = 0  # Current fill position (0-34)
        
        # Breathing rainbow parameters
        self.breathing_color_index = 0  # Current color in sequence
        self.breathing_brightness = 1.0  # Current brightness (1.0 = max, 0.0 = min)
        self.breathing_direction = -1   # -1 = fading out, 1 = fading in
        self.breathing_speed = 0.02     # Brightness change per frame
        self.color_sequence = [0.0, 0.08, 0.16, 0.33, 0.5, 0.66, 0.83]  # 7 rainbow colors
        
        # Frame counter
        self.frame_counter = 0
        
        # Internal buffers
        self._pixel_buffer: List[Color] = [Color(0, 0, 0)] * self.led_count
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._cleanup)
        signal.signal(signal.SIGTERM, self._cleanup)
    
    def _cleanup(self, signum, frame):
        """Clean up LED state and exit gracefully"""
        print("\n[CLEANUP] Turning off all LEDs...")
        self.strip.set_all_pixels(Color(0, 0, 0))
        self.strip.show()
        sys.exit(0)
    
    def hsv_to_color(self, h: float, s: float = 1.0, v: float = 1.0) -> Color:
        """Convert HSV to WS2812 Color with brightness limiting"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return Color(
            int(r * self.brightness),
            int(g * self.brightness),
            int(b * self.brightness)
        )
    
    def _apply_brightness_to_color(self, color: Color) -> Color:
        """Apply brightness scaling to a direct Color object"""
        return Color(
            int(color.r * self.brightness / 5),  # Divide by 5 because base colors use 0-5 range
            int(color.g * self.brightness / 5),
            int(color.b * self.brightness / 5)
        )
    
    def _get_smooth_color(self) -> Color:
        """Get continuously changing color for smooth gradient"""
        color = self.hsv_to_color(self.hue_offset)
        self.hue_offset = (self.hue_offset + self.hue_increment) % 1.0
        return color
    
    def _get_discrete_color(self) -> Color:
        """Get current discrete color from sequence"""
        hue = self.color_sequence[self.color_index]
        return self.hsv_to_color(hue)
    
    def _advance_discrete_color(self):
        """Advance to next discrete color"""
        self.color_index = (self.color_index + 1) % len(self.color_sequence)
    
    def _apply_fade(self, color: Color, factor: float) -> Color:
        """Apply fade effect to color"""
        return Color(
            int(color.r * factor),
            int(color.g * factor),
            int(color.b * factor)
        )
    
    # ==================== Eleven Animation Modes ====================
    
    def rainbow_gradient(self):
        """Mode 1: All LEDs synchronized smooth gradient"""
        current_color = self._get_smooth_color()
        self.strip.set_all_pixels(current_color)
        self.strip.show()
    
    def rainbow_flow_forward(self):
        """Mode 2: Rainbow wave flowing forward from first LED"""
        for i in range(self.led_count):
            hue = ((i / self.led_count) * 0.8 + self.flow_offset) % 1.0
            self.strip.set_pixel_color(i, self.hsv_to_color(hue))
        self.strip.show()
        self.flow_offset = (self.flow_offset + 0.02) % 1.0
    
    def rainbow_flow_backward(self):
        """Mode 3: Rainbow wave flowing backward from last LED"""
        for i in range(self.led_count):
            hue = ((i / self.led_count) * 0.8 - self.flow_offset) % 1.0
            self.strip.set_pixel_color(i, self.hsv_to_color(hue))
        self.strip.show()
        self.flow_offset = (self.flow_offset + 0.02) % 1.0
    
    def rainbow_trail(self):
        """Mode 4: Color trail dragging forward on black background"""
        self._pixel_buffer = [
            self._apply_fade(color, 0.85) 
            for color in self._pixel_buffer
        ]
        
        # ? Use continuous rainbow color instead of discrete colors
        head_color = self.hsv_to_color(self.hue_offset)
        self.hue_offset = (self.hue_offset + 0.02) % 1.0  # Advance hue for smooth rainbow effect
        
        self._pixel_buffer[int(self.flow_offset) % self.led_count] = head_color
        
        for i, color in enumerate(self._pixel_buffer):
            self.strip.set_pixel_color(i, color)
        self.strip.show()
        
        self.flow_offset = (self.flow_offset + self.trail_speed) % self.led_count
        
        self.frame_counter += 1
    
    def rainbow_trail_forward_on(self):
        """Mode 5: Static rainbow background + forward trail movement"""
        # Static rainbow background
        for i in range(self.led_count):
            static_hue = (i / self.led_count) * 0.8
            self.strip.set_pixel_color(i, self.hsv_to_color(static_hue))
        
        # Moving highlight trail
        trail_head = int(self.flow_offset) % self.led_count
        for j in range(5):
            pos = (trail_head - j) % self.led_count
            brightness = 1.0 - (j / 5)
            enhanced = self.hsv_to_color(self.color_sequence[self.color_index], v=brightness * 2.0)
            self.strip.set_pixel_color(pos, enhanced)
        
        self.strip.show()
        self.flow_offset = (self.flow_offset + self.trail_speed) % self.led_count
        
        if self.frame_counter % 30 == 0:
            self._advance_discrete_color()
        
        self.frame_counter += 1
    
    def rainbow_trail_backward_on(self):
        """Mode 6: Static rainbow background + backward trail movement"""
        # Static rainbow background
        for i in range(self.led_count):
            static_hue = (i / self.led_count) * 0.8
            self.strip.set_pixel_color(i, self.hsv_to_color(static_hue))
        # Backward moving highlight trail (moves from LED34→LED0)
        trail_head = int(self.flow_offset) % self.led_count
        for j in range(5):
            pos = (trail_head + j) % self.led_count
            brightness = 1.0 - (j / 5)
            enhanced = self.hsv_to_color(self.color_sequence[self.color_index], v=brightness * 2.0)
            self.strip.set_pixel_color(pos, enhanced)
        self.strip.show()
        # ? Move backward (decrement instead of increment)
        self.flow_offset = (self.flow_offset - self.trail_speed) % self.led_count
        if self.frame_counter % 30 == 0:
            self._advance_discrete_color()
        self.frame_counter += 1
    
    def green_base_forward(self):
        """Mode 7: Green background with blue flowing forward from first LED (interval 5)"""
        green = self._apply_brightness_to_color(Color(0, 5, 0))
        blue = self._apply_brightness_to_color(Color(0, 0, 5))
        blue_position = int(self.flow_offset) % self.led_count
        
        for i in range(self.led_count):
            if (i - blue_position) % 6 == 0:
                self.strip.set_pixel_color(i, blue)
            else:
                self.strip.set_pixel_color(i, green)
        
        self.strip.show()
        self.flow_offset = (self.flow_offset + 1) % self.led_count
    
    def green_base_backward(self):
        """Mode 8: Green background with blue flowing backward from last LED (interval 5)"""
        green = self._apply_brightness_to_color(Color(0, 5, 0))
        blue = self._apply_brightness_to_color(Color(0, 0, 5))
        blue_position = int(self.flow_offset) % self.led_count
        
        for i in range(self.led_count):
            if (i + blue_position) % 6 == 0:
                self.strip.set_pixel_color(i, blue)
            else:
                self.strip.set_pixel_color(i, green)
        
        self.strip.show()
        self.flow_offset = (self.flow_offset + 1) % self.led_count
    
    def color_run(self):
        """Mode 9: Rainbow color run: all LEDs on, discrete rainbow flowing"""
        # Each LED displays a color from sequence, sequence flows across strip
        for i in range(self.led_count):
            color_idx = (i + int(self.flow_offset)) % len(self.color_sequence)
            hue = self.color_sequence[color_idx]
            self.strip.set_pixel_color(i, self.hsv_to_color(hue))
        
        self.strip.show()
        self.flow_offset = (self.flow_offset + self.trail_speed) % self.led_count
        
        self.frame_counter += 1
    
    # ========================================
    # Green-Red-Blue Color Fill Wave (Cumulative Lighting)
    # ========================================
    def grb_fill(self):
        """Mode 10: Green-Red-Blue color fill wave (cumulative lighting from LED0)"""
        
        # Phase 1: Green fill
        if self.grb_color_index == 0:
            # Light up LEDs from 0 to grb_position in green, others off
            current_color = self._apply_brightness_to_color(Color(0, 5, 0))
            for i in range(self.led_count):
                if i <= self.grb_position:
                    self.strip.set_pixel_color(i, current_color)
                else:
                    self.strip.set_pixel_color(i, Color(0, 0, 0))
            
            self.strip.show()
            self.grb_position += 1
            
            # When entire strip is filled, switch to red
            if self.grb_position >= self.led_count:
                self.grb_color_index = 1  # Switch to red
                self.grb_position = 0
                print(f"[GRB-FILL] Green filled, switching to Red")
        
        # Phase 2: Red fill
        elif self.grb_color_index == 1:
            current_color = self._apply_brightness_to_color(Color(5, 0, 0))
            for i in range(self.led_count):
                if i <= self.grb_position:
                    self.strip.set_pixel_color(i, current_color)
                else:
                    self.strip.set_pixel_color(i, Color(0, 0, 0))
            
            self.strip.show()
            self.grb_position += 1
            
            if self.grb_position >= self.led_count:
                self.grb_color_index = 2  # Switch to blue
                self.grb_position = 0
                print(f"[GRB-FILL] Red filled, switching to Blue")
        
        # Phase 3: Blue fill
        elif self.grb_color_index == 2:
            current_color = self._apply_brightness_to_color(Color(0, 0, 5))
            for i in range(self.led_count):
                if i <= self.grb_position:
                    self.strip.set_pixel_color(i, current_color)
                else:
                    self.strip.set_pixel_color(i, Color(0, 0, 0))
            
            self.strip.show()
            self.grb_position += 1
            
            if self.grb_position >= self.led_count:
                self.grb_color_index = 0  # Cycle back to green
                self.grb_position = 0
                print(f"[GRB-FILL] Blue filled, cycling to Green")
        
        self.frame_counter += 1
    
    # ========================================
    # Rainbow Breathing Light Effect (7 Colors, Each Fades Max→Min→Max)
    # ========================================
    def breathing_rainbow(self):
        """Mode 11: Rainbow breathing light effect (7 colors cycle, each fades max→min→max)"""
        
        # Update brightness for breathing effect
        self.breathing_brightness += self.breathing_direction * self.breathing_speed
        
        # Reverse direction at boundaries
        if self.breathing_brightness >= 1.0:
            self.breathing_brightness = 1.0
            self.breathing_direction = -1  # Start fading out
        elif self.breathing_brightness <= 0.0:
            self.breathing_brightness = 0.0
            self.breathing_direction = 1   # Start fading in
            
            # ? When reaching minimum, switch to next color in sequence
            self.breathing_color_index = (self.breathing_color_index + 1) % len(self.color_sequence)
        
        # Get current rainbow color with breathing brightness applied
        current_hue = self.color_sequence[self.breathing_color_index]
        current_color = self.hsv_to_color(current_hue, v=self.breathing_brightness)
        
        # Apply to all LEDs
        self.strip.set_all_pixels(current_color)
        self.strip.show()
        
        self.frame_counter += 1
    
    # ==================== Run Control ====================
    
    def run_animation(self, mode: AnimationMode, duration: float = None):
        """Run animation mode with optional duration"""
        animation_methods: dict[AnimationMode, Callable] = {
            AnimationMode.RAINBOW_GRADIENT: self.rainbow_gradient,
            AnimationMode.FLOW_FORWARD: self.rainbow_flow_forward,
            AnimationMode.FLOW_BACKWARD: self.rainbow_flow_backward,
            AnimationMode.TRAIL_FORWARD: self.rainbow_trail,
            AnimationMode.TRAIL_FORWARD_ON: self.rainbow_trail_forward_on,
            AnimationMode.TRAIL_BACKWARD_ON: self.rainbow_trail_backward_on,
            AnimationMode.GREEN_BASE_FORWARD: self.green_base_forward,
            AnimationMode.GREEN_BASE_BACKWARD: self.green_base_backward,
            AnimationMode.COLOR_RUN: self.color_run,
            AnimationMode.GRB_FILL: self.grb_fill,
            AnimationMode.BREATHING_RAINBOW: self.breathing_rainbow,
        }
        
        if mode not in animation_methods:
            raise ValueError(f"Unsupported mode: {mode}")
        
        # Reset all animation parameters
        self.flow_offset = 0.0
        self.color_index = 0
        self.frame_counter = 0
        self.hue_offset = 0.0
        self.grb_color_index = 0
        self.grb_position = 0
        self.breathing_brightness = 1.0  # Start at max brightness
        self.breathing_direction = -1    # Start fading out
        self.breathing_color_index = 0
        self._pixel_buffer = [Color(0, 0, 0)] * self.led_count
        
        method = animation_methods[mode]
        start_time = time.time()
        
        print(f"[INFO] {mode.name} | LEDs: {self.led_count} | Speed: {self.animation_speed}s")
        print(f"[INFO] Sequence: Red→Orange→Yellow→Green→Cyan→Blue→Purple, each fades max→min→max")
        print("[INFO] Press Ctrl+C to exit")
        
        try:
            while True:
                method()
                time.sleep(self.animation_speed)
                
                if duration and (time.time() - start_time) >= duration:
                    print(f"[INFO] Completed ({duration}s)")
                    break
        except KeyboardInterrupt:
            self._cleanup(signal.SIGINT, None)
    
    def cycle_modes(self, mode_duration: float = 15.0):
        """Cycle through all 11 modes sequentially"""
        modes = list(AnimationMode)
        
        print(f"\n{'='*60}")
        print(f"STARTING MODE CYCLE | {len(modes)} modes | {mode_duration}s each")
        print(f"{'='*60}")
        
        for idx, mode in enumerate(modes):
            print(f"\n[MODE {idx+1}/{len(modes)}] {mode.name}")
            print("-" * 40)
            
            self.run_animation(mode, duration=mode_duration)
            time.sleep(0.5)
        
        print("\n?? Cycle completed. Restarting...\n")
        time.sleep(2)
        self.cycle_modes(mode_duration=mode_duration)


def main():
    # Configuration
    CONFIG = {
        'led_count': 34,
        'spi_bus': 1,
        'spi_device': 0,
        'default_mode': AnimationMode.BREATHING_RAINBOW,
        'cycle_modes': True,  # Enable all modes auto cycle
        'mode_duration': 15.0,  # Each mode runs for 15 seconds
    }
    
    animator = LedAnimator(
        led_count=CONFIG['led_count'],
        spi_bus=CONFIG['spi_bus'],
        spi_device=CONFIG['spi_device']
    )
    
    # Adjustable parameters
    animator.animation_speed = 0.05      # Frame rate
    animator.breathing_speed = 0.02      # Breathing speed (0.01=slow, 0.05=fast)
    
    try:
        if CONFIG['cycle_modes']:
            print(f"\n{'='*60}")
            print(f"?? Starting 11-mode automatic cycle")
            print(f"??  Duration per mode: {CONFIG['mode_duration']}s")
            print(f"?? Cycle order: Rainbow_Gradient → Flow_Forward → Flow_Backward → Trail_Forward → Trail_Forward_On → Trail_Backward_On → Green_Base_Forward → Green_Base_Backward → Color_Run → GRB_Fill → Breathing_Rainbow")
            print(f"{'='*60}")
            animator.cycle_modes(mode_duration=CONFIG['mode_duration'])
        else:
            print("\n[INFO] Single mode mode. Press Ctrl+C to exit.")
            animator.run_animation(CONFIG['default_mode'])
    except KeyboardInterrupt:
        animator._cleanup(signal.SIGINT, None)
    except Exception as e:
        print(f"[ERROR] {e}")
        animator._cleanup(signal.SIGTERM, None)


if __name__ == "__main__":
    main()