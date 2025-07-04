#!/usr/bin/env python3
"""
測試延誤案例的分析邏輯
"""

import json
from datetime import datetime


def test_delay_analysis():
    """測試延誤分析邏輯"""
    print("🧪 測試延誤分析邏輯")
    print("="*50)
    
    # 讀取真實資料
    with open('airport_data_example.json', 'r', encoding='utf-8') as f:
        departure_data = json.load(f)
    
    # 機場代碼對應
    airport_names = {
        'TSA': '松山',
        'TPE': '桃園', 
        'KHH': '高雄',
        'TNN': '台南',
        'CYI': '嘉義',
        'RMQ': '馬公',
        'KNH': '金門'
    }
    
    warnings = []
    
    for flight in departure_data:
        try:
            airline_id = flight.get('AirlineID', '')
            flight_number = flight.get('FlightNumber', '')
            destination_code = flight.get('ArrivalAirportID', '')
            destination = airport_names.get(destination_code, destination_code)
            schedule_time = flight.get('ScheduleDepartureTime', '')
            actual_time = flight.get('ActualDepartureTime', '')
            remark = flight.get('DepartureRemark', '')
            
            # 檢查延誤狀況
            if actual_time and schedule_time:
                try:
                    schedule_dt = datetime.fromisoformat(schedule_time)
                    actual_dt = datetime.fromisoformat(actual_time)
                    delay_minutes = (actual_dt - schedule_dt).total_seconds() / 60
                    
                    # 延誤超過30分鐘才警告
                    if delay_minutes >= 30:
                        warning = f"⏰ 起飛延誤: {airline_id}{flight_number} → {destination} 延誤 {int(delay_minutes)} 分鐘"
                        warnings.append(warning)
                        print(f"  ⚠️ {warning}")
                except:
                    pass
        except Exception as e:
            print(f"  ❌ 分析失敗: {e}")
    
    print(f"\n📊 分析結果:")
    print(f"  發現 {len(warnings)} 個延誤警告")
    
    # 模擬 LINE 通知格式
    if warnings:
        print(f"\n📱 模擬 LINE 通知內容:")
        print("🚨 颱風警報 - 2025-07-04 19:58")
        print("---------------------------")
        print("🔴 警告狀態: 有風險")
        print()
        print("✈️ 7/6 金門→台南航班風險: 高風險 - 航班已延誤")
        print("🏥 7/7 台南體檢風險: 低風險")
        print()
        print("🛫 金門機場即時狀況:")
        for warning in warnings:
            print(f"• {warning}")
    
    return warnings


if __name__ == "__main__":
    test_delay_analysis()
