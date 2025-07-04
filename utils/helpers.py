"""
Helper utilities for Typhoon Weather Monitor
"""

import logging

logger = logging.getLogger(__name__)

# Global data storage that can be imported by any module
global_data = {
    'latest_alerts': {},
    'latest_weather': {},
    'latest_typhoons': {},
    'tainan_weekly_weather': {}
}

def update_global_data(alerts_data, typhoons_data, weather_data, tainan_weekly_data=None):
    """Update global data that can be accessed by any module"""
    global global_data
    global_data['latest_alerts'] = alerts_data if not isinstance(alerts_data, Exception) else {}
    global_data['latest_typhoons'] = typhoons_data if not isinstance(typhoons_data, Exception) else {}
    global_data['latest_weather'] = weather_data if not isinstance(weather_data, Exception) else {}
    if tainan_weekly_data is not None:
        global_data['tainan_weekly_weather'] = tainan_weekly_data if not isinstance(tainan_weekly_data, Exception) else {}

def get_global_data():
    """Get the current global data"""
    return global_data