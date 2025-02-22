# BrightLess: Intelligent Screen Brightness Management

## Overview

BrightLess is a screen brightness management tool that automatically adjusts your screen's brightness based on time of day, location, and sunrise/sunset cycles.

## Features

- 🌞 Automatic Brightness Adjustment
  - Dynamically changes screen brightness based on time of day
  - Uses sinusoidal curve for smooth brightness transitions
  - Configurable brightness range and base levels

- 🌅 Location-Based Sunrise/Sunset Tracking
  - Automatically detects sunrise and sunset times for your location
  - Adjusts brightness according to natural light conditions
  - Configurable via zipcode

- 🖥️ System Tray Control
  - Toggle between automatic and manual brightness modes
  - Quick access to brightness settings via system tray icon

## Prerequisites

- Python 3.8+
- Windows Operating System

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/BrightLess.git
   cd BrightLess
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Edit `brightness_config.json` to customize your brightness settings:

```json
{
    "brightness_function": {
        "type": "sinusoidal",
        "parameters": {
            "brightness_range_amplitude": 45,
            "base_brightness_level": 50,
            "daily_cycle_hours": 24,
            "day_night_curve_offset": -6
        }
    },
    "zipcode_config": {
        "zipcode": 12345,
        "use_sunrise_sunset": true,
        "sunrise_brightness": 40,
        "sunset_brightness": 1,
        "min_brightness_modifier": 1,
        "max_brightness_modifier": 100
    }
}
```

## Usage

Run the brightness scheduler:
```bash
python brightness_scheduler.py
```

The application will start and create a system tray icon. You can:
- Toggle between automatic and manual modes
- Exit the application from the tray menu

## Dependencies

- `screen-brightness-control`: Screen brightness manipulation
- `requests`: API calls for geolocation
- `astral`: Sun position and sunrise/sunset calculations
- `pystray`: System tray icon management
- `pillow`: Image processing for tray icon
