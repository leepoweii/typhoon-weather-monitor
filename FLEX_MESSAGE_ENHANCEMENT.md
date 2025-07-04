# FlexMessage Enhancement: Tainan Weather Forecast

## Overview
Enhanced the LINE Bot FlexMessage to include a dedicated Tainan weather forecast section for dates 7/6-7/10, focusing specifically on wind and rain conditions while excluding temperature information.

## Implementation Details

### New Features Added

1. **📅 Tainan Weather Forecast Section**
   - Displays weather for specific dates: 7/6-7/10 (July 6-10, 2025)
   - Shows date format as MM/DD(週X) - e.g., "7/6(週一)"
   - Focuses only on weather phenomena and rain probability

2. **🌧️ Wind and Rain Focus**
   - **Included**: Weather phenomena (Wx) - storms, wind, rain conditions
   - **Included**: Rain probability (PoP) - percentage chance of precipitation
   - **Excluded**: Temperature data (MinT, MaxT) as requested
   - **Excluded**: Comfort index and other non-critical metrics

3. **🎨 Color-Coded Risk Levels**
   - **Red (#FF4757)**: High risk - 颱風, 暴風, 豪雨
   - **Orange (#FFA726)**: Medium risk - 大雨, 雷雨, 強風
   - **Green (#2ED573)**: Low risk - 雨, 陣雨
   - **Black (#333333)**: Normal conditions

### Code Changes

#### File: `notifications/flex_message_builder.py`

**Added Method**: `_get_tainan_weather_forecast()`
```python
def _get_tainan_weather_forecast(self) -> List[Dict]:
    """取得台南市7/6-7/10天氣預報，專注於風雨資訊"""
    # Target dates: 2025-07-06 to 2025-07-10
    target_dates = ["2025-07-06", "2025-07-07", "2025-07-08", "2025-07-09", "2025-07-10"]
    
    # Process only Wx (weather) and PoP (rain probability)
    # Exclude MinT, MaxT (temperature) and CI (comfort index)
```

**Modified Method**: `create_typhoon_status_flex()`
```python
# Added Tainan weather forecast to the main FlexMessage
] + warning_contents + self._get_tainan_weather_forecast() + self._get_typhoon_details_flex_content()
```

### FlexMessage Structure

The enhanced FlexMessage now includes:

```
🌀 颱風警訊播報
├── Status Overview (DANGER/SAFE)
├── Travel Risk Assessment
├── Checkup Risk Assessment
├── Warning Messages
├── 🌧️ 台南市天氣預報 (7/6-7/10)  ← **NEW SECTION**
│   ├── 7/6(一): 🌤️ [Weather] 🌧️ [Rain %]
│   ├── 7/7(二): 🌤️ [Weather] 🌧️ [Rain %]
│   ├── 7/8(三): 🌤️ [Weather] 🌧️ [Rain %]
│   ├── 7/9(四): 🌤️ [Weather] 🌧️ [Rain %]
│   └── 7/10(五): 🌤️ [Weather] 🌧️ [Rain %]
├── Typhoon Details
└── Dashboard Link Button
```

### Data Processing Logic

1. **Date Filtering**: Only processes weather data for the 5 target dates
2. **Element Filtering**: Only extracts Wx and PoP elements from weather API
3. **Location Filtering**: Specifically searches for "台南" or "臺南" in location names
4. **Risk Assessment**: Automatically color-codes based on weather keywords
5. **Fallback Handling**: Gracefully handles missing data with "無資料" indicators

### Benefits

- ✅ **Focused Information**: Users see only relevant wind/rain data for their travel period
- ✅ **Visual Clarity**: Color coding helps quickly identify risky weather days
- ✅ **Reduced Clutter**: Temperature data excluded to focus on critical weather conditions
- ✅ **Consistent Format**: Standardized date display and weather information layout
- ✅ **Error Resilience**: Handles API failures and missing data gracefully

### Testing Results

All tests passed successfully:
- ✓ FlexMessage structure validated
- ✓ Tainan weather forecast section found
- ✓ Specific dates (7/6-7/10) included
- ✓ Temperature information properly excluded
- ✓ Wind and rain data properly included
- ✓ Color-coded risk levels working
- ✓ Ready for LINE Bot notifications

## Usage

The enhanced FlexMessage is automatically used whenever:
1. LINE Bot sends typhoon status notifications
2. Users request weather updates via trigger keywords
3. System detects status changes and pushes notifications

Users will now see comprehensive weather forecasts for their specific travel dates, helping them make informed decisions about their 7/6 flight and 7/7 medical checkup in Tainan.