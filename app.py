"""
颱風警訊播報系統
監控金門縣和台南市的颱風及天氣警報，以及金門機場即時起降資訊
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse
import logging
import hashlib
import hmac
import base64

# LINE Bot SDK
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('typhoon_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 用於現代 FastAPI lifespan 事件
@asynccontextmanager
async def lifespan(app):
    # 啟動時開始監控
    task = asyncio.create_task(continuous_monitoring())
    yield
    # FastAPI 關閉時可在這裡清理資源（如有需要）
    task.cancel()

app = FastAPI(title="颱風警訊播報系統", description="監控金門縣和台南市的颱風警報及金門機場即時起降資訊", lifespan=lifespan)


# 中央氣象署 API 設定
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api"
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.getenv("CWA_API_KEY", "")

# LINE Bot 設定
LINE_CHANNEL_ID = os.getenv("LINE_CHANNEL_ID", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# 初始化 LINE Bot
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 監控設定
MONITOR_LOCATIONS = [s.strip() for s in os.getenv("MONITOR_LOCATIONS", "金門縣,臺南市").split(",") if s.strip()]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300").split("#")[0].strip())
TRAVEL_DATE = os.getenv("TRAVEL_DATE", "2025-07-06")
CHECKUP_DATE = os.getenv("CHECKUP_DATE", "2025-07-07")
SERVER_PORT = int(os.getenv("PORT", os.getenv("SERVER_PORT", "8000")).split("#")[0].strip())

# 全域變數儲存最新狀態
latest_alerts = {}
latest_weather = {}
latest_typhoons = {}
latest_airport_departure = {}
latest_airport_arrival = {}
latest_airport_update_time = None
airport_api_status = "未知"  # "正常", "異常", "未知"
last_notification_status = "SAFE"  # 追蹤上次通知的狀態
line_user_ids = []  # 儲存所有好友的USER ID

class LineNotifier:
    def __init__(self):
        self.api_client = ApiClient(configuration)
        self.line_bot_api = MessagingApi(self.api_client)
    
    def format_typhoon_status(self, result: Dict) -> str:
        """格式化颱風狀態訊息"""
        timestamp = datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))
        status_icon = "🔴" if result["status"] == "DANGER" else "🟢"
        status_text = "有風險" if result["status"] == "DANGER" else "無明顯風險"
        
        message = f"🚨 颱風警報 - {timestamp.strftime('%Y-%m-%d %H:%M')}\n"
        message += f"---------------------------\n"
        message += f"{status_icon} 警告狀態: {status_text}\n\n"
        message += f"✈️ 7/6 金門→台南航班風險: {result['travel_risk']}\n"
        message += f"🏥 7/7 台南體檢風險: {result['checkup_risk']}\n\n"
        
        if result["warnings"]:
            # 分類警告訊息
            flight_warnings = [w for w in result["warnings"] if any(keyword in w for keyword in ['起飛', '抵達', '航班', '停飛', '延誤'])]
            weather_warnings = [w for w in result["warnings"] if w not in flight_warnings]
            
            if flight_warnings:
                message += "� 金門機場即時狀況:\n"
                for warning in flight_warnings:
                    message += f"• {warning}\n"
                message += "\n"
            
            if weather_warnings:
                message += "🌪️ 天氣警報:\n"
                for warning in weather_warnings:
                    message += f"• {warning}\n"
        else:
            message += "✅ 目前無特殊警報\n"
        
        return message.strip()
    
    async def push_to_all_friends(self, message: str):
        """推送訊息給所有好友"""
        if not line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送推送訊息")
            return
        
        try:
            for user_id in line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功推送訊息給 {len(line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"LINE推送失敗: {e}")
    
    async def reply_message(self, reply_token: str, message: str):
        """回覆訊息"""
        try:
            reply_message = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=message)]
            )
            self.line_bot_api.reply_message(reply_message)
            logger.info("成功回覆LINE訊息")
        except Exception as e:
            logger.error(f"LINE回覆失敗: {e}")

# 初始化LINE通知器
line_notifier = LineNotifier()

class AirportMonitor:
    """金門機場起降資訊監控器"""
    
    def __init__(self):
        # 設定SSL驗證為False以解決macOS的SSL問題
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)
        self.base_url = "https://tdx.transportdata.tw/api/basic/v2/Air/FIDS/Airport"
        
    async def get_departure_info(self) -> Dict:
        """取得金門機場起飛航班資訊"""
        try:
            url = f"{self.base_url}/Departure/KNH?$format=JSON"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # 更新全域狀態
            global latest_airport_departure, latest_airport_update_time, airport_api_status
            latest_airport_departure = data
            latest_airport_update_time = datetime.now()
            airport_api_status = "正常"
            
            logger.info(f"成功取得金門機場起飛資訊，共 {len(data) if isinstance(data, list) else 0} 筆航班")
            return data
        except Exception as e:
            logger.warning(f"取得金門機場起飛資訊失敗: {e}")
            global airport_api_status
            airport_api_status = "異常"
            return latest_airport_departure  # 返回最後一次成功的資料
    
    async def get_arrival_info(self) -> Dict:
        """取得金門機場抵達航班資訊"""
        try:
            url = f"{self.base_url}/Arrival/KNH?$format=JSON"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # 更新全域狀態
            global latest_airport_arrival, latest_airport_update_time, airport_api_status
            latest_airport_arrival = data
            latest_airport_update_time = datetime.now()
            airport_api_status = "正常"
            
            logger.info(f"成功取得金門機場抵達資訊，共 {len(data) if isinstance(data, list) else 0} 筆航班")
            return data
        except Exception as e:
            logger.warning(f"取得金門機場抵達資訊失敗: {e}")
            global airport_api_status
            airport_api_status = "異常"
            return latest_airport_arrival  # 返回最後一次成功的資料
            return {}
    
    def analyze_flight_status(self, departure_data: Dict, arrival_data: Dict) -> List[str]:
        """分析航班狀態，檢查停飛或延誤情況"""
        warnings = []
        
        # 檢查 API 狀態並添加相應的警告
        global airport_api_status, latest_airport_update_time
        if airport_api_status == "異常":
            if latest_airport_update_time:
                last_update = latest_airport_update_time.strftime('%Y-%m-%d %H:%M')
                warnings.append(f"⚠️ 機場API連線異常，使用最後更新資料 ({last_update})")
            else:
                warnings.append(f"⚠️ 機場API連線異常，無法取得航班資料")
                return warnings
        elif airport_api_status == "正常" and latest_airport_update_time:
            # 如果資料超過10分鐘沒更新，也提醒
            time_diff = (datetime.now() - latest_airport_update_time).total_seconds() / 60
            if time_diff > 10:
                warnings.append(f"📅 機場資料已 {int(time_diff)} 分鐘未更新")
        
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
        
        # 分析起飛航班
        if departure_data and isinstance(departure_data, list):
            for flight in departure_data:
                try:
                    airline_id = flight.get('AirlineID', '')
                    flight_number = flight.get('FlightNumber', '')
                    destination_code = flight.get('ArrivalAirportID', '')
                    destination = airport_names.get(destination_code, destination_code)
                    schedule_time = flight.get('ScheduleDepartureTime', '')
                    actual_time = flight.get('ActualDepartureTime', '')
                    estimated_time = flight.get('EstimatedDepartureTime', '')
                    remark = flight.get('DepartureRemark', '')
                    gate = flight.get('Gate', '')
                    
                    # 檢查停飛或取消狀況
                    if remark and any(keyword in remark for keyword in ['取消', '停飛', 'CANCELLED', '暫停']):
                        warnings.append(f"✈️ 起飛停飛: {airline_id}{flight_number} → {destination} ({schedule_time[:16]}) - {remark}")
                    
                    # 檢查延誤狀況（實際時間與排定時間差異）
                    elif actual_time and schedule_time:
                        try:
                            from datetime import datetime
                            schedule_dt = datetime.fromisoformat(schedule_time)
                            actual_dt = datetime.fromisoformat(actual_time)
                            delay_minutes = (actual_dt - schedule_dt).total_seconds() / 60
                            
                            # 延誤超過30分鐘才警告
                            if delay_minutes >= 30:
                                warnings.append(f"⏰ 起飛延誤: {airline_id}{flight_number} → {destination} 延誤 {int(delay_minutes)} 分鐘")
                        except:
                            pass
                    
                    # 檢查預計時間延誤
                    elif estimated_time and schedule_time and not actual_time:
                        try:
                            from datetime import datetime
                            schedule_dt = datetime.fromisoformat(schedule_time)
                            estimated_dt = datetime.fromisoformat(estimated_time)
                            delay_minutes = (estimated_dt - schedule_dt).total_seconds() / 60
                            
                            if delay_minutes >= 30:
                                warnings.append(f"⏰ 起飛預計延誤: {airline_id}{flight_number} → {destination} 預計延誤 {int(delay_minutes)} 分鐘")
                        except:
                            pass
                    
                    # 檢查特殊狀態備註
                    if remark and any(keyword in remark for keyword in ['延誤', '異常', '等待', '暫緩']):
                        warnings.append(f"📝 起飛狀況: {airline_id}{flight_number} → {destination} - {remark}")
                
                except Exception as e:
                    logger.error(f"分析起飛航班失敗: {e}")
        
        # 分析抵達航班
        if arrival_data and isinstance(arrival_data, list):
            for flight in arrival_data:
                try:
                    airline_id = flight.get('AirlineID', '')
                    flight_number = flight.get('FlightNumber', '')
                    origin_code = flight.get('DepartureAirportID', '')
                    origin = airport_names.get(origin_code, origin_code)
                    schedule_time = flight.get('ScheduleArrivalTime', '')
                    actual_time = flight.get('ActualArrivalTime', '')
                    estimated_time = flight.get('EstimatedArrivalTime', '')
                    remark = flight.get('ArrivalRemark', '')
                    gate = flight.get('Gate', '')
                    
                    # 檢查停飛或取消狀況
                    if remark and any(keyword in remark for keyword in ['取消', '停飛', 'CANCELLED', '暫停']):
                        warnings.append(f"🛬 抵達停飛: {airline_id}{flight_number} ← {origin} ({schedule_time[:16]}) - {remark}")
                    
                    # 檢查延誤狀況（實際時間與排定時間差異）
                    elif actual_time and schedule_time:
                        try:
                            from datetime import datetime
                            schedule_dt = datetime.fromisoformat(schedule_time)
                            actual_dt = datetime.fromisoformat(actual_time)
                            delay_minutes = (actual_dt - schedule_dt).total_seconds() / 60
                            
                            # 延誤超過30分鐘才警告
                            if delay_minutes >= 30:
                                warnings.append(f"⏰ 抵達延誤: {airline_id}{flight_number} ← {origin} 延誤 {int(delay_minutes)} 分鐘")
                        except:
                            pass
                    
                    # 檢查預計時間延誤
                    elif estimated_time and schedule_time and not actual_time:
                        try:
                            from datetime import datetime
                            schedule_dt = datetime.fromisoformat(schedule_time)
                            estimated_dt = datetime.fromisoformat(estimated_time)
                            delay_minutes = (estimated_dt - schedule_dt).total_seconds() / 60
                            
                            if delay_minutes >= 30:
                                warnings.append(f"⏰ 抵達預計延誤: {airline_id}{flight_number} ← {origin} 預計延誤 {int(delay_minutes)} 分鐘")
                        except:
                            pass
                    
                    # 檢查特殊狀態備註
                    if remark and any(keyword in remark for keyword in ['延誤', '異常', '等待', '暫緩']):
                        warnings.append(f"📝 抵達狀況: {airline_id}{flight_number} ← {origin} - {remark}")
                
                except Exception as e:
                    logger.error(f"分析抵達航班失敗: {e}")
        
        return warnings
    
    async def check_flight_conditions(self) -> List[str]:
        """檢查金門機場航班狀況"""
        logger.info("開始檢查金門機場航班狀況...")
        
        # 並行取得起降資料
        departure_task = self.get_departure_info()
        arrival_task = self.get_arrival_info()
        
        departure_data, arrival_data = await asyncio.gather(
            departure_task, arrival_task, return_exceptions=True
        )
        
        # 處理異常情況
        if isinstance(departure_data, Exception):
            logger.error(f"取得起飛資料失敗: {departure_data}")
            departure_data = {}
        
        if isinstance(arrival_data, Exception):
            logger.error(f"取得抵達資料失敗: {arrival_data}")
            arrival_data = {}
        
        # 分析航班狀態
        flight_warnings = self.analyze_flight_status(departure_data, arrival_data)
        
        return flight_warnings

class TyphoonMonitor:
    def __init__(self):
        # 設定SSL驗證為False以解決macOS的SSL問題
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)
        
    async def get_weather_alerts(self) -> Dict:
        """取得天氣特報資訊"""
        try:
            url = f"{CWA_BASE_URL}/v1/rest/datastore/W-C0033-001"
            params = {
                "Authorization": API_KEY,
                "format": "JSON",
                "locationName": ",".join(MONITOR_LOCATIONS)
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得天氣特報失敗: {e}")
            return {}
    
    async def get_typhoon_paths(self) -> Dict:
        """取得颱風路徑資訊"""
        try:
            url = f"{CWA_BASE_URL}/v1/rest/datastore/W-C0034-005"
            params = {
                "Authorization": API_KEY,
                "format": "JSON"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得颱風路徑失敗: {e}")
            return {}
    
    async def get_weather_forecast(self) -> Dict:
        """取得36小時天氣預報"""
        try:
            url = f"{CWA_BASE_URL}/v1/rest/datastore/F-C0032-001"
            params = {
                "Authorization": API_KEY,
                "format": "JSON",
                "locationName": ",".join(MONITOR_LOCATIONS)
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得天氣預報失敗: {e}")
            return {}
    
    def analyze_alerts(self, alerts_data: Dict) -> List[str]:
        """分析警報資料"""
        warnings = []
        
        if not alerts_data or 'records' not in alerts_data:
            return warnings
        
        try:
            for record in alerts_data.get('records', {}).get('location', []):
                location_name = record.get('locationName', '')
                if location_name in MONITOR_LOCATIONS:
                    hazards = record.get('hazardConditions', {}).get('hazards', [])
                    for hazard in hazards:
                        phenomena = hazard.get('phenomena', '')
                        significance = hazard.get('significance', '')
                        if '颱風' in phenomena or '強風' in phenomena:
                            warnings.append(f"⚠️ {location_name}: {phenomena} {significance}")
        except Exception as e:
            logger.error(f"分析警報資料失敗: {e}")
        
        return warnings
    
    def analyze_typhoons(self, typhoon_data: Dict) -> List[str]:
        """分析颱風路徑資料"""
        warnings = []
        
        if not typhoon_data or 'records' not in typhoon_data:
            return warnings
        
        try:
            for typhoon in typhoon_data.get('records', {}).get('typhoon', []):
                name = typhoon.get('typhoonName', '未知颱風')
                intensity = typhoon.get('intensity', {})
                max_wind = intensity.get('maximumWind', {}).get('value', 0)
                
                # 如果最大風速超過一定值，發出警告
                # 金門機場側風停飛標準：25節(46.3 km/h)，暴風圈標準：34節(63 km/h)
                if max_wind > 60:  # km/h - 調整為更實際的航班風險閾值
                    if max_wind > 80:
                        warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (航班高風險)")
                    else:
                        warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (航班可能影響)")
                    
                    # 檢查預報路徑是否影響目標區域
                    forecasts = typhoon.get('forecast', [])
                    for forecast in forecasts:
                        location = forecast.get('location', {})
                        lat = location.get('lat', 0)
                        lon = location.get('lon', 0)
                        
                        # 簡單的地理區域判斷（台灣範圍）
                        if 22 <= lat <= 25.5 and 119 <= lon <= 122:
                            forecast_time = forecast.get('time', '')
                            warnings.append(f"📍 {name}颱風預報將於 {forecast_time} 接近台灣")
                            break
        except Exception as e:
            logger.error(f"分析颱風資料失敗: {e}")
        
        return warnings
    
    def analyze_weather(self, weather_data: Dict) -> List[str]:
        """分析天氣預報資料"""
        warnings = []
        
        if not weather_data or 'records' not in weather_data:
            return warnings
        
        try:
            for location in weather_data.get('records', {}).get('location', []):
                location_name = location.get('locationName', '')
                if location_name in MONITOR_LOCATIONS:
                    elements = location.get('weatherElement', [])
                    for element in elements:
                        element_name = element.get('elementName', '')
                        if element_name == 'Wx':  # 天氣現象
                            times = element.get('time', [])
                            for time_data in times:
                                start_time = time_data.get('startTime', '')
                                weather_desc = time_data.get('parameter', {}).get('parameterName', '')
                                
                                # 檢查是否有惡劣天氣
                                if any(keyword in weather_desc for keyword in ['颱風', '暴風', '豪雨', '大雨']):
                                    warnings.append(f"🌧️ {location_name} {start_time}: {weather_desc}")
        except Exception as e:
            logger.error(f"分析天氣資料失敗: {e}")
        
        return warnings
    
    async def check_all_conditions(self) -> Dict:
        """檢查所有條件"""
        logger.info("開始檢查天氣條件...")
        
        # 並行取得所有資料
        alerts_task = self.get_weather_alerts()
        typhoons_task = self.get_typhoon_paths()
        weather_task = self.get_weather_forecast()
        departure_task = airport_monitor.get_departure_info()
        arrival_task = airport_monitor.get_arrival_info()
        
        alerts_data, typhoons_data, weather_data, departure_data, arrival_data = await asyncio.gather(
            alerts_task, typhoons_task, weather_task, departure_task, arrival_task, return_exceptions=True
        )
        
        # 更新全域狀態
        global latest_alerts, latest_typhoons, latest_weather, latest_airport_departure, latest_airport_arrival, last_notification_status
        latest_alerts = alerts_data if not isinstance(alerts_data, Exception) else {}
        latest_typhoons = typhoons_data if not isinstance(typhoons_data, Exception) else {}
        latest_weather = weather_data if not isinstance(weather_data, Exception) else {}
        latest_airport_departure = departure_data if not isinstance(departure_data, Exception) else {}
        latest_airport_arrival = arrival_data if not isinstance(arrival_data, Exception) else {}
        
        # 分析機場資料
        flight_warnings = airport_monitor.analyze_flight_status(latest_airport_departure, latest_airport_arrival)
        
        # 分析所有資料
        alert_warnings = self.analyze_alerts(latest_alerts)
        typhoon_warnings = self.analyze_typhoons(latest_typhoons)
        weather_warnings = self.analyze_weather(latest_weather)
        
        all_warnings = alert_warnings + typhoon_warnings + weather_warnings + flight_warnings
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "warnings": all_warnings,
            "status": "DANGER" if all_warnings else "SAFE",
            "travel_risk": self.assess_travel_risk(all_warnings),
            "checkup_risk": self.assess_checkup_risk(all_warnings)
        }
        
        # 輸出警報到控制台
        self.print_alerts(result)
        
        # 檢查是否需要發送LINE通知
        await self.check_and_send_line_notification(result)
        
        return result
    
    async def check_and_send_line_notification(self, result: Dict):
        """檢查並發送LINE通知"""
        global last_notification_status
        current_status = result["status"]
        
        # 只在狀態變化且變為DANGER時發送通知
        if current_status == "DANGER" and last_notification_status != "DANGER":
            message = line_notifier.format_typhoon_status(result)
            await line_notifier.push_to_all_friends(message)
            logger.info("已發送LINE風險通知")
        
        # 更新上次通知狀態
        last_notification_status = current_status
    
    def assess_travel_risk(self, warnings: List[str]) -> str:
        """評估7/6航班風險"""
        if not warnings:
            return "低風險"
        
        typhoon_warnings = [w for w in warnings if '颱風' in w]
        wind_warnings = [w for w in warnings if '強風' in w or '暴風' in w]
        flight_warnings = [w for w in warnings if '停飛' in w or '取消' in w]
        delay_warnings = [w for w in warnings if '延誤' in w]
        
        # 實際航班已有停飛或取消，風險最高
        if flight_warnings:
            return "高風險 - 航班已停飛/取消"
        elif typhoon_warnings:
            return "高風險 - 建議考慮改期"
        elif delay_warnings:
            return "中風險 - 航班可能延誤"
        elif wind_warnings:
            return "中風險 - 密切關注"
        else:
            return "中風險 - 持續監控"
    
    def assess_checkup_risk(self, warnings: List[str]) -> str:
        """評估7/7體檢風險"""
        if not warnings:
            return "低風險"
        
        for warning in warnings:
            if '台南' in warning or '臺南' in warning:
                if '颱風' in warning:
                    return "高風險 - 可能停班停課"
                elif '強風' in warning or '豪雨' in warning:
                    return "中風險 - 可能影響交通"
        
        return "低風險"
    
    def print_alerts(self, result: Dict):
        """在控制台輸出警報"""
        print("\n" + "="*60)
        print(f"🚨 颱風警訊播報系統 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        status = result["status"]
        if status == "DANGER":
            print("🔴 警告狀態: 有風險")
        else:
            print("🟢 安全狀態: 無明顯風險")
        
        print(f"\n✈️ 7/6 金門→台南航班風險: {result['travel_risk']}")
        print(f"🏥 7/7 台南體檢風險: {result['checkup_risk']}")
        
        warnings = result["warnings"]
        if warnings:
            print("\n📢 目前警報:")
            for warning in warnings:
                print(f"  {warning}")
        else:
            print("\n✅ 目前無特殊警報")
        
        print("="*60)

# 建立監控器實例
monitor = TyphoonMonitor()
airport_monitor = AirportMonitor()

async def continuous_monitoring():
    """持續監控"""
    while True:
        try:
            await monitor.check_all_conditions()
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"監控過程發生錯誤: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

## 移除舊的 on_event 寫法，已改用 lifespan

# LINE Webhook 處理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """處理LINE訊息事件"""
    user_id = event.source.user_id
    message_text = event.message.text.strip()
    
    # 將新用戶加入好友列表
    if user_id not in line_user_ids:
        line_user_ids.append(user_id)
        logger.info(f"新增LINE好友: {user_id}")
    
    # 處理"颱風近況"關鍵字
    if "颱風近況" in message_text:
        # 取得最新監控結果
        result = asyncio.create_task(monitor.check_all_conditions())
        # 註：在實際環境中，這裡需要使用異步處理
        # 暫時使用同步方式回覆
        current_result = {
            "timestamp": datetime.now().isoformat(),
            "warnings": [],  # 簡化處理，使用空警報
            "status": "SAFE",
            "travel_risk": "低風險",
            "checkup_risk": "低風險"
        }
        
        reply_message = line_notifier.format_typhoon_status(current_result)
        asyncio.create_task(line_notifier.reply_message(event.reply_token, reply_message))

@app.post("/webhook")
async def line_webhook(request: Request):
    """LINE Webhook端點"""
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    
    # 驗證簽名
    if not _verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    try:
        handler.handle(body.decode('utf-8'), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    return "OK"

def _verify_signature(body: bytes, signature: str) -> bool:
    """驗證LINE簽名"""
    hash_val = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash_val).decode('utf-8')
    return signature == expected_signature

@app.get("/")
async def get_dashboard():
    """取得監控儀表板"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>颱風警訊播報系統 + 金門機場監控</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
            .status-safe {{ color: green; font-size: 24px; font-weight: bold; }}
            .status-danger {{ color: red; font-size: 24px; font-weight: bold; }}
            .warning-item {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 5px 0; border-radius: 5px; }}
            .risk-high {{ color: red; font-weight: bold; }}
            .risk-medium {{ color: orange; font-weight: bold; }}
            .risk-low {{ color: green; font-weight: bold; }}
            .update-time {{ color: #666; font-size: 14px; }}
            .explain-block {{ background: #e3f2fd; border-left: 5px solid #1976d2; padding: 16px; margin: 24px 0; border-radius: 8px; }}
            .explain-block h2 {{ margin-top: 0; color: #1976d2; }}
            .explain-block ul {{ margin: 0 0 0 1.5em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌀 颱風警訊播報系統 + ✈️ 金門機場監控</h1>
            <p class="update-time">最後更新: <span id="updateTime">載入中...</span></p>
            <div id="status">載入中...</div>
            <div id="travelRisk">載入中...</div>
            <div id="checkupRisk">載入中...</div>
            <div id="warnings">載入中...</div>

            <div class="explain-block">
                <h2>🔎 分析邏輯與方法說明</h2>
                <ul>
                    <li><b>天氣特報</b>：直接採用中央氣象署API的警特報結果，若金門或台南有「颱風」或「強風」等現象，則列為警報。</li>
                    <li><b>颱風路徑</b>：
                        <ul>
                            <li>若颱風最大風速 <b>超過60 km/h</b>，則列為警報（接近金門機場停飛標準）。</li>
                            <li>若颱風最大風速 <b>超過80 km/h</b>，則列為高風險警報。</li>
                            <li>若颱風預報路徑座標 <b>落在台灣經緯度範圍（緯度22~25.5，經度119~122）</b>，則視為「接近台灣」並警示。</li>
                            <li><small>📍 參考：金門機場側風停飛標準為25節(46.3 km/h)，暴風圈標準為34節(63 km/h)</small></li>
                        </ul>
                    </li>
                    <li><b>天氣預報</b>：
                        <ul>
                            <li>若36小時內預報有「颱風」、「暴風」、「豪雨」、「大雨」等關鍵字，則列為警報。</li>
                        </ul>
                    </li>
                    <li><b>金門機場即時監控</b>：
                        <ul>
                            <li>監控金門機場（KNH）起飛和抵達航班的即時狀況。</li>
                            <li>若航班狀態為「取消」或「停飛」，立即列為高風險警報。</li>
                            <li>若預計時間比排定時間 <b>延誤30分鐘以上</b>，列為延誤警報。</li>
                            <li>若備註中包含「延誤」、「取消」、「停飛」等關鍵字，列為異常警報。</li>
                        </ul>
                    </li>
                    <li><b>航班/體檢風險評估</b>：
                        <ul>
                            <li>若有實際航班停飛/取消，航班列為「高風險」（優先級最高）。</li>
                            <li>若有颱風警報，航班列為「高風險」；有強風則為「中風險」。</li>
                            <li>若有航班延誤，列為「中風險」。</li>
                            <li>台南有颱風警報，體檢列為「高風險」；有強風或豪雨則為「中風險」。</li>
                        </ul>
                    </li>
                </ul>
                <p style="color:#555;font-size:14px;">（所有分析規則皆可於程式碼內各分析方法查閱與調整。機場資料來源：交通部TDX運輸資料流通服務）</p>
            </div>
        </div>
        <script>
            async function updateData() {{
                try {{
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    document.getElementById('updateTime').textContent = new Date(data.timestamp).toLocaleString('zh-TW');
                    const statusDiv = document.getElementById('status');
                    if (data.status === 'DANGER') {{
                        statusDiv.innerHTML = '<div class="status-danger">🔴 警告狀態: 有風險</div>';
                    }} else {{
                        statusDiv.innerHTML = '<div class="status-safe">🟢 安全狀態: 無明顯風險</div>';
                    }}
                    document.getElementById('travelRisk').innerHTML = `<p>✈️ 7/6 金門→台南航班風險: <span class="risk-${{getRiskClass(data.travel_risk)}}">${{data.travel_risk}}</span></p>`;
                    document.getElementById('checkupRisk').innerHTML = `<p>🏥 7/7 台南體檢風險: <span class="risk-${{getRiskClass(data.checkup_risk)}}">${{data.checkup_risk}}</span></p>`;
                    const warningsDiv = document.getElementById('warnings');
                    if (data.warnings.length > 0) {{
                        warningsDiv.innerHTML = '<h3>📢 目前警報:</h3>' + 
                            data.warnings.map(w => `<div class="warning-item">${{w}}</div>`).join('');
                    }} else {{
                        warningsDiv.innerHTML = '<h3>✅ 目前無特殊警報</h3>';
                    }}
                }} catch (error) {{
                    console.error('更新資料失敗:', error);
                }}
            }}
            function getRiskClass(risk) {{
                if (risk.includes('高風險')) return 'high';
                if (risk.includes('中風險')) return 'medium';
                return 'low';
            }}
            // 每30秒更新一次
            updateData();
            setInterval(updateData, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/status")
async def get_status():
    """取得目前狀態"""
    return await monitor.check_all_conditions()

@app.get("/api/raw-data")
async def get_raw_data():
    """取得原始資料"""
    return {
        "alerts": latest_alerts,
        "typhoons": latest_typhoons,
        "weather": latest_weather,
        "airport_departure": latest_airport_departure,
        "airport_arrival": latest_airport_arrival
    }

@app.get("/api/line/friends")
async def get_line_friends():
    """取得LINE好友列表"""
    return {
        "friends_count": len(line_user_ids),
        "last_notification_status": last_notification_status
    }

@app.post("/api/line/test-notification")
async def send_test_notification():
    """發送測試通知給所有LINE好友"""
    test_result = {
        "timestamp": datetime.now().isoformat(),
        "warnings": ["🧪 這是測試訊息"],
        "status": "DANGER",
        "travel_risk": "測試風險",
        "checkup_risk": "測試風險"
    }
    
    message = line_notifier.format_typhoon_status(test_result)
    await line_notifier.push_to_all_friends(message)
    
    return {
        "message": "測試通知已發送",
        "sent_to": len(line_user_ids),
        "friends": line_user_ids
    }

@app.get("/api/airport")
async def get_airport_status():
    """取得金門機場即時起降資訊"""
    departure_info = await airport_monitor.get_departure_info()
    arrival_info = await airport_monitor.get_arrival_info()
    flight_warnings = await airport_monitor.check_flight_conditions()
    
    return {
        "departure_flights": departure_info,
        "arrival_flights": arrival_info,
        "warnings": flight_warnings,
        "last_updated": datetime.now().isoformat()
    }

def main():
    """主函數"""
    print("🌀 颱風警訊播報系統啟動中...")
    print("📝 系統資訊:")
    print(f"- 監控地區: {', '.join(MONITOR_LOCATIONS)}")
    print(f"- 檢查間隔: {CHECK_INTERVAL} 秒")
    print(f"- 服務端口: {SERVER_PORT}")
    print(f"- 旅行日期: {TRAVEL_DATE}")
    print(f"- 體檢日期: {CHECKUP_DATE}")
    print("- 機場監控: 金門機場 (KNH) 起降資訊")
    
    if not API_KEY:
        print("⚠️ 警告: 中央氣象署API KEY尚未設定")
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("⚠️ 警告: LINE ACCESS TOKEN尚未設定，LINE功能將無法使用")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)

if __name__ == "__main__":
    main()
