import json
import datetime
import screen_brightness_control as sbc
import time
from astral import LocationInfo
from astral.sun import sun
import requests

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
        tuple: (latitude, longitude) or None if not found
    """
    try:
        url = f"https://api.zippopotam.us/us/{zipcode}"
        response = requests.get(url)
        data = response.json()
        
        if 'places' in data and len(data['places']) > 0:
            place = data['places'][0]
            return float(place['latitude']), float(place['longitude'])
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
    
    coordinates = get_coordinates_from_zipcode(zipcode)
    if not coordinates:
        print(f"Could not find coordinates for zipcode {zipcode}")
        return None
    
    latitude, longitude = coordinates
    print(f"Coordinates for {zipcode}: Latitude {latitude}, Longitude {longitude}")  # Debug print
    
    # Use current date
    today = datetime.date.today()
    
    # Create location info
    location = LocationInfo('Custom Location', 'Region', 'UTC', latitude, longitude)
    
    # Get sun times
    sun_times = sun(location.observer, date=today)
    
    print(f"Sunrise time: {sun_times['sunrise'].time()}")  # Debug print
    print(f"Sunset time: {sun_times['sunset'].time()}")  # Debug print
    
    return (
        sun_times['sunrise'].time(), 
        sun_times['sunset'].time()
    )

def get_current_brightness_preset(config, current_time):
    """
    Determine the appropriate brightness level based on current time.
    
    Args:
        config (dict): Brightness configuration dictionary
        current_time (datetime.time): Current time
    
    Returns:
        int: Brightness level (0-100)
    """
    print(f"Current time: {current_time}")  # Debug print
    
    # First check if sunrise/sunset configuration is enabled
    sunrise_sunset_times = get_sunrise_sunset_times(config)
    
    if sunrise_sunset_times:
        sunrise_time, sunset_time = sunrise_sunset_times
        zipcode_config = config.get('zipcode_config', {})
        
        print(f"Sunrise time: {sunrise_time}")  # Debug print
        print(f"Sunset time: {sunset_time}")  # Debug print
        
        # Check if current time is between sunrise and sunset
        if sunrise_time <= current_time < sunset_time:
            brightness = zipcode_config.get('sunrise_brightness', 40)
            print(f"Daytime: Using sunrise brightness {brightness}")  # Debug print
            return brightness
        else:
            brightness = zipcode_config.get('sunset_brightness', 20)
            print(f"Nighttime: Using sunset brightness {brightness}")  # Debug print
            return brightness
    
    # Fallback to time presets if no sunrise/sunset config
    time_presets = config.get('time_presets', [])
    for preset in time_presets:
        start_time = datetime.datetime.strptime(preset['start_time'], '%H:%M').time()
        end_time = datetime.datetime.strptime(preset['end_time'], '%H:%M').time()
        
        # Handle midnight crossing
        if start_time < end_time:
            if start_time <= current_time < end_time:
                return preset['brightness']
        else:  # Crosses midnight
            if current_time >= start_time or current_time < end_time:
                return preset['brightness']
    
    # Default brightness if no preset matches
    return 50

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

def smooth_brightness_transition(start_brightness, target_brightness, duration=3, steps=10):
    """
    Smoothly transition screen brightness.
    
    Args:
        start_brightness (int): Starting brightness level
        target_brightness (int): Target brightness level
        duration (float): Total transition time in seconds
        steps (int): Number of intermediate brightness steps
    """
    # Ensure start and target are integers
    start_brightness = int(start_brightness)
    target_brightness = int(target_brightness)
    
    # Calculate step size and delay
    step_size = (target_brightness - start_brightness) / steps
    step_delay = duration / steps
    
    print(f"Transitioning brightness from {start_brightness}% to {target_brightness}%")
    
    # Perform smooth transition
    for step in range(1, steps + 1):
        # Calculate intermediate brightness
        intermediate_brightness = start_brightness + (step_size * step)
        
        # Set brightness and pause
        try:
            sbc.set_brightness(int(intermediate_brightness))
            time.sleep(step_delay)
        except Exception as e:
            print(f"Error during brightness transition: {e}")
            break
    
    # Ensure final brightness is exactly the target
    try:
        sbc.set_brightness(target_brightness)
    except Exception as e:
        print(f"Error setting final brightness: {e}")

def main():
    """Main function to set brightness based on current time."""
    try:
        config = load_brightness_config()
        current_time = datetime.datetime.now().time()
        recommended_brightness = get_current_brightness_preset(config, current_time)
        
        # Get current brightness
        current_brightness = get_current_brightness()
        
        # Only set brightness if recommended differs from current
        if current_brightness is not None:
            # Check if brightness needs adjustment (more than 5% difference)
            if abs(current_brightness - recommended_brightness) > 5:
                print(f"Adjusting brightness from {current_brightness}% to {recommended_brightness}%")
                smooth_brightness_transition(current_brightness, recommended_brightness)
            else:
                print(f"Current brightness of {current_brightness}% is close to recommended {recommended_brightness}%")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
