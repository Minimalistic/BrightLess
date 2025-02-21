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
from PIL import Image, ImageDraw
import sys

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
    Determine the appropriate brightness level by combining location-based constraints
    and time-based presets.
    
    Args:
        config (dict): Brightness configuration dictionary
        current_time (datetime.time): Current time
    
    Returns:
        int: Brightness level (0-100)
    """
    # Get zipcode configuration and time presets
    zipcode_config = config.get('zipcode_config', {})
    time_presets = config.get('time_presets', [])
    
    # Get brightness modifiers, defaulting to full range if not specified
    min_brightness = zipcode_config.get('min_brightness_modifier', 1)
    max_brightness = zipcode_config.get('max_brightness_modifier', 100)
    
    # Check if sunrise/sunset configuration is enabled
    sunrise_sunset_times = get_sunrise_sunset_times(config)
    
    # Find the matching time preset
    matching_preset = None
    for preset in time_presets:
        start_time = datetime.strptime(preset['start_time'], '%H:%M').time()
        end_time = datetime.strptime(preset['end_time'], '%H:%M').time()
        
        # Handle time ranges that cross midnight
        if start_time <= end_time:
            in_range = start_time <= current_time < end_time
        else:
            in_range = current_time >= start_time or current_time < end_time
        
        if in_range:
            matching_preset = preset
            break
    
    # Default brightness if no preset found
    base_brightness = 50
    
    # Use sunrise/sunset times if enabled and available
    if sunrise_sunset_times and zipcode_config.get('use_sunrise_sunset', False):
        sunrise_time, sunset_time = sunrise_sunset_times
        
        if sunrise_time <= current_time < sunset_time:
            base_brightness = zipcode_config.get('sunrise_brightness', base_brightness)
        else:
            base_brightness = zipcode_config.get('sunset_brightness', base_brightness)
    
    # If a time preset is found, use its brightness
    if matching_preset:
        base_brightness = matching_preset['brightness']
    
    # Apply min and max brightness constraints
    brightness = min(max_brightness, max(min_brightness, base_brightness))
    
    print(f"Brightness calculation - Current time: {current_time}, Base brightness: {base_brightness}, Final brightness: {brightness}")
    
    return brightness

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

def create_tray_icon():
    """Create a system tray icon with a menu."""
    def create_image():
        # Create a blank image for the tray icon
        image = Image.new('RGB', (64, 64), color = (73, 109, 137))
        d = ImageDraw.Draw(image)
        d.rectangle([0, 0, 63, 63], outline=(255, 255, 255))
        return image

    def on_exit(icon):
        icon.stop()
        sys.exit(0)

    def manual_brightness(brightness_level):
        try:
            sbc.set_brightness(brightness_level)
            print(f"Manually set brightness to {brightness_level}%")
        except Exception as e:
            print(f"Error setting brightness: {e}")

    # Create the system tray icon
    icon = pystray.Icon("ChromaDim", create_image())
    
    # Define menu items
    icon.menu = pystray.Menu(
        pystray.MenuItem("100% Brightness", lambda: manual_brightness(100)),
        pystray.MenuItem("75% Brightness", lambda: manual_brightness(75)),
        pystray.MenuItem("50% Brightness", lambda: manual_brightness(50)),
        pystray.MenuItem("25% Brightness", lambda: manual_brightness(25)),
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
