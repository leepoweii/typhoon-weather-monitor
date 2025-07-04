#!/usr/bin/env python3
"""
測試颱風原始資料顯示功能
"""

import requests
import json

def test_typhoon_raw_data():
    """測試颱風原始資料顯示"""
    print("🧪 測試颱風原始資料顯示功能")
    print("=" * 50)
    
    try:
        # 測試 API 狀態
        print("📡 測試 API 狀態...")
        response = requests.get("http://localhost:8000/api/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 狀態正常")
            print(f"⏰ 時間戳: {data['timestamp']}")
            print(f"🚨 警告狀態: {data['status']}")
            print(f"✈️ 航班風險: {data['travel_risk']}")
            print(f"🏥 體檢風險: {data['checkup_risk']}")
            if data['warnings']:
                print("⚠️ 警告訊息:")
                for warning in data['warnings']:
                    print(f"  • {warning}")
            else:
                print("✅ 無警告訊息")
        else:
            print(f"❌ API 狀態錯誤: {response.status_code}")
        
        print("\n" + "=" * 50)
        
        # 測試原始資料
        print("📊 測試原始氣象資料...")
        response = requests.get("http://localhost:8000/api/raw-data")
        if response.status_code == 200:
            raw_data = response.json()
            
            # 檢查天氣資料
            if 'weather' in raw_data and raw_data['weather']:
                weather = raw_data['weather']
                if 'records' in weather and 'location' in weather['records']:
                    locations = weather['records']['location']
                    print(f"✅ 天氣資料: 找到 {len(locations)} 個地區")
                    
                    for location in locations[:2]:  # 只顯示前兩個地區
                        name = location.get('locationName', '未知')
                        print(f"\n🏃 {name} 天氣資料:")
                        
                        elements = location.get('weatherElement', [])
                        for element in elements:
                            element_name = element.get('elementName', '')
                            times = element.get('time', [])
                            
                            if times:
                                latest = times[0]
                                param = latest.get('parameter', {})
                                value = param.get('parameterName', '')
                                unit = param.get('parameterUnit', '')
                                start_time = latest.get('startTime', '')
                                
                                if element_name == 'Wx':
                                    print(f"  🌤️ 天氣現象: {value}")
                                elif element_name == 'PoP':
                                    print(f"  🌧️ 降雨機率: {value}%")
                                elif element_name == 'MinT':
                                    print(f"  🌡️ 最低溫: {value}°C")
                                elif element_name == 'MaxT':
                                    print(f"  🌡️ 最高溫: {value}°C")
                                elif element_name == 'CI':
                                    print(f"  😌 舒適度: {value}")
                                
                                if element_name in ['Wx', 'PoP']:
                                    print(f"    ⏰ 時間: {start_time}")
                else:
                    print("❌ 天氣資料格式異常")
            else:
                print("⚠️ 無天氣資料")
            
            # 檢查颱風資料
            if 'typhoons' in raw_data and raw_data['typhoons']:
                typhoons = raw_data['typhoons']
                print(f"\n🌀 颱風資料: {json.dumps(typhoons, indent=2, ensure_ascii=False)}")
            else:
                print("\n🌀 目前無颱風資料")
            
            # 檢查特報資料
            if 'alerts' in raw_data and raw_data['alerts']:
                alerts = raw_data['alerts']
                if 'records' in alerts and 'location' in alerts['records']:
                    locations = alerts['records']['location']
                    print(f"\n⚠️ 特報資料: 找到 {len(locations)} 個地區")
                    
                    for location in locations:
                        name = location.get('locationName', '未知')
                        hazards = location.get('hazardConditions', {}).get('hazards', [])
                        if hazards:
                            print(f"  📢 {name} 特報:")
                            for hazard in hazards:
                                phenomena = hazard.get('phenomena', '')
                                significance = hazard.get('significance', '')
                                print(f"    • {phenomena} {significance}")
                else:
                    print("\n✅ 無特報資料")
            else:
                print("\n✅ 無特報資料")
        else:
            print(f"❌ 原始資料錯誤: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 測試建議:")
    print("• 透過 LINE Bot 發送 '颱風近況' 來查看包含原始資料的 Flex Message")
    print("• 查看 http://localhost:8000/ 儀表板確認資料顯示")
    print("• 檢查風險評估是否基於實際氣象數據")

if __name__ == "__main__":
    test_typhoon_raw_data()
