"""
Constants and templates for Typhoon Weather Monitor
"""

# Risk assessment constants
THREAT_RADII = {
    "direct": 200,      # 直接威脅半徑 (公里)
    "moderate": 400,    # 中等威脅半徑 (公里)
    "indirect": 600     # 間接威脅半徑 (公里)
}

# Taiwan region coordinates
TAIWAN_REGIONS = {
    "台北": (25.0, 121.5),
    "台中": (24.1, 120.7), 
    "台南": (23.0, 120.2),
    "高雄": (22.6, 120.3),
    "金門": (24.4, 118.3),
    "澎湖": (23.6, 119.6)
}

# Key regions for detailed timing analysis
KEY_REGIONS = {
    "金門": (24.4, 118.3),
    "台南": (23.0, 120.2)
}

# Warning message templates
WARNING_TEMPLATES = {
    "typhoon_forecast": "📍 {name}預報將在 {tau} 小時後接近{region}區域 (距離{distance:.0f}km)",
    "typhoon_current": "🌀 {name} 最大風速: {wind_speed} m/s ({wind_kmh:.1f} km/h) - {threat_level}{distance_info}",
    "weather_alert": "⚠️ {location}: {phenomena} {significance}",
    "weather_forecast": "🌧️ {location} {start_time}: {weather_desc}",
    "typhoon_timing": "⏰ {name}預計{action}{region}時間: {time_str} ({tau}小時後)",
    "typhoon_summary": "📊 {name}影響{region}時間預估: 接近 {approach_time}, 離開 {depart_time}"
}

# Risk level mappings
RISK_LEVELS = {
    "high": "高風險",
    "medium": "中風險", 
    "low": "低風險",
    "none": "無風險"
}

# Travel risk messages
TRAVEL_RISK_MESSAGES = {
    "flight_cancelled": "高風險 - 航班已停飛/取消",
    "typhoon_high": "高風險 - 建議考慮改期 (基於天氣預報)",
    "typhoon_forecast": "中風險 - 航班可能延誤 (基於天氣預報)",
    "wind_warning": "中風險 - 密切關注",
    "general_warning": "中風險 - 持續監控",
    "airport_disabled": "基於天氣預報評估 (機場即時監控已禁用)"
}

# Checkup risk messages  
CHECKUP_RISK_MESSAGES = {
    "typhoon_direct": "高風險 - 可能停班停課",
    "typhoon_indirect": "中風險 - 可能影響交通",
    "geographic_high": "高風險 - 颱風地理威脅",
    "geographic_medium": "中風險 - 颱風間接威脅"
}