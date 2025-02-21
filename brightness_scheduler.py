import json
import time as py_time
from datetime import datetime, time
import screen_brightness_control as sbc
import requests
from astral import LocationInfo
from astral.sun import sun
import zoneinfo
import threading
import pystray
from PIL import Image
import sys
import math

# Global variable to track brightness mode
BRIGHTNESS_MODE = 'auto'

def load_brightness_config(config_path='brightness_config.json'):
    """Load brightness configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def get_coordinates_from_zipcode(zipcode):
    """
    Fetch latitude and longitude for a given zipcode using a free geocoding API.
    
    Args:
        zipcode (str): US Zipcode
    
    Returns:
        tuple: (latitude, longitude, timezone) or None if not found
    """
    try:
        url = f"https://api.zippopotam.us/us/{zipcode}"
        response = requests.get(url)
        data = response.json()
        
        if 'places' in data and len(data['places']) > 0:
            place = data['places'][0]
            # Attempt to get timezone based on location
            timezone_str = f"US/Central"  # Default to Central Time
            return (
                float(place['latitude']), 
                float(place['longitude']), 
                timezone_str
            )
    except Exception as e:
        print(f"Error getting coordinates for zipcode {zipcode}: {e}")
    
    return None

def get_sunrise_sunset_times(config):
    """
    Get sunrise and sunset times based on zipcode configuration.
    
    Args:
        config (dict): Configuration dictionary
    
    Returns:
        tuple: (sunrise_time, sunset_time) or None
    """
    zipcode_config = config.get('zipcode_config', {})
    
    print(f"Zipcode Config: {zipcode_config}")  # Debug print
    
    if not zipcode_config.get('use_sunrise_sunset', False):
        print("Sunrise/sunset is not enabled in configuration")  # Debug print
        return None
    
    zipcode = zipcode_config.get('zipcode')
    if not zipcode:
        print("No zipcode specified for sunrise/sunset configuration.")
        return None
    
    coordinates = get_coordinates_from_zipcode(str(zipcode))
    if not coordinates:
        print(f"Could not find coordinates for zipcode {zipcode}")
        return None
    
    latitude, longitude, timezone_str = coordinates
    print(f"Coordinates for {zipcode}: Latitude {latitude}, Longitude {longitude}, Timezone {timezone_str}")  # Debug print
    
    # Use current date in local timezone
    today = datetime.today()
    local_tz = zoneinfo.ZoneInfo(timezone_str)
    
    # Create location info with timezone
    location = LocationInfo('Custom Location', 'Region', timezone_str, latitude, longitude)
    
    # Get sun times with local timezone
    sun_times = sun(location.observer, date=today, tzinfo=local_tz)
    
    print(f"Sunrise time (local): {sun_times['sunrise']}")  # Debug print
    print(f"Sunset time (local): {sun_times['sunset']}")  # Debug print
    
    return (
        sun_times['sunrise'].time(), 
        sun_times['sunset'].time()
    )

def get_current_brightness_preset(config, current_time):
    """
    Determine the appropriate brightness level using a mathematical brightness function.
    
    Args:
        config (dict): Brightness configuration dictionary
        current_time (datetime.time): Current time
    
    Returns:
        int: Brightness level (0-100)
    """
    # Get zipcode configuration and brightness function
    zipcode_config = config.get('zipcode_config', {})
    brightness_func = config.get('brightness_function', {})
    
    # Get brightness modifiers, defaulting to full range if not specified
    min_brightness = zipcode_config.get('min_brightness_modifier', 1)
    max_brightness = zipcode_config.get('max_brightness_modifier', 100)
    
    # Get sunrise/sunset times if enabled
    sunrise_sunset_times = get_sunrise_sunset_times(config)
    
    # Default base brightness calculation using sinusoidal function
    if brightness_func.get('type') == 'sinusoidal':
        params = brightness_func.get('parameters', {})
        amplitude = params.get('brightness_range_amplitude', 45)
        midpoint = params.get('base_brightness_level', 50)
        period = params.get('daily_cycle_hours', 24)
        phase_shift = params.get('day_night_curve_offset', -6)
        
        # Convert current time to hours since midnight
        hours_since_midnight = current_time.hour + current_time.minute / 60
        
        # Apply phase shift and calculate sinusoidal brightness
        base_brightness = midpoint + amplitude * math.sin(
            2 * math.pi * (hours_since_midnight + phase_shift) / period
        )
    else:
        base_brightness = 50  # Fallback default
    
    # Override with sunrise/sunset times if enabled
    if sunrise_sunset_times and zipcode_config.get('use_sunrise_sunset', False):
        sunrise_time, sunset_time = sunrise_sunset_times
        
        if sunrise_time <= current_time < sunset_time:
            base_brightness = max(base_brightness, zipcode_config.get('sunrise_brightness', base_brightness))
        else:
            base_brightness = min(base_brightness, zipcode_config.get('sunset_brightness', base_brightness))
    
    # Apply min and max brightness constraints
    brightness = min(max_brightness, max(min_brightness, base_brightness))
    
    print(f"Brightness calculation - Current time: {current_time}, Mathematical brightness: {brightness}")
    
    return round(brightness)

def get_current_brightness():
    """
    Get the current screen brightness.
    
    Returns:
        int: Current brightness level (0-100)
    """
    try:
        # Get brightness for all displays
        brightness_levels = sbc.get_brightness()
        
        # If multiple displays, return the first one's brightness
        if brightness_levels:
            current_brightness = brightness_levels[0]
            print(f"Current screen brightness: {current_brightness}%")
            return current_brightness
        else:
            print("No displays found.")
            return None
    except Exception as e:
        print(f"Error getting current brightness: {e}")
        return None

def smooth_brightness_transition(start_brightness, target_brightness, duration=3, steps=20):
    """
    Smoothly transition screen brightness using an ease-in-out quadratic function.
    
    Args:
        start_brightness (int): Starting brightness level
        target_brightness (int): Target brightness level
        duration (float): Total transition time in seconds
        steps (int): Number of intermediate brightness steps
    """
    try:
        # Ensure brightness is within 0-100 range
        start_brightness = max(0, min(100, start_brightness))
        target_brightness = max(0, min(100, target_brightness))
        
        # Calculate step delay
        step_delay = duration / steps
        
        # Calculate brightness increments
        brightness_diff = target_brightness - start_brightness
        
        for step in range(steps + 1):
            # Use ease-in-out quadratic interpolation
            t = step / steps
            # Quadratic ease-in-out formula
            interpolation = (t < 0.5) * (2 * t * t) + (t >= 0.5) * (-2 * t * t + 4 * t - 1)
            
            current_brightness = int(start_brightness + (brightness_diff * interpolation))
            
            # Set brightness
            sbc.set_brightness(current_brightness)
            
            # Wait between steps
            py_time.sleep(step_delay)
        
        # Ensure final brightness is set exactly
        sbc.set_brightness(target_brightness)
        
    except Exception as e:
        print(f"Error during brightness transition: {e}")
        # Fallback to direct brightness set if transition fails
        sbc.set_brightness(target_brightness)

def toggle_brightness_mode(mode='auto'):
    """
    Toggle between manual and auto brightness modes.
    
    Args:
        mode (str): Mode to switch to. Default is 'auto'.
    """
    global BRIGHTNESS_MODE
    BRIGHTNESS_MODE = mode
    
    if mode == 'auto':
        # Load configuration
        config = load_brightness_config()
        
        # Get current time and corresponding brightness preset
        current_time = datetime.now(zoneinfo.ZoneInfo(config.get('timezone', 'US/Central'))).time()
        target_brightness = get_current_brightness_preset(config, current_time)
        
        # Immediately set brightness to current time-based preset
        try:
            current_brightness = get_current_brightness()
            smooth_brightness_transition(current_brightness, target_brightness)
            print(f"Switched to auto brightness mode. Setting brightness to {target_brightness}%")
        except Exception as e:
            print(f"Error reverting to auto brightness: {e}")
    else:
        print(f"Switched to manual brightness mode: {mode}")

def create_tray_icon():
    """Create a system tray icon with a menu."""
    def on_exit(icon):
        icon.stop()
        sys.exit(0)

    def manual_brightness(brightness_level):
        try:
            # Switch to manual mode when manually setting brightness
            toggle_brightness_mode(f'{brightness_level}%')
            sbc.set_brightness(brightness_level)
            print(f"Manually set brightness to {brightness_level}%")
        except Exception as e:
            print(f"Error setting brightness: {e}")

    # Create the system tray icon with the custom brightness icon
    icon = pystray.Icon("ChromaDim", Image.open("brightness_icon.ico"))
    
    # Define menu items
    icon.menu = pystray.Menu(
        pystray.MenuItem("100% Brightness", lambda: manual_brightness(100)),
        pystray.MenuItem("75% Brightness", lambda: manual_brightness(75)),
        pystray.MenuItem("50% Brightness", lambda: manual_brightness(50)),
        pystray.MenuItem("25% Brightness", lambda: manual_brightness(25)),
        pystray.MenuItem("1% Brightness", lambda: manual_brightness(1)),
        pystray.MenuItem("Re-enable Auto Brightness", lambda: toggle_brightness_mode()),
        pystray.MenuItem("Exit", on_exit)
    )
    
    return icon

def run_tray_icon(icon):
    """Run the system tray icon in a separate thread."""
    icon.run()

def main():
    # Load configuration
    config = load_brightness_config()
    
    # Create system tray icon
    tray_icon = create_tray_icon()
    
    # Start tray icon in a separate thread
    tray_thread = threading.Thread(target=run_tray_icon, args=(tray_icon,), daemon=True)
    tray_thread.start()
    
    try:
        while True:
            # Check if we're in auto mode
            if BRIGHTNESS_MODE == 'auto':
                # Existing brightness scheduling logic
                current_time = datetime.now(zoneinfo.ZoneInfo(config.get('timezone', 'US/Central'))).time()
                target_brightness = get_current_brightness_preset(config, current_time)
                current_brightness = get_current_brightness()
                
                # Smoothly transition brightness if needed
                if abs(current_brightness - target_brightness) > 5:
                    smooth_brightness_transition(current_brightness, target_brightness)
            
            # Sleep for a while before next check
            py_time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("Brightness scheduler stopped.")
    finally:
        tray_icon.stop()

if __name__ == "__main__":
    main()
