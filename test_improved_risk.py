#!/usr/bin/env python3
"""
測試改進後的台南風險評估邏輯
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# 設置路徑
sys.path.append('.')

# 模擬颱風資料
mock_typhoon_scenarios = {
    "scenario_1_nearby_strong": {
        "description": "強颱風接近台南（距離100km）",
        "data": {
            "records": {
                "tropicalCyclones": {
                    "tropicalCyclone": [
                        {
                            "typhoonName": "GAEMI", 
                            "cwaTyphoonName": "凱米",
                            "analysisData": {
                                "fix": [
                                    {
                                        "fixTime": "2025-07-06T14:00:00+08:00",
                                        "coordinate": "120.8,23.6",  # 距離台南約100km
                                        "maxWindSpeed": "45",  # 162 km/h
                                        "maxGustSpeed": "60",
                                        "pressure": "945",
                                        "movingSpeed": "15",
                                        "movingDirection": "NW",
                                        "circleOf15Ms": {"radius": "150"}  # 暴風圈半徑150km
                                    }
                                ]
                            },
                            "forecastData": {
                                "fix": [
                                    {
                                        "initTime": "2025-07-06T14:00:00+08:00",
                                        "tau": "12",
                                        "coordinate": "120.2,23.0",  # 預計直接經過台南
                                        "maxWindSpeed": "50",
                                        "circleOf15Ms": {"radius": "180"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    },
    "scenario_2_distant_weak": {
        "description": "遠距弱颱風（距離400km）",
        "data": {
            "records": {
                "tropicalCyclones": {
                    "tropicalCyclone": [
                        {
                            "typhoonName": "WEAK",
                            "cwaTyphoonName": "微弱",
                            "analysisData": {
                                "fix": [
                                    {
                                        "fixTime": "2025-07-06T14:00:00+08:00",
                                        "coordinate": "124.0,25.0",  # 距離台南約400km
                                        "maxWindSpeed": "18",  # 65 km/h
                                        "maxGustSpeed": "25",
                                        "pressure": "990",
                                        "movingSpeed": "20",
                                        "movingDirection": "E",
                                        "circleOf15Ms": {"radius": "80"}
                                    }
                                ]
                            },
                            "forecastData": {
                                "fix": [
                                    {
                                        "initTime": "2025-07-06T14:00:00+08:00",
                                        "tau": "24",
                                        "coordinate": "126.0,26.0",  # 遠離台南
                                        "maxWindSpeed": "15"
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    },
    "scenario_3_timing_threat": {
        "description": "時間威脅（體檢日當天通過）",
        "data": {
            "records": {
                "tropicalCyclones": {
                    "tropicalCyclone": [
                        {
                            "typhoonName": "TIMING",
                            "cwaTyphoonName": "時機",
                            "analysisData": {
                                "fix": [
                                    {
                                        "fixTime": "2025-07-05T14:00:00+08:00",
                                        "coordinate": "118.0,22.0",  # 南方200km
                                        "maxWindSpeed": "30",  # 108 km/h
                                        "maxGustSpeed": "40",
                                        "pressure": "970",
                                        "movingSpeed": "25",
                                        "movingDirection": "N",
                                        "circleOf15Ms": {"radius": "120"}
                                    }
                                ]
                            },
                            "forecastData": {
                                "fix": [
                                    {
                                        "initTime": "2025-07-05T14:00:00+08:00",
                                        "tau": "40",  # 40小時後 = 7/7 早上
                                        "coordinate": "120.0,23.5",  # 接近台南
                                        "maxWindSpeed": "35",
                                        "circleOf15Ms": {"radius": "140"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }
}

async def test_improved_risk_assessment():
    """測試改進後的風險評估"""
    
    print("🧪 測試改進後的台南風險評估邏輯")
    print("=" * 70)
    
    # 導入必要模組
    from app import TyphoonMonitor
    import app
    
    monitor = TyphoonMonitor()
    
    print("\n📋 測試說明:")
    print("• 台南座標: 23.0°N, 120.2°E")
    print("• 體檢日期: 2025-07-07")
    print("• 評估範圍: 地理距離 + 風速強度 + 時間預測")
    
    for scenario_name, scenario in mock_typhoon_scenarios.items():
        print(f"\n{'='*50}")
        print(f"🎬 測試情境: {scenario['description']}")
        print("="*50)
        
        # 設置模擬資料
        app.latest_typhoons = scenario['data']
        
        # 模擬警告（無台南直接特報）
        mock_warnings = []
        
        # 執行風險評估
        risk_result = monitor.assess_checkup_risk(mock_warnings)
        
        print(f"\n📊 評估結果:")
        print(f"風險等級: {risk_result}")
        
        # 詳細分析資料
        typhoon_data = scenario['data']['records']['tropicalCyclones']['tropicalCyclone'][0]
        analysis = typhoon_data['analysisData']['fix'][0]
        forecast = typhoon_data.get('forecastData', {}).get('fix', [])
        
        # 計算距離
        coordinate = analysis['coordinate']
        lon, lat = map(float, coordinate.split(','))
        distance = monitor._calculate_distance(lat, lon, 23.0, 120.2)
        
        print(f"\n🔍 詳細分析:")
        print(f"  颱風名稱: {typhoon_data.get('cwaTyphoonName', '未知')}")
        print(f"  當前位置: {lat}°N, {lon}°E")
        print(f"  距離台南: {distance:.1f} km")
        print(f"  最大風速: {analysis['maxWindSpeed']} m/s ({int(analysis['maxWindSpeed']) * 3.6:.0f} km/h)")
        
        storm_radius = analysis.get('circleOf15Ms', {}).get('radius', 0)
        if storm_radius:
            print(f"  暴風圈半徑: {storm_radius} km")
            if distance < float(storm_radius):
                print(f"  ⚠️ 台南在暴風圈內！")
            else:
                print(f"  ✅ 台南在暴風圈外")
        
        print(f"  移動方向: {analysis.get('movingDirection', '未知')}")
        print(f"  移動速度: {analysis.get('movingSpeed', '未知')} km/h")
        
        # 預報分析
        if forecast:
            print(f"\n📈 預報分析:")
            for f in forecast:
                tau = f.get('tau', '')
                if tau:
                    hours = int(tau)
                    forecast_time = datetime.now() + timedelta(hours=hours)
                    f_coord = f.get('coordinate', '')
                    if f_coord:
                        f_lon, f_lat = map(float, f_coord.split(','))
                        f_distance = monitor._calculate_distance(f_lat, f_lon, 23.0, 120.2)
                        print(f"  {hours}小時後 ({forecast_time.strftime('%m/%d %H時')}): 距離台南 {f_distance:.1f} km")
    
    print(f"\n{'='*50}")
    print("🆚 新舊邏輯對比測試")
    print("="*50)
    
    # 測試原有邏輯 vs 新邏輯
    test_cases = [
        {
            "name": "無任何警告",
            "warnings": [],
            "expected_old": "低風險"
        },
        {
            "name": "台南強風特報",
            "warnings": ["⚠️ 臺南市: 陸上強風 特報"],
            "expected_old": "中風險 - 可能影響交通"
        },
        {
            "name": "颱風但無地區指定",
            "warnings": ["🌀 凱米颱風 最大風速: 45 m/s (162.0 km/h) - 高風險"],
            "expected_old": "低風險"
        }
    ]
    
    # 設定接近台南的強颱風資料用於對比
    app.latest_typhoons = mock_typhoon_scenarios["scenario_1_nearby_strong"]["data"]
    
    for case in test_cases:
        print(f"\n🔄 測試案例: {case['name']}")
        
        # 新邏輯結果
        new_result = monitor.assess_checkup_risk(case['warnings'])
        
        # 舊邏輯結果（簡化模擬）
        old_result = case['expected_old']
        if case['warnings']:
            for warning in case['warnings']:
                if '台南' in warning or '臺南' in warning:
                    if '颱風' in warning:
                        old_result = "高風險 - 可能停班停課"
                        break
                    elif '強風' in warning or '豪雨' in warning:
                        old_result = "中風險 - 可能影響交通"
                        break
        
        print(f"  舊邏輯: {old_result}")
        print(f"  新邏輯: {new_result.split('詳細分析:')[0].strip()}")
        
        if "詳細分析:" in new_result:
            details = new_result.split('詳細分析:')[1].strip()
            print(f"  地理分析: {details}")
        
        print(f"  差異: {'顯著提升' if len(new_result) > len(old_result) else '相同'}")
    
    print(f"\n🎯 改進總結:")
    print("✅ 新增地理距離計算")
    print("✅ 新增暴風圈影響評估") 
    print("✅ 新增時間預測分析")
    print("✅ 新增風速強度評估")
    print("✅ 保留原有特報邏輯")
    print("✅ 提供詳細分析資訊")
    
    await monitor.client.aclose()

if __name__ == "__main__":
    asyncio.run(test_improved_risk_assessment())
