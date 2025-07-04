"""
LINE Bot notification service for Typhoon Weather Monitor
Handles LINE Bot messaging and notifications
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, 
    TextMessage, FlexMessage as LineFlexMessage, FlexContainer, FlexBubble, FlexBox,
    FlexText, FlexButton, FlexSeparator, FlexFiller, MessageAction, URIAction
)
from config.settings import settings
from notifications.flex_message_builder import FlexMessageFactory
from models.flex_message_models import TyphoonData, WeatherData

logger = logging.getLogger(__name__)

class LineNotifier:
    """LINE Bot notification service"""
    
    def __init__(self):
        # Initialize LINE Bot configuration
        self.configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        self.api_client = ApiClient(self.configuration)
        self.line_bot_api = MessagingApi(self.api_client)
        
        # Initialize FlexMessage factory
        self.flex_factory = FlexMessageFactory()
        
        # Feature flags
        self.use_flex_messages = getattr(settings, 'USE_FLEX_MESSAGES', True)
        self.flex_fallback_enabled = getattr(settings, 'FLEX_FALLBACK_ENABLED', True)
        
        # Store user IDs for notifications
        self.line_user_ids = []
    
    def _convert_to_line_flex_container(self, flex_message) -> FlexContainer:
        """Convert our FlexMessage to LINE SDK FlexContainer"""
        try:
            # Get the message dictionary
            message_dict = flex_message.to_dict()
            contents = message_dict.get("contents", {})
            
            if contents.get("type") == "bubble":
                return self._convert_bubble(contents)
            else:
                raise ValueError(f"Unsupported container type: {contents.get('type')}")
                
        except Exception as e:
            logger.error(f"Failed to convert FlexMessage to LINE format: {e}")
            raise
    
    def _convert_bubble(self, bubble_dict: Dict) -> FlexBubble:
        """Convert bubble dictionary to LINE FlexBubble"""
        bubble_kwargs = {}
        
        # Convert header if present
        if "header" in bubble_dict:
            bubble_kwargs["header"] = self._convert_box(bubble_dict["header"])
        
        # Convert body if present
        if "body" in bubble_dict:
            bubble_kwargs["body"] = self._convert_box(bubble_dict["body"])
        
        # Convert footer if present
        if "footer" in bubble_dict:
            bubble_kwargs["footer"] = self._convert_box(bubble_dict["footer"])
        
        return FlexBubble(**bubble_kwargs)
    
    def _convert_box(self, box_dict: Dict) -> FlexBox:
        """Convert box dictionary to LINE FlexBox"""
        # Convert contents
        contents = []
        for content in box_dict.get("contents", []):
            converted_content = self._convert_component(content)
            if converted_content:
                contents.append(converted_content)
        
        # Build FlexBox kwargs
        box_kwargs = {
            "layout": box_dict.get("layout", "vertical"),
            "contents": contents
        }
        
        # Add optional properties
        optional_props = ["spacing", "margin", "paddingAll", "paddingTop", "paddingBottom", 
                         "paddingStart", "paddingEnd", "backgroundColor", "borderColor", 
                         "borderWidth", "cornerRadius", "flex"]
        
        for prop in optional_props:
            if prop in box_dict:
                # Convert camelCase to snake_case for Python
                python_prop = self._camel_to_snake(prop)
                box_kwargs[python_prop] = box_dict[prop]
        
        return FlexBox(**box_kwargs)
    
    def _convert_component(self, component_dict: Dict):
        """Convert component dictionary to appropriate LINE component"""
        component_type = component_dict.get("type")
        
        if component_type == "text":
            return self._convert_text(component_dict)
        elif component_type == "button":
            return self._convert_button(component_dict)
        elif component_type == "separator":
            return self._convert_separator(component_dict)
        elif component_type == "spacer":
            return self._convert_spacer(component_dict)
        elif component_type == "filler":
            return self._convert_filler(component_dict)
        elif component_type == "box":
            return self._convert_box(component_dict)
        else:
            logger.warning(f"Unsupported component type: {component_type}")
            return None
    
    def _convert_text(self, text_dict: Dict) -> FlexText:
        """Convert text dictionary to LINE FlexText"""
        text_kwargs = {
            "text": text_dict.get("text", "")
        }
        
        # Add optional properties
        optional_props = ["size", "weight", "color", "align", "wrap", "maxLines", "flex"]
        
        for prop in optional_props:
            if prop in text_dict:
                python_prop = self._camel_to_snake(prop)
                text_kwargs[python_prop] = text_dict[prop]
        
        return FlexText(**text_kwargs)
    
    def _convert_button(self, button_dict: Dict) -> FlexButton:
        """Convert button dictionary to LINE FlexButton"""
        action_data = button_dict.get("action", {})
        action_type = action_data.get("type")
        
        line_action = None
        if action_type == "message":
            line_action = MessageAction(
                label=action_data.get("label", "Action"),
                text=action_data.get("text", "Message")
            )
        elif action_type == "uri":
            line_action = URIAction(
                label=action_data.get("label", "Action"),
                uri=action_data.get("uri", "#")
            )
        else:
            logger.warning(f"Unsupported action type for button: {action_type}")
            # Fallback to a default action if type is unknown or missing
            line_action = MessageAction(label="Unsupported", text="Unsupported Action")

        button_kwargs = {
            "action": line_action
        }
        
        # Add optional properties
        optional_props = ["style", "color", "height", "margin", "flex"]
        
        for prop in optional_props:
            if prop in button_dict:
                button_kwargs[prop] = button_dict[prop]
        
        return FlexButton(**button_kwargs)
    
    def _convert_separator(self, separator_dict: Dict) -> FlexSeparator:
        """Convert separator dictionary to LINE FlexSeparator"""
        separator_kwargs = {}
        
        # Add optional properties
        optional_props = ["margin", "color"]
        
        for prop in optional_props:
            if prop in separator_dict:
                separator_kwargs[prop] = separator_dict[prop]
        
        return FlexSeparator(**separator_kwargs)
    
    def _convert_spacer(self, spacer_dict: Dict) -> FlexFiller:
        """Convert spacer dictionary to LINE FlexFiller"""
        return FlexFiller()
    
    def _convert_filler(self, filler_dict: Dict) -> FlexFiller:
        """Convert filler dictionary to LINE FlexFiller"""
        return FlexFiller()
    
    def _camel_to_snake(self, camel_str: str) -> str:
        """Convert camelCase to snake_case"""
        import re
        # Insert underscores before uppercase letters that follow lowercase letters
        s1 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', camel_str)
        return s1.lower()
    
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
        message += f"✈️ 7/6 金門→台南航班風險: {result.get('travel_risk') or '未知'}\n"
        
        # 處理可能包含詳細分析的體檢風險
        checkup_risk = result.get('checkup_risk') or '未知'
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
    
    def _extract_typhoon_data(self) -> TyphoonData:
        """Extract typhoon data for FlexMessage"""
        try:
            from utils.helpers import get_global_data
            data = get_global_data()
            latest_typhoons = data['latest_typhoons']
            
            if not latest_typhoons:
                return None
            
            records = latest_typhoons.get('records', {})
            if 'tropicalCyclones' in records:
                tropical_cyclones = records['tropicalCyclones']
                typhoons = tropical_cyclones.get('tropicalCyclone', [])
                
                for typhoon in typhoons:
                    if not isinstance(typhoon, dict):
                        continue
                    
                    # Extract typhoon information
                    typhoon_name = typhoon.get('typhoonName', '')
                    cwa_typhoon_name = typhoon.get('cwaTyphoonName', '')
                    cwa_td_no = typhoon.get('cwaTdNo', '')
                    
                    name = cwa_typhoon_name or typhoon_name or f"熱帶性低氣壓 {cwa_td_no}"
                    
                    # Get analysis data
                    analysis_data = typhoon.get('analysisData', {})
                    fixes = analysis_data.get('fix', [])
                    
                    if fixes:
                        latest_fix = fixes[-1]
                        
                        wind_speed = latest_fix.get('maxWindSpeed', '')
                        max_gust = latest_fix.get('maxGustSpeed', '')
                        pressure = latest_fix.get('pressure', '')
                        moving_speed = latest_fix.get('movingSpeed', '')
                        moving_direction = latest_fix.get('movingDirection', '')
                        coordinate = latest_fix.get('coordinate', '')
                        fix_time = latest_fix.get('fixTime', '')
                        
                        # Convert coordinate to readable format
                        location = None
                        if coordinate:
                            try:
                                lon, lat = coordinate.split(',')
                                location = f"{lat}°N, {lon}°E"
                            except:
                                location = coordinate
                        
                        # Get storm circle radius
                        radius = None
                        circle_of_15ms = latest_fix.get('circleOf15Ms', {})
                        if circle_of_15ms:
                            radius = circle_of_15ms.get('radius', '')
                        
                        return TyphoonData(
                            name=name,
                            wind_speed=wind_speed,
                            max_gust=max_gust,
                            pressure=pressure,
                            location=location,
                            direction=moving_direction,
                            speed=moving_speed,
                            radius=radius,
                            time=fix_time[:16] if fix_time else None
                        )
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract typhoon data: {e}")
            return None
    
    def _extract_weather_data(self) -> List[WeatherData]:
        """Extract weather data for FlexMessage"""
        try:
            from utils.helpers import get_global_data
            data = get_global_data()
            latest_weather = data['latest_weather']
            
            weather_list = []
            
            if latest_weather and 'records' in latest_weather:
                for location in latest_weather.get('records', {}).get('location', []):
                    location_name = location.get('locationName', '')
                    if location_name in settings.MONITOR_LOCATIONS:
                        
                        weather_data = WeatherData(location=location_name)
                        
                        elements = location.get('weatherElement', [])
                        for element in elements:
                            element_name = element.get('elementName', '')
                            times = element.get('time', [])
                            
                            if element_name == 'Wx' and times:  # Weather description
                                latest_time = times[0]
                                weather_desc = latest_time.get('parameter', {}).get('parameterName', '')
                                weather_data.weather_description = weather_desc
                            
                            elif element_name == 'PoP' and times:  # Rain probability
                                latest_time = times[0]
                                pop_value = latest_time.get('parameter', {}).get('parameterName', '')
                                weather_data.rain_probability = pop_value
                            
                            elif element_name == 'MinT' and times:  # Min temperature
                                latest_time = times[0]
                                min_temp = latest_time.get('parameter', {}).get('parameterName', '')
                                weather_data.temperature_min = min_temp
                            
                            elif element_name == 'MaxT' and times:  # Max temperature
                                latest_time = times[0]
                                max_temp = latest_time.get('parameter', {}).get('parameterName', '')
                                weather_data.temperature_max = max_temp
                            
                            elif element_name == 'CI' and times:  # Comfort index
                                latest_time = times[0]
                                comfort = latest_time.get('parameter', {}).get('parameterName', '')
                                weather_data.comfort_level = comfort
                        
                        weather_list.append(weather_data)
            
            return weather_list
            
        except Exception as e:
            logger.warning(f"Failed to extract weather data: {e}")
            return []
    
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
    
    async def push_typhoon_status(self, result: Dict):
        """推送颱風狀態訊息給所有好友（支援 FlexMessage 和文字備援）"""
        if not self.line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送推送訊息")
            return
        
        try:
            # Try FlexMessage first if enabled
            if self.use_flex_messages:
                success = await self._push_typhoon_flex(result)
                if success:
                    return
                elif not self.flex_fallback_enabled:
                    logger.error("FlexMessage failed and fallback is disabled")
                    return
            
            # Fallback to text message
            text_message = self.format_typhoon_status(result)
            await self.push_to_all_friends(text_message)
            
        except Exception as e:
            logger.error(f"LINE 推送失敗: {e}")
    
    async def _push_typhoon_flex(self, result: Dict) -> bool:
        """推送 FlexMessage 颱風狀態"""
        try:
            # Extract data for FlexMessage
            typhoon_data = self._extract_typhoon_data()
            weather_data = self._extract_weather_data()
            
            # Debug log extracted data
            logger.debug(f"Push - Extracted typhoon_data: {typhoon_data}")
            logger.debug(f"Push - Extracted weather_data: {weather_data}")
            logger.debug(f"Push - Result data: {result}")
            
            # Create FlexMessage
            flex_message = self.flex_factory.create_typhoon_status_message(
                result, typhoon_data, weather_data
            )
            
            # Validate message
            if not self.flex_factory.validate_message(flex_message):
                logger.warning("FlexMessage validation failed")
                # Log the invalid message for debugging
                try:
                    invalid_json = self.flex_factory.to_json(flex_message)
                    logger.error(f"Invalid FlexMessage JSON: {invalid_json}")
                except Exception as json_error:
                    logger.error(f"Failed to serialize invalid FlexMessage: {json_error}")
                return False
            
            # Convert to LINE API format using FlexContainer objects
            line_flex_container = self._convert_to_line_flex_container(flex_message)
            line_flex = LineFlexMessage(
                alt_text=flex_message.alt_text,
                contents=line_flex_container
            )
            
            # Debug log the final message structure
            logger.debug(f"Sending FlexMessage with alt_text: {flex_message.alt_text}")
            logger.debug(f"FlexMessage container type: {type(line_flex_container)}")
            
            # Send to all users
            for user_id in self.line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[line_flex]
                )
                self.line_bot_api.push_message(push_message)
            
            logger.info(f"成功推送 FlexMessage 給 {len(self.line_user_ids)} 位好友")
            return True
            
        except Exception as e:
            logger.warning(f"FlexMessage 推送失敗，使用文字備援: {e}")
            return False
    
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
    
    async def reply_typhoon_status(self, reply_token: str, result: Dict):
        """回覆颱風狀態訊息（支援 FlexMessage 和文字備援）"""
        try:
            # Try FlexMessage first if enabled
            if self.use_flex_messages:
                success = await self._reply_typhoon_flex(reply_token, result)
                if success:
                    return
                elif not self.flex_fallback_enabled:
                    logger.error("FlexMessage failed and fallback is disabled")
                    return
            
            # Fallback to text message
            text_message = self.format_typhoon_status(result)
            await self.reply_message(reply_token, text_message)
            
        except Exception as e:
            error_msg = str(e)
            if "Invalid reply token" in error_msg:
                logger.warning(f"Reply token 已過期或無效，跳過回覆: {reply_token}")
                return
            else:
                logger.error(f"LINE 回覆失敗: {e}")
    
    async def _reply_typhoon_flex(self, reply_token: str, result: Dict) -> bool:
        """回覆 FlexMessage 颱風狀態"""
        try:
            # Extract data for FlexMessage
            typhoon_data = self._extract_typhoon_data()
            weather_data = self._extract_weather_data()
            
            # Debug log extracted data
            logger.debug(f"Reply - Extracted typhoon_data: {typhoon_data}")
            logger.debug(f"Reply - Extracted weather_data: {weather_data}")
            logger.debug(f"Reply - Result data: {result}")
            
            # Create FlexMessage
            flex_message = self.flex_factory.create_typhoon_status_message(
                result, typhoon_data, weather_data
            )
            
            # Validate message
            if not self.flex_factory.validate_message(flex_message):
                logger.warning("FlexMessage validation failed")
                # Log the invalid message for debugging
                try:
                    invalid_json = self.flex_factory.to_json(flex_message)
                    logger.error(f"Invalid FlexMessage JSON: {invalid_json}")
                except Exception as json_error:
                    logger.error(f"Failed to serialize invalid FlexMessage: {json_error}")
                return False
            
            # Convert to LINE API format using FlexContainer objects
            line_flex_container = self._convert_to_line_flex_container(flex_message)
            line_flex = LineFlexMessage(
                alt_text=flex_message.alt_text,
                contents=line_flex_container
            )
            
            # Debug log the final message structure
            logger.debug(f"Replying with FlexMessage alt_text: {flex_message.alt_text}")
            logger.debug(f"FlexMessage container type: {type(line_flex_container)}")
            
            # Reply with FlexMessage
            reply_message = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[line_flex]
            )
            self.line_bot_api.reply_message(reply_message)
            
            logger.info("成功回覆 FlexMessage")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "Invalid reply token" in error_msg:
                logger.warning(f"Reply token 已過期或無效: {reply_token}")
                return False
            else:
                logger.warning(f"FlexMessage 回覆失敗，使用文字備援: {e}")
                return False
    
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
            error_msg = str(e)
            if "Invalid reply token" in error_msg:
                logger.warning(f"Reply token 已過期或無效: {reply_token}")
                # Reply token 過期時，不再嘗試回覆，避免重複錯誤
                return
            else:
                logger.error(f"LINE回覆失敗: {e}")
    
    async def send_test_notification(self):
        """發送測試訊息（支援 FlexMessage 和文字備援）"""
        if not self.line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送測試訊息")
            return
        
        try:
            # Try FlexMessage first if enabled
            if self.use_flex_messages:
                success = await self._send_test_flex()
                if success:
                    return
                elif not self.flex_fallback_enabled:
                    logger.error("FlexMessage test failed and fallback is disabled")
                    return
            
            # Fallback to text message
            test_message = f"🧪 LINE Bot 測試成功！\n\n✅ LINE Bot 連線正常\n📡 監控系統運作中\n🔔 通知功能正常\n\n時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await self.push_to_all_friends(test_message)
            logger.info(f"成功發送測試訊息給 {len(self.line_user_ids)} 位好友")
            
        except Exception as e:
            logger.error(f"測試訊息發送失敗: {e}")
    
    async def _send_test_flex(self) -> bool:
        """發送 FlexMessage 測試訊息"""
        try:
            # Create test FlexMessage
            flex_message = self.flex_factory.create_test_message()
            
            # Validate message
            if not self.flex_factory.validate_message(flex_message):
                logger.warning("Test FlexMessage validation failed")
                return False
            
            # Convert to LINE API format using FlexContainer objects
            line_flex_container = self._convert_to_line_flex_container(flex_message)
            line_flex = LineFlexMessage(
                alt_text=flex_message.alt_text,
                contents=line_flex_container
            )
            
            # Send to all users
            for user_id in self.line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[line_flex]
                )
                self.line_bot_api.push_message(push_message)
            
            logger.info(f"成功發送 FlexMessage 測試訊息給 {len(self.line_user_ids)} 位好友")
            return True
            
        except Exception as e:
            logger.warning(f"FlexMessage 測試失敗，使用文字備援: {e}")
            return False

# LINE Bot Webhook Handler
def create_webhook_handler() -> WebhookHandler:
    """Create LINE Bot webhook handler"""
    return WebhookHandler(settings.LINE_CHANNEL_SECRET)