#!/usr/bin/env python3
"""
測試原始氣象資料顯示功能
"""

import json
from datetime import datetime
import sys
import os

# 模擬颱風資料
mock_typhoon_data = {
    "records": {
        "tropicalCyclones": {
            "tropicalCyclone": [
                {
                    "typhoonName": "GAEMI",
                    "cwaTyphoonName": "凱米",
                    "cwaTyNo": "202404",
                    "analysisData": {
                        "fix": [
                            {
                                "fixTime": "2025-07-04T12:00:00",
                                "maxWindSpeed": "45",  # m/s
                                "maxGustSpeed": "60",  # m/s
                                "pressure": "945",    # hPa
                                "movingSpeed": "15",  # km/h
                                "movingDirection": "NNE",
                                "coordinate": "121.5,24.8",
                                "circleOf15Ms": {
                                    "radius": "150"  # km
                                }
                            }
                        ]
                    },
                    "forecastData": {
                        "fix": [
                            {
                                "tau": "6",
                                "coordinate": "121.2,24.5"
                            }
                        ]
                    }
                }
            ]
        }
    }
}

# 模擬天氣預報資料
mock_weather_data = {
    "records": {
        "location": [
            {
                "locationName": "金門縣",
                "weatherElement": [
                    {
                        "elementName": "Wx",
                        "time": [
                            {
                                "startTime": "2025-07-04T12:00:00",
                                "parameter": {
                                    "parameterName": "大雨特報"
                                }
                            }
                        ]
                    },
                    {
                        "elementName": "PoP",
                        "time": [
                            {
                                "startTime": "2025-07-04T12:00:00",
                                "parameter": {
                                    "parameterName": "85"
                                }
                            }
                        ]
                    },
                    {
                        "elementName": "MinT",
                        "time": [
                            {
                                "startTime": "2025-07-04T12:00:00",
                                "parameter": {
                                    "parameterName": "26"
                                }
                            }
                        ]
                    },
                    {
                        "elementName": "MaxT",
                        "time": [
                            {
                                "startTime": "2025-07-04T12:00:00",
                                "parameter": {
                                    "parameterName": "32"
                                }
                            }
                        ]
                    },
                    {
                        "elementName": "CI",
                        "time": [
                            {
                                "startTime": "2025-07-04T12:00:00",
                                "parameter": {
                                    "parameterName": "悶熱"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
}

# 模擬天氣特報資料
mock_alerts_data = {
    "records": {
        "location": [
            {
                "locationName": "金門縣",
                "hazardConditions": {
                    "hazards": [
                        {
                            "phenomena": "颱風",
                            "significance": "陸上颱風警報",
                            "effectiveTime": "2025-07-04T10:00:00"
                        },
                        {
                            "phenomena": "強風",
                            "significance": "特報",
                            "effectiveTime": "2025-07-04T11:00:00"
                        }
                    ]
                }
            }
        ]
    }
}

def test_original_data_display():
    """測試原始資料顯示功能"""
    
    # 設置環境變數
    os.environ['MONITOR_LOCATIONS'] = '金門縣,臺南市'
    
    # 設置全域變數
    sys.path.append('.')
    from app import latest_typhoons, latest_weather, latest_alerts, LineNotifier
    
    # 直接設置全域變數來模擬資料
    import app
    app.latest_typhoons = mock_typhoon_data
    app.latest_weather = mock_weather_data
    app.latest_alerts = mock_alerts_data
    
    # 創建通知器並測試格式化
    notifier = LineNotifier()
    
    # 模擬監控結果
    mock_result = {
        "timestamp": datetime.now().isoformat(),
        "warnings": [
            "🌀 凱米颱風 最大風速: 45 m/s (162.0 km/h) - 高風險",
            "⚠️ 金門縣: 颱風 陸上颱風警報",
            "🌧️ 金門縣 2025-07-04T12:00:00: 大雨特報"
        ],
        "status": "DANGER",
        "travel_risk": "高風險 - 建議考慮改期",
        "checkup_risk": "中風險 - 密切關注"
    }
    
    print("=" * 60)
    print("🧪 測試原始氣象資料顯示功能")
    print("=" * 60)
    
    # 測試颱風詳細資料
    print("\n📊 颱風詳細資料測試:")
    typhoon_details = notifier._get_typhoon_details()
    print(typhoon_details)
    
    print("\n" + "=" * 40)
    
    # 測試天氣原始資料
    print("\n🌤️ 天氣原始資料測試:")
    weather_raw_data = notifier._get_weather_raw_data()
    print(weather_raw_data)
    
    print("\n" + "=" * 40)
    
    # 測試完整格式化訊息
    print("\n📱 完整 LINE 訊息格式化:")
    formatted_message = notifier.format_typhoon_status(mock_result)
    print(formatted_message)
    
    print("\n" + "=" * 60)
    print("✅ 測試完成")
    
    # 分析資料內容
    print("\n🔍 原始資料分析:")
    print("颱風資料包含:")
    print("- 颱風名稱: 凱米 (GAEMI)")
    print("- 最大風速: 45 m/s (162 km/h) - 屬於高風險範圍")
    print("- 最大陣風: 60 m/s (216 km/h)")
    print("- 中心氣壓: 945 hPa")
    print("- 移動速度: 15 km/h")
    print("- 移動方向: 北北東")
    print("- 暴風圈半徑: 150 km")
    print("- 座標位置: 24.8°N, 121.5°E")
    
    print("\n天氣預報資料包含:")
    print("- 天氣現象: 大雨特報")
    print("- 降雨機率: 85%")
    print("- 溫度範圍: 26-32°C")
    print("- 舒適度: 悶熱")
    
    print("\n特報資料包含:")
    print("- 颱風陸上警報")
    print("- 強風特報")
    
    print("\n💡 風險評估邏輯:")
    print("- 系統基於風速 >80km/h 判定為高風險")
    print("- 凱米颱風風速 162km/h，遠超過高風險標準")
    print("- 大雨特報與強風特報增加額外風險")
    print("- 暴風圈半徑 150km 影響範圍廣泛")

if __name__ == "__main__":
    test_original_data_display()
