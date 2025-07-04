"""
LINE Bot notification service for Typhoon Weather Monitor
Handles LINE Bot messaging and notifications
"""

import logging
import os
from datetime import datetime
from typing import Dict, List
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, 
    TextMessage, FlexMessage
)
from config.settings import settings
from notifications.flex_message_builder import FlexMessageBuilder

logger = logging.getLogger(__name__)

class LineNotifier:
    """LINE Bot notification service"""
    
    def __init__(self):
        # Initialize LINE Bot configuration
        self.configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        self.api_client = ApiClient(self.configuration)
        self.line_bot_api = MessagingApi(self.api_client)
        
        # Initialize FlexMessageBuilder
        app_url = os.getenv("APP_URL", settings.get_base_url())
        self.flex_builder = FlexMessageBuilder(base_url=app_url)
        
        # Store user IDs for notifications
        self.line_user_ids = []
    
    def set_user_ids(self, user_ids: List[str]):
        """Set LINE user IDs for notifications"""
        self.line_user_ids = user_ids
    
    def format_typhoon_status(self, result: Dict) -> str:
        """格式化颱風狀態訊息（保留文字版本作為備用）"""
        timestamp = datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))
        status_icon = "🔴" if result["status"] == "DANGER" else "🟢"
        status_text = "有風險" if result["status"] == "DANGER" else "無明顯風險"
        
        message = f"🚨 颱風警報 - {timestamp.strftime('%Y-%m-%d %H:%M')}\n"
        message += f"---------------------------\n"
        message += f"{status_icon} 警告狀態: {status_text}\n\n"
        message += f"✈️ 7/6 金門→台南航班風險: {result['travel_risk']}\n"
        
        # 處理可能包含詳細分析的體檢風險
        checkup_risk = result['checkup_risk']
        if "\n詳細分析:" in checkup_risk:
            main_risk, details = checkup_risk.split("\n詳細分析:", 1)
            message += f"🏥 7/7 台南體檢風險: {main_risk}\n"
            message += f"   📊 地理分析: {details.strip()}\n"
        else:
            message += f"🏥 7/7 台南體檢風險: {checkup_risk}\n"
        
        message += "\n"
        
        if result["warnings"]:
            # 所有警告都視為天氣警告（機場功能已禁用）
            weather_warnings = result["warnings"]
            
            if weather_warnings:
                message += "🌪️ 天氣警報:\n"
                for warning in weather_warnings:
                    message += f"• {warning}\n"
                message += "\n"
        else:
            message += "✅ 目前無特殊警報\n\n"
        
        # 添加颱風詳細資料
        typhoon_details = self._get_typhoon_details()
        if typhoon_details:
            message += "📊 颱風詳細資料:\n"
            message += typhoon_details
        
        return message.strip()
    
    def _get_typhoon_details(self) -> str:
        """取得颱風詳細資料（風速、強度等）"""
        details = ""
        
        # Get data from global storage
        from utils.helpers import get_global_data
        data = get_global_data()
        latest_typhoons = data['latest_typhoons']
        latest_weather = data['latest_weather']
        latest_alerts = data['latest_alerts']
        
        if latest_typhoons:
            try:
                records = latest_typhoons.get('records', {})
                typhoon_found = False
                
                # 新的颱風資料結構
                if 'tropicalCyclones' in records:
                    tropical_cyclones = records['tropicalCyclones']
                    typhoons = tropical_cyclones.get('tropicalCyclone', [])
                    
                    for typhoon in typhoons:
                        if not isinstance(typhoon, dict):
                            continue
                        
                        # 颱風基本資訊
                        typhoon_name = typhoon.get('typhoonName', '')
                        cwa_typhoon_name = typhoon.get('cwaTyphoonName', '')
                        cwa_td_no = typhoon.get('cwaTdNo', '')
                        cwa_ty_no = typhoon.get('cwaTyNo', '')
                        
                        name = cwa_typhoon_name or typhoon_name or f"熱帶性低氣壓 {cwa_td_no}"
                        details += f"🌀 名稱: {name}\n"
                        typhoon_found = True
                        
                        if cwa_ty_no:
                            details += f"🏷️ 颱風編號: {cwa_ty_no}\n"
                        elif cwa_td_no:
                            details += f"🏷️ 熱帶性低氣壓編號: {cwa_td_no}\n"
                        
                        # 從最新分析資料取得詳細資訊
                        analysis_data = typhoon.get('analysisData', {})
                        fixes = analysis_data.get('fix', [])
                        
                        if fixes:
                            latest_fix = fixes[-1]  # 取最新的資料
                            
                            # 風速資訊
                            max_wind_speed = latest_fix.get('maxWindSpeed', '')
                            max_gust_speed = latest_fix.get('maxGustSpeed', '')
                            if max_wind_speed:
                                max_wind_kmh = int(max_wind_speed) * 3.6  # m/s 轉 km/h
                                details += f"💨 最大風速: {max_wind_speed} m/s ({max_wind_kmh:.1f} km/h)\n"
                            if max_gust_speed:
                                max_gust_kmh = int(max_gust_speed) * 3.6
                                details += f"💨 最大陣風: {max_gust_speed} m/s ({max_gust_kmh:.1f} km/h)\n"
                            
                            # 中心氣壓
                            pressure = latest_fix.get('pressure', '')
                            if pressure:
                                details += f"📊 中心氣壓: {pressure} hPa\n"
                            
                            # 移動資訊
                            moving_speed = latest_fix.get('movingSpeed', '')
                            moving_direction = latest_fix.get('movingDirection', '')
                            if moving_speed:
                                details += f"🏃 移動速度: {moving_speed} km/h\n"
                            if moving_direction:
                                direction_map = {
                                    'N': '北', 'NNE': '北北東', 'NE': '東北', 'ENE': '東北東',
                                    'E': '東', 'ESE': '東南東', 'SE': '東南', 'SSE': '南南東',
                                    'S': '南', 'SSW': '南南西', 'SW': '西南', 'WSW': '西南西',
                                    'W': '西', 'WNW': '西北西', 'NW': '西北', 'NNW': '北北西'
                                }
                                direction_zh = direction_map.get(moving_direction, moving_direction)
                                details += f"➡️ 移動方向: {direction_zh} ({moving_direction})\n"
                            
                            # 座標位置
                            coordinate = latest_fix.get('coordinate', '')
                            fix_time = latest_fix.get('fixTime', '')
                            if coordinate:
                                try:
                                    lon, lat = coordinate.split(',')
                                    details += f"📍 座標位置: {lat}°N, {lon}°E\n"
                                except:
                                    details += f"📍 座標位置: {coordinate}\n"
                            
                            if fix_time:
                                details += f"🕐 觀測時間: {fix_time[:16]}\n"
                        
                        # 暴風圈資訊
                        if fixes:
                            latest_fix = fixes[-1]
                            circle_of_15ms = latest_fix.get('circleOf15Ms', {})
                            if circle_of_15ms:
                                radius = circle_of_15ms.get('radius', '')
                                if radius:
                                    details += f"🌪️ 暴風圈半徑: {radius} km\n"
                        
                        # 只顯示第一個颱風的詳細資料
                        break
                
                # 如果沒找到颱風資料，但有其他氣象資料
                if not typhoon_found:
                    details += "🌀 目前無活躍颱風資料\n"
                    
            except Exception as e:
                logger.warning(f"解析颱風詳細資料失敗: {e}")
        
        # 添加天氣預報原始資料
        weather_details = self._get_weather_raw_data()
        if weather_details:
            details += "\n📊 天氣原始資料:\n"
            details += weather_details
        
        # 添加風險評估說明
        if details:
            details += "\n📋 風險評估依據:\n"
            details += "• 颱風風速 >80km/h = 高風險\n"
            details += "• 颱風風速 60-80km/h = 中風險\n"
            details += "• 大雨/豪雨預報 = 中-高風險\n"
            details += "• 強風特報 = 中風險\n"
            details += "• 暴風圈範圍 = 高度關注\n"
        
        return details
    
    def _get_weather_raw_data(self) -> str:
        """取得天氣預報原始資料"""
        weather_info = ""
        
        try:
            # Get data from global storage
            from utils.helpers import get_global_data
            data = get_global_data()
            latest_weather = data['latest_weather']
            latest_alerts = data['latest_alerts']
            
            # 從天氣預報資料中提取原始數據
            if latest_weather and 'records' in latest_weather:
                for location in latest_weather.get('records', {}).get('location', []):
                    location_name = location.get('locationName', '')
                    if location_name in settings.MONITOR_LOCATIONS:
                        weather_info += f"\n🏃 {location_name}:\n"
                        
                        elements = location.get('weatherElement', [])
                        for element in elements:
                            element_name = element.get('elementName', '')
                            times = element.get('time', [])
                            
                            if element_name == 'Wx' and times:  # 天氣現象
                                latest_time = times[0]
                                weather_desc = latest_time.get('parameter', {}).get('parameterName', '')
                                start_time = latest_time.get('startTime', '')
                                if weather_desc:
                                    weather_info += f"  🌤️ 天氣: {weather_desc}\n"
                                    weather_info += f"  🕐 時間: {start_time[:16]}\n"
                            
                            elif element_name == 'PoP' and times:  # 降雨機率
                                latest_time = times[0]
                                pop_value = latest_time.get('parameter', {}).get('parameterName', '')
                                if pop_value:
                                    weather_info += f"  🌧️ 降雨機率: {pop_value}%\n"
                            
                            elif element_name == 'MinT' and times:  # 最低溫度
                                latest_time = times[0]
                                min_temp = latest_time.get('parameter', {}).get('parameterName', '')
                                if min_temp:
                                    weather_info += f"  🌡️ 最低溫: {min_temp}°C\n"
                            
                            elif element_name == 'MaxT' and times:  # 最高溫度
                                latest_time = times[0]
                                max_temp = latest_time.get('parameter', {}).get('parameterName', '')
                                if max_temp:
                                    weather_info += f"  🌡️ 最高溫: {max_temp}°C\n"
                            
                            elif element_name == 'CI' and times:  # 舒適度指數
                                latest_time = times[0]
                                comfort = latest_time.get('parameter', {}).get('parameterName', '')
                                if comfort:
                                    weather_info += f"  😌 舒適度: {comfort}\n"
                        
                        weather_info += "\n"
            
            # 從天氣特報中提取原始資料
            if latest_alerts and 'records' in latest_alerts:
                alert_info = ""
                for record in latest_alerts.get('records', {}).get('location', []):
                    location_name = record.get('locationName', '')
                    if location_name in settings.MONITOR_LOCATIONS:
                        hazards = record.get('hazardConditions', {}).get('hazards', [])
                        if hazards:
                            alert_info += f"⚠️ {location_name} 特報:\n"
                            for hazard in hazards:
                                phenomena = hazard.get('phenomena', '')
                                significance = hazard.get('significance', '')
                                effective_time = hazard.get('effectiveTime', '')
                                if phenomena:
                                    alert_info += f"  📢 {phenomena} {significance}\n"
                                    if effective_time:
                                        alert_info += f"  🕐 生效時間: {effective_time[:16]}\n"
                            alert_info += "\n"
                
                if alert_info:
                    weather_info += alert_info
                    
        except Exception as e:
            logger.warning(f"解析天氣原始資料失敗: {e}")
        
        return weather_info.strip()
    
    async def push_typhoon_status_flex(self, result: Dict):
        """推送颱風狀態 Flex Message 給所有好友"""
        if not self.line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送推送訊息")
            return
        
        try:
            flex_container = self.flex_builder.create_typhoon_status_flex(result)
            flex_message = FlexMessage(alt_text="颱風警訊播報", contents=flex_container)
            
            for user_id in self.line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[flex_message]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功推送 Flex Message 給 {len(self.line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"LINE Flex 推送失敗，嘗試文字版本: {e}")
            # 失敗時回退到文字訊息
            text_message = self.format_typhoon_status(result)
            await self.push_to_all_friends(text_message)
    
    async def push_airport_status_flex(self, airport_data: Dict):
        """推送機場狀態 Flex Message 給所有好友（已禁用）"""
        logger.warning("Airport functionality is disabled")
        return
    
    async def push_to_all_friends(self, message: str):
        """推送文字訊息給所有好友（備用方法）"""
        if not self.line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送推送訊息")
            return
        
        try:
            for user_id in self.line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功推送文字訊息給 {len(self.line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"LINE推送失敗: {e}")
    
    async def push_text_message(self, message: str):
        """推送純文字訊息給所有用戶"""
        await self.push_to_all_friends(message)
    
    async def reply_typhoon_status_flex(self, reply_token: str, result: Dict):
        """回覆颱風狀態 Flex Message"""
        try:
            flex_container = self.flex_builder.create_typhoon_status_flex(result)
            flex_message = FlexMessage(alt_text="颱風警訊播報", contents=flex_container)
            
            reply_message = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[flex_message]
            )
            self.line_bot_api.reply_message(reply_message)
            logger.info("成功回覆 Flex Message")
        except Exception as e:
            logger.error(f"LINE Flex 回覆失敗，嘗試文字版本: {e}")
            # 失敗時回退到文字訊息
            text_message = self.format_typhoon_status(result)
            await self.reply_message(reply_token, text_message)
    
    async def reply_message(self, reply_token: str, message: str):
        """回覆文字訊息（備用方法）"""
        try:
            reply_message = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=message)]
            )
            self.line_bot_api.reply_message(reply_message)
            logger.info("成功回覆LINE訊息")
        except Exception as e:
            logger.error(f"LINE回覆失敗: {e}")
    
    async def send_test_notification_flex(self):
        """發送測試 Flex Message"""
        if not self.line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送測試訊息")
            return
        
        try:
            flex_container = self.flex_builder.create_test_notification_flex("🧪 LINE Bot Flex Message 測試成功！")
            flex_message = FlexMessage(alt_text="系統測試通知", contents=flex_container)
            
            for user_id in self.line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[flex_message]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功發送測試 Flex Message 給 {len(self.line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"測試 Flex Message 發送失敗: {e}")

# LINE Bot Webhook Handler
def create_webhook_handler() -> WebhookHandler:
    """Create LINE Bot webhook handler"""
    return WebhookHandler(settings.LINE_CHANNEL_SECRET)