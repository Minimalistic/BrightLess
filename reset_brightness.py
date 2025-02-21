import screen_brightness_control as sbc

def reset_brightness():
    """
    Reset screen brightness to 100% for all connected monitors.
    """
    try:
        # Get all connected monitors
        monitors = sbc.list_monitors()
        
        # Set brightness to 100% for each monitor
        for monitor in monitors:
            sbc.set_brightness(100, display=monitor)
        
        print(f"Screen brightness reset to 100% for {len(monitors)} monitor(s)")
    except Exception as e:
        print(f"Error resetting brightness: {e}")

if __name__ == "__main__":
    reset_brightness()
