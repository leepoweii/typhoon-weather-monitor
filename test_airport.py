#!/usr/bin/env python3
"""
測試金門機場監控功能
"""

import asyncio
import httpx
import json
from datetime import datetime


class TestAirportMonitor:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)
        self.base_url = "https://tdx.transportdata.tw/api/basic/v2/Air/FIDS/Airport"
    
    async def test_departure_api(self):
        """測試起飛資訊 API"""
        try:
            url = f"{self.base_url}/Departure/KNH?$format=JSON"
            print(f"正在測試起飛資訊 API: {url}")
            
            # TDX API 可能需要認證，但先嘗試不帶認證的公開端點
            # 或者使用備用的公開資料
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 起飛資訊 API 測試成功")
            print(f"   回傳資料類型: {type(data)}")
            if isinstance(data, list):
                print(f"   航班數量: {len(data)}")
                if data:
                    print(f"   第一筆資料範例:")
                    first_flight = data[0]
                    print(f"     航空公司: {first_flight.get('AirlineID', 'N/A')}")
                    print(f"     航班號: {first_flight.get('FlightNumber', 'N/A')}")
                    print(f"     目的地: {first_flight.get('Destination', 'N/A')}")
                    print(f"     排定時間: {first_flight.get('ScheduleDepartureTime', 'N/A')}")
                    print(f"     狀態: {first_flight.get('FlightStatusName', 'N/A')}")
            else:
                print(f"   資料內容: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")
            
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print(f"❌ API 需要認證 (401 Unauthorized)")
                print(f"   請確認是否需要 TDX API Key 或其他認證方式")
                print(f"   將返回模擬資料進行功能測試...")
                # 返回模擬資料以測試分析邏輯
                return self.get_mock_departure_data()
            else:
                print(f"❌ 起飛資訊 API 測試失敗: {e}")
                return None
        except Exception as e:
            print(f"❌ 起飛資訊 API 測試失敗: {e}")
            return None
    
    async def test_arrival_api(self):
        """測試抵達資訊 API"""
        try:
            url = f"{self.base_url}/Arrival/KNH?$format=JSON"
            print(f"正在測試抵達資訊 API: {url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ 抵達資訊 API 測試成功")
            print(f"   回傳資料類型: {type(data)}")
            if isinstance(data, list):
                print(f"   航班數量: {len(data)}")
                if data:
                    print(f"   第一筆資料範例:")
                    first_flight = data[0]
                    print(f"     航空公司: {first_flight.get('AirlineID', 'N/A')}")
                    print(f"     航班號: {first_flight.get('FlightNumber', 'N/A')}")
                    print(f"     起點: {first_flight.get('Origin', 'N/A')}")
                    print(f"     排定時間: {first_flight.get('ScheduleArrivalTime', 'N/A')}")
                    print(f"     狀態: {first_flight.get('FlightStatusName', 'N/A')}")
            else:
                print(f"   資料內容: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")
            
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print(f"❌ API 需要認證 (401 Unauthorized)")
                print(f"   請確認是否需要 TDX API Key 或其他認證方式")
                print(f"   將返回模擬資料進行功能測試...")
                # 返回模擬資料以測試分析邏輯
                return self.get_mock_arrival_data()
            else:
                print(f"❌ 抵達資訊 API 測試失敗: {e}")
                return None
        except Exception as e:
            print(f"❌ 抵達資訊 API 測試失敗: {e}")
            return None
    
    async def test_analyze_function(self, departure_data, arrival_data):
        """測試分析功能"""
        print("\n正在測試航班狀態分析功能...")
        
        warnings = []
        
        # 目的地機場代碼對應
        airport_names = {
            'TSA': '松山',
            'TPE': '桃園', 
            'KHH': '高雄',
            'TNN': '台南',
            'CYI': '嘉義',
            'RMQ': '馬公',
            'KNH': '金門'
        }
        
        # 模擬分析邏輯（根據真實資料結構）
        if departure_data and isinstance(departure_data, list):
            for flight in departure_data[:5]:  # 只檢查前5筆
                try:
                    airline_id = flight.get('AirlineID', '')
                    flight_number = flight.get('FlightNumber', '')
                    destination_code = flight.get('ArrivalAirportID', '')
                    destination = airport_names.get(destination_code, destination_code)
                    schedule_time = flight.get('ScheduleDepartureTime', '')
                    actual_time = flight.get('ActualDepartureTime', '')
                    estimated_time = flight.get('EstimatedDepartureTime', '')
                    remark = flight.get('DepartureRemark', '')
                    
                    print(f"   分析起飛航班: {airline_id}{flight_number} → {destination}")
                    print(f"     排定時間: {schedule_time}")
                    print(f"     實際時間: {actual_time}")
                    print(f"     預計時間: {estimated_time}")
                    print(f"     狀態備註: {remark}")
                    
                    # 檢查停飛
                    if remark and any(keyword in remark for keyword in ['取消', '停飛', 'CANCELLED', '暫停']):
                        warning = f"✈️ 起飛停飛: {airline_id}{flight_number} → {destination} - {remark}"
                        warnings.append(warning)
                        print(f"     ⚠️ 警告: {warning}")
                    
                    # 檢查延誤（實際時間 vs 排定時間）
                    elif actual_time and schedule_time:
                        try:
                            from datetime import datetime
                            schedule_dt = datetime.fromisoformat(schedule_time)
                            actual_dt = datetime.fromisoformat(actual_time)
                            delay_minutes = (actual_dt - schedule_dt).total_seconds() / 60
                            
                            if delay_minutes >= 30:
                                warning = f"⏰ 起飛延誤: {airline_id}{flight_number} → {destination} 延誤 {int(delay_minutes)} 分鐘"
                                warnings.append(warning)
                                print(f"     ⚠️ 警告: {warning}")
                            elif delay_minutes > 0:
                                print(f"     📍 輕微延誤: {int(delay_minutes)} 分鐘 (未達警告標準)")
                        except Exception as e:
                            print(f"     ❌ 延誤計算失敗: {e}")
                    
                    # 檢查預計延誤
                    elif estimated_time and schedule_time and not actual_time:
                        try:
                            from datetime import datetime
                            schedule_dt = datetime.fromisoformat(schedule_time)
                            estimated_dt = datetime.fromisoformat(estimated_time)
                            delay_minutes = (estimated_dt - schedule_dt).total_seconds() / 60
                            
                            if delay_minutes >= 30:
                                warning = f"⏰ 起飛預計延誤: {airline_id}{flight_number} → {destination} 預計延誤 {int(delay_minutes)} 分鐘"
                                warnings.append(warning)
                                print(f"     ⚠️ 警告: {warning}")
                        except Exception as e:
                            print(f"     ❌ 預計延誤計算失敗: {e}")
                    
                    # 檢查特殊狀態
                    if remark and any(keyword in remark for keyword in ['延誤', '異常', '等待', '暫緩']):
                        warning = f"📝 起飛狀況: {airline_id}{flight_number} → {destination} - {remark}"
                        warnings.append(warning)
                        print(f"     ⚠️ 警告: {warning}")
                    
                    print()
                    
                except Exception as e:
                    print(f"     ❌ 分析航班失敗: {e}")
        
        # 類似處理抵達航班...
        
        print(f"分析結果:")
        if warnings:
            print(f"   發現 {len(warnings)} 個警告:")
            for warning in warnings:
                print(f"   • {warning}")
        else:
            print(f"   ✅ 未發現異常狀況")
        
        return warnings
    
    async def run_tests(self):
        """執行所有測試"""
        print("="*60)
        print("🧪 金門機場監控功能測試")
        print("="*60)
        print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 測試 API
        departure_data = await self.test_departure_api()
        print()
        arrival_data = await self.test_arrival_api()
        print()
        
        # 測試分析功能
        if departure_data is not None or arrival_data is not None:
            await self.test_analyze_function(departure_data, arrival_data)
        
        print("\n" + "="*60)
        print("測試完成！")
    
    def get_mock_departure_data(self):
        """取得模擬起飛資料用於測試"""
        return [
            {
                "AirlineID": "B7",
                "FlightNumber": "7881",
                "AircraftType": "ATR72",
                "Destination": "台北松山",
                "ScheduleDepartureTime": "2025-07-04T08:30:00+08:00",
                "EstimatedDepartureTime": "2025-07-04T09:00:00+08:00",
                "ActualDepartureTime": None,
                "DepartureRamp": "1",
                "FlightStatusName": "正常",
                "Remark": ""
            },
            {
                "AirlineID": "UNI",
                "FlightNumber": "B78891",
                "AircraftType": "ATR72",
                "Destination": "台中",
                "ScheduleDepartureTime": "2025-07-04T10:15:00+08:00",
                "EstimatedDepartureTime": "2025-07-04T11:30:00+08:00",
                "ActualDepartureTime": None,
                "DepartureRamp": "2",
                "FlightStatusName": "延誤",
                "Remark": "因天候延誤"
            },
            {
                "AirlineID": "FAT",
                "FlightNumber": "781",
                "AircraftType": "ATR72",
                "Destination": "台南",
                "ScheduleDepartureTime": "2025-07-04T14:00:00+08:00",
                "EstimatedDepartureTime": None,
                "ActualDepartureTime": None,
                "DepartureRamp": "3",
                "FlightStatusName": "取消",
                "Remark": "因颱風影響停飛"
            }
        ]
    
    def get_mock_arrival_data(self):
        """取得模擬抵達資料用於測試"""
        return [
            {
                "AirlineID": "B7",
                "FlightNumber": "7882",
                "AircraftType": "ATR72",
                "Origin": "台北松山",
                "ScheduleArrivalTime": "2025-07-04T09:45:00+08:00",
                "EstimatedArrivalTime": "2025-07-04T09:45:00+08:00",
                "ActualArrivalTime": "2025-07-04T09:42:00+08:00",
                "ArrivalRamp": "1",
                "FlightStatusName": "正常",
                "Remark": ""
            },
            {
                "AirlineID": "UNI",
                "FlightNumber": "B78892",
                "AircraftType": "ATR72",
                "Origin": "台中",
                "ScheduleArrivalTime": "2025-07-04T11:30:00+08:00",
                "EstimatedArrivalTime": "2025-07-04T12:15:00+08:00",
                "ActualArrivalTime": None,
                "ArrivalRamp": "2",
                "FlightStatusName": "延誤",
                "Remark": "機械故障延誤"
            }
        ]
    

async def main():
    """主測試函數"""
    tester = TestAirportMonitor()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
