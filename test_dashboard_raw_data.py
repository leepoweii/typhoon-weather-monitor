#!/usr/bin/env python3
"""
測試儀表板原始資料顯示功能
"""

import json
import requests
import time

def test_dashboard_raw_data():
    """測試儀表板原始資料功能"""
    
    base_url = "http://localhost:8001"
    
    print("🧪 測試儀表板原始資料顯示功能")
    print("=" * 60)
    
    try:
        # 測試狀態 API
        print("\n📝 1. 測試狀態 API...")
        status_response = requests.get(f"{base_url}/api/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"✅ 狀態: {status_data['status']}")
            print(f"📊 警告數量: {len(status_data['warnings'])}")
            print(f"✈️ 航班風險: {status_data['travel_risk']}")
            print(f"🏥 體檢風險: {status_data['checkup_risk']}")
            
            if status_data['warnings']:
                print("⚠️ 當前警告:")
                for warning in status_data['warnings']:
                    print(f"  • {warning}")
        else:
            print(f"❌ 狀態 API 錯誤: {status_response.status_code}")
            return
        
        # 測試原始資料 API
        print("\n📊 2. 測試原始資料 API...")
        raw_data_response = requests.get(f"{base_url}/api/raw-data")
        if raw_data_response.status_code == 200:
            raw_data = raw_data_response.json()
            
            # 分析颱風資料
            typhoons = raw_data.get('typhoons', {})
            if typhoons.get('records', {}).get('tropicalCyclones'):
                cyclones = typhoons['records']['tropicalCyclones']['tropicalCyclone']
                print(f"🌀 颱風資料: 找到 {len(cyclones)} 個熱帶氣旋")
                
                for i, cyclone in enumerate(cyclones):
                    name = cyclone.get('cwaTyphoonName') or cyclone.get('typhoonName') or f"TD-{cyclone.get('cwaTdNo', 'Unknown')}"
                    print(f"  {i+1}. {name}")
                    
                    # 最新分析資料
                    analysis = cyclone.get('analysisData', {})
                    fixes = analysis.get('fix', [])
                    if fixes:
                        latest = fixes[-1]
                        wind = latest.get('maxWindSpeed')
                        pressure = latest.get('pressure')
                        if wind:
                            wind_kmh = int(wind) * 3.6
                            print(f"     💨 風速: {wind} m/s ({wind_kmh:.1f} km/h)")
                        if pressure:
                            print(f"     📊 氣壓: {pressure} hPa")
            
            # 分析天氣資料
            weather = raw_data.get('weather', {})
            if weather.get('records', {}).get('location'):
                locations = weather['records']['location']
                print(f"\n🌤️ 天氣預報: 找到 {len(locations)} 個地區")
                
                for location in locations:
                    location_name = location.get('locationName')
                    print(f"  📍 {location_name}")
                    
                    elements = location.get('weatherElement', [])
                    for element in elements:
                        element_name = element.get('elementName')
                        times = element.get('time', [])
                        if times:
                            value = times[0].get('parameter', {}).get('parameterName')
                            if element_name == 'Wx':
                                print(f"     🌤️ 天氣: {value}")
                            elif element_name == 'PoP':
                                print(f"     🌧️ 降雨機率: {value}%")
                            elif element_name == 'MinT':
                                print(f"     🌡️ 最低溫: {value}°C")
                            elif element_name == 'MaxT':
                                print(f"     🌡️ 最高溫: {value}°C")
            
            # 分析特報資料
            alerts = raw_data.get('alerts', {})
            if alerts.get('records', {}).get('location'):
                locations = alerts['records']['location']
                print(f"\n⚠️ 特報資料: 檢查 {len(locations)} 個地區")
                
                for location in locations:
                    location_name = location.get('locationName')
                    hazards = location.get('hazardConditions', {}).get('hazards', [])
                    
                    if hazards:
                        print(f"  📍 {location_name}: {len(hazards)} 個特報")
                        for hazard in hazards:
                            phenomena = hazard.get('info', {}).get('phenomena', '')
                            significance = hazard.get('info', {}).get('significance', '')
                            print(f"     📢 {phenomena} {significance}")
                    else:
                        print(f"  📍 {location_name}: 無特報")
        else:
            print(f"❌ 原始資料 API 錯誤: {raw_data_response.status_code}")
            return
        
        # 測試儀表板頁面
        print("\n🌐 3. 測試儀表板頁面...")
        dashboard_response = requests.get(f"{base_url}/")
        if dashboard_response.status_code == 200:
            html_content = dashboard_response.text
            
            # 檢查關鍵元素
            checks = [
                ("原始氣象資料", "📊 原始氣象資料" in html_content),
                ("颱風詳細資料", "🌀</span> 颱風詳細資料" in html_content),
                ("天氣預報資料", "🌤️</span> 天氣預報資料" in html_content),
                ("特報資料", "⚠️</span> 天氣特報資料" in html_content),
                ("風險評估說明", "📋 風險評估依據" in html_content),
                ("JavaScript 功能", "formatRawData" in html_content),
                ("展開/收合功能", "toggleContent" in html_content),
            ]
            
            print("📋 儀表板內容檢查:")
            for check_name, result in checks:
                status = "✅" if result else "❌"
                print(f"  {status} {check_name}")
                
            print(f"\n📄 HTML 頁面大小: {len(html_content):,} 字元")
        else:
            print(f"❌ 儀表板頁面錯誤: {dashboard_response.status_code}")
            return
        
        print("\n🎉 所有測試完成！")
        print("\n📱 訪問儀表板:")
        print(f"🔗 主頁面: {base_url}/")
        print(f"📊 狀態API: {base_url}/api/status")
        print(f"💾 原始資料API: {base_url}/api/raw-data")
        
        print("\n💡 儀表板功能說明:")
        print("• 📊 原始氣象資料區塊已添加到儀表板")
        print("• 🌀 颱風詳細資料（風速、氣壓、座標等）")
        print("• 🌤️ 天氣預報資料（溫度、降雨機率、舒適度等）")
        print("• ⚠️ 特報資料（強風特報、颱風警報等）")
        print("• 📋 風險評估依據說明")
        print("• 🎛️ 展開/收合功能（點擊標題切換顯示）")
        print("• 🔄 每30秒自動更新")
        print("• 📱 響應式設計，支援手機瀏覽")
        
    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到伺服器，請確認伺服器正在運行在 localhost:8001")
    except Exception as e:
        print(f"❌ 測試過程發生錯誤: {e}")

if __name__ == "__main__":
    test_dashboard_raw_data()
