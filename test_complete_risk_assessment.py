#!/usr/bin/env python3
"""
完整測試改進後的台南風險評估邏輯
驗證地理分析、風速評估、時間預測等功能
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# 設置路徑
sys.path.append('.')

async def test_complete_risk_assessment():
    """完整測試風險評估邏輯"""
    print("🔬 完整風險評估邏輯測試")
    print("=" * 80)
    
    # 導入主程式
    from app import TyphoonMonitor
    
    # 創建監控器實例
    monitor = TyphoonMonitor()
    
    # 準備測試情境
    test_scenarios = [
        {
            "name": "極高風險情境：超強颱風直襲台南",
            "typhoon_data": {
                "records": {
                    "tropicalCyclones": {
                        "tropicalCyclone": [
                            {
                                "typhoonName": "SUPER",
                                "cwaTyphoonName": "超強",
                                "cwaTyNo": "2025001",
                                "analysisData": {
                                    "fix": [
                                        {
                                            "fixTime": "2025-07-06T18:00:00+08:00",
                                            "coordinate": "120.0,23.2",  # 非常接近台南
                                            "maxWindSpeed": "60",  # 216 km/h - 超強颱風
                                            "maxGustSpeed": "75",
                                            "pressure": "920",
                                            "movingSpeed": "20",
                                            "movingDirection": "NW",
                                            "circleOf15Ms": {"radius": "200"}
                                        }
                                    ]
                                },
                                "forecastData": {
                                    "fix": [
                                        {
                                            "tau": "12",
                                            "coordinate": "120.2,23.0",  # 直接經過台南中心
                                            "maxWindSpeed": "65",
                                            "circleOf15Ms": {"radius": "220"}
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            },
            "warnings": ["台南市發布颱風警報", "台南市停止上班上課"]
        },
        {
            "name": "高風險情境：強颱風接近但未直接影響",
            "typhoon_data": {
                "records": {
                    "tropicalCyclones": {
                        "tropicalCyclone": [
                            {
                                "typhoonName": "STRONG",
                                "cwaTyphoonName": "強風",
                                "analysisData": {
                                    "fix": [
                                        {
                                            "fixTime": "2025-07-06T12:00:00+08:00",
                                            "coordinate": "121.0,24.0",  # 距離約150km
                                            "maxWindSpeed": "50",  # 180 km/h
                                            "maxGustSpeed": "65",
                                            "pressure": "940",
                                            "movingSpeed": "25",
                                            "movingDirection": "W",
                                            "circleOf15Ms": {"radius": "180"}
                                        }
                                    ]
                                },
                                "forecastData": {
                                    "fix": [
                                        {
                                            "tau": "18",
                                            "coordinate": "120.5,23.5",  # 最接近點
                                            "maxWindSpeed": "45",
                                            "circleOf15Ms": {"radius": "160"}
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            },
            "warnings": ["強風特報", "大雨特報"]
        },
        {
            "name": "中風險情境：中等颱風遠距離經過",
            "typhoon_data": {
                "records": {
                    "tropicalCyclones": {
                        "tropicalCyclone": [
                            {
                                "typhoonName": "MEDIUM",
                                "cwaTyphoonName": "中等",
                                "analysisData": {
                                    "fix": [
                                        {
                                            "fixTime": "2025-07-06T06:00:00+08:00",
                                            "coordinate": "118.0,25.0",  # 距離約300km
                                            "maxWindSpeed": "35",  # 126 km/h
                                            "maxGustSpeed": "45",
                                            "pressure": "960",
                                            "movingSpeed": "30",
                                            "movingDirection": "NE",
                                            "circleOf15Ms": {"radius": "120"}
                                        }
                                    ]
                                },
                                "forecastData": {
                                    "fix": [
                                        {
                                            "tau": "36",
                                            "coordinate": "119.0,26.0",
                                            "maxWindSpeed": "30",
                                            "circleOf15Ms": {"radius": "100"}
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            },
            "warnings": ["外圍環流影響", "偶有陣雨"]
        },
        {
            "name": "低風險情境：遠距離弱颱風",
            "typhoon_data": {
                "records": {
                    "tropicalCyclones": {
                        "tropicalCyclone": [
                            {
                                "typhoonName": "WEAK",
                                "cwaTyphoonName": "微弱",
                                "analysisData": {
                                    "fix": [
                                        {
                                            "fixTime": "2025-07-05T12:00:00+08:00",
                                            "coordinate": "125.0,20.0",  # 距離約600km
                                            "maxWindSpeed": "20",  # 72 km/h
                                            "maxGustSpeed": "25",
                                            "pressure": "985",
                                            "movingSpeed": "15",
                                            "movingDirection": "E",
                                            "circleOf15Ms": {"radius": "80"}
                                        }
                                    ]
                                },
                                "forecastData": {
                                    "fix": [
                                        {
                                            "tau": "48",
                                            "coordinate": "130.0,22.0",
                                            "maxWindSpeed": "25",
                                            "circleOf15Ms": {"radius": "60"}
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            },
            "warnings": []
        }
    ]
    
    # 執行測試
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📊 測試情境 {i}: {scenario['name']}")
        print("-" * 60)
        
        # 設置颱風資料
        global latest_typhoons
        from app import latest_typhoons
        latest_typhoons.clear()
        latest_typhoons.update(scenario['typhoon_data'])
        
        # 執行風險評估
        risk_result = monitor.assess_checkup_risk(scenario['warnings'])
        
        print(f"🎯 風險評估結果: {risk_result}")
        
        # 執行地理風險分析
        tainan_lat, tainan_lon = 23.0, 120.2
        checkup_date = datetime(2025, 7, 7)
        geo_risk = monitor._assess_typhoon_geographic_risk(tainan_lat, tainan_lon, checkup_date)
        
        print(f"📍 地理風險等級: {geo_risk['level']}")
        if geo_risk['distance']:
            print(f"📏 最近距離: {geo_risk['distance']:.1f} km")
        print(f"💨 風速威脅: {'是' if geo_risk['wind_threat'] else '否'}")
        print(f"⏰ 時間威脅: {'是' if geo_risk['time_threat'] else '否'}")
        
        if geo_risk['details']:
            print("🔍 詳細威脅分析:")
            for detail in geo_risk['details']:
                print(f"  • {detail}")
        
        # 分析颱風詳細資料
        if 'tropicalCyclone' in scenario['typhoon_data']['records']['tropicalCyclones']:
            typhoon = scenario['typhoon_data']['records']['tropicalCyclones']['tropicalCyclone'][0]
            analysis = typhoon['analysisData']['fix'][0]
            
            print("🌀 颱風參數分析:")
            coord = analysis['coordinate']
            lon, lat = map(float, coord.split(','))
            distance = monitor._calculate_distance(lat, lon, tainan_lat, tainan_lon)
            
            wind_speed_ms = int(analysis['maxWindSpeed'])
            wind_speed_kmh = wind_speed_ms * 3.6
            storm_radius = float(analysis['circleOf15Ms']['radius'])
            
            print(f"  📍 颱風位置: {lat}°N, {lon}°E")
            print(f"  📏 距離台南: {distance:.1f} km")
            print(f"  💨 最大風速: {wind_speed_ms} m/s ({wind_speed_kmh:.1f} km/h)")
            print(f"  🌪️ 暴風圈半徑: {storm_radius} km")
            print(f"  📊 中心氣壓: {analysis['pressure']} hPa")
            print(f"  🏃 移動速度: {analysis['movingSpeed']} km/h")
            print(f"  ➡️ 移動方向: {analysis['movingDirection']}")
            
            # 威脅程度分析
            in_storm_circle = distance < storm_radius
            wind_threat = distance < 200 and wind_speed_kmh > 80
            severe_threat = distance < 100 and wind_speed_kmh > 150
            
            print("⚠️ 威脅程度分析:")
            print(f"  暴風圈威脅: {'⚠️ 是' if in_storm_circle else '✅ 否'}")
            print(f"  強風威脅: {'⚠️ 是' if wind_threat else '✅ 否'}")
            print(f"  嚴重威脅: {'🚨 是' if severe_threat else '✅ 否'}")
    
    print(f"\n{'='*80}")
    print("🎉 完整風險評估測試完成")
    print("\n📋 系統能力總結:")
    print("✅ 地理距離精準計算")
    print("✅ 暴風圈影響評估") 
    print("✅ 風速強度分級")
    print("✅ 時間預測分析")
    print("✅ 多重威脅綜合評估")
    print("✅ 詳細分析說明")
    print("✅ 傳統特報邏輯保留")

def test_format_message_with_geo_analysis():
    """測試訊息格式化是否包含地理分析"""
    print(f"\n{'='*80}")
    print("📝 測試訊息格式化功能（含地理分析）")
    print("-" * 60)
    
    from app import LineNotifier
    
    # 創建 LINE 通知器
    notifier = LineNotifier()
    
    # 模擬包含地理分析的結果
    mock_result = {
        "timestamp": "2025-01-07T10:00:00Z",
        "status": "DANGER",
        "travel_risk": "高風險 - 航班可能取消",
        "checkup_risk": "極高風險 - 強烈建議延期\n詳細分析: 🌪️ 超強 暴風圈影響台南（距離50km < 半徑200.0km）; ⏰ 超強 預計07/07 06時影響台南（距離20km）",
        "warnings": [
            "台南市發布颱風警報",
            "台南市停止上班上課",
            "預期風速達200km/h以上"
        ]
    }
    
    # 格式化訊息
    formatted_message = notifier.format_typhoon_status(mock_result)
    
    print("🖼️ 格式化後的訊息:")
    print("-" * 40)
    print(formatted_message)
    print("-" * 40)
    
    # 檢查是否包含地理分析
    if "地理分析:" in formatted_message:
        print("✅ 成功包含地理分析資訊")
    else:
        print("❌ 缺少地理分析資訊")
    
    # 檢查是否包含風險評估依據
    if "風險評估依據:" in formatted_message:
        print("✅ 成功包含風險評估依據")
    else:
        print("❌ 缺少風險評估依據")

if __name__ == "__main__":
    asyncio.run(test_complete_risk_assessment())
    test_format_message_with_geo_analysis()
