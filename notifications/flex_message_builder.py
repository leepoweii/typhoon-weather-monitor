"""
LINE Flex Message Builder for Typhoon Weather Monitor
Modular and reusable Flex Message components for typhoon monitoring system
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from models.flex_message_models import (
    FlexMessage, FlexBubble, FlexBox, FlexText, FlexButton, FlexSeparator, 
    FlexSpacer, FlexLayout, FlexSize, FlexWeight, FlexAlign, FlexSpacing, 
    FlexColor, RiskLevel, TyphoonData, WeatherData
)
from config.settings import settings

logger = logging.getLogger(__name__)


class FlexMessageBuilder:
    """
    Modular Flex Message Builder for typhoon monitoring system
    Provides reusable components and templates for rich LINE notifications
    """
    
    def __init__(self):
        """Initialize the FlexMessageBuilder"""
        self.risk_colors = {
            RiskLevel.LOW: FlexColor.SUCCESS.value,
            RiskLevel.MEDIUM: FlexColor.WARNING.value,
            RiskLevel.HIGH: FlexColor.DANGER.value,
            RiskLevel.EXTREME: FlexColor.DANGER.value
        }
        
        self.weather_icons = {
            "晴": "☀️",
            "多雲": "⛅",
            "陰": "☁️",
            "雨": "🌧️",
            "雷雨": "⛈️",
            "颱風": "🌀",
            "強風": "💨"
        }
        
        logger.info("FlexMessageBuilder initialized successfully")
    
    def create_typhoon_status_message(self, result: Dict, typhoon_data: Optional[TyphoonData] = None, 
                                    weather_data: Optional[List[WeatherData]] = None) -> FlexMessage:
        """
        Create a comprehensive typhoon status Flex Message
        
        Args:
            result: Risk assessment result dictionary
            typhoon_data: Typhoon information data
            weather_data: List of weather data for monitored locations
            
        Returns:
            FlexMessage object ready for LINE API
        """
        try:
            # Determine risk level and colors
            is_danger = result.get("status") == "DANGER"
            status_color = FlexColor.DANGER.value if is_danger else FlexColor.SUCCESS.value
            status_text = "有風險" if is_danger else "無明顯風險"
            status_icon = "🔴" if is_danger else "🟢"
            
            # Create header
            header = self._create_header(result["timestamp"], status_icon, status_color)
            
            # Create body with risk assessment
            body = self._create_body(result, typhoon_data, weather_data)
            
            # Create footer with action buttons
            footer = self._create_footer()
            
            # Create bubble
            bubble = FlexBubble(
                header=header,
                body=body,
                footer=footer
            )
            
            # Create final message
            alt_text = f"颱風警報 - {status_text}"
            message = FlexMessage(alt_text=alt_text, contents=bubble)
            
            logger.info(f"Created typhoon status Flex Message: {status_text}")
            return message
            
        except Exception as e:
            logger.error(f"Failed to create typhoon status message: {e}")
            raise
    
    def _create_header(self, timestamp: str, status_icon: str, status_color: str) -> FlexBox:
        """Create message header with timestamp and status"""
        try:
            # Parse timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
            
            # Create header content
            header_content = [
                FlexText(
                    text=f"{status_icon} 颱風警報",
                    size=FlexSize.LG,
                    weight=FlexWeight.BOLD,
                    color=status_color
                ),
                FlexText(
                    text=formatted_time,
                    size=FlexSize.SM,
                    color=FlexColor.DARK.value
                )
            ]
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=header_content,
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD
            )
            
        except Exception as e:
            logger.error(f"Failed to create header: {e}")
            raise
    
    def _create_body(self, result: Dict, typhoon_data: Optional[TyphoonData], 
                    weather_data: Optional[List[WeatherData]]) -> FlexBox:
        """Create message body with risk assessment and details"""
        try:
            body_contents = []
            
            # Risk assessment section
            risk_section = self._create_risk_assessment_section(result)
            body_contents.append(risk_section)
            
            # Add separator
            body_contents.append(FlexSeparator(margin=FlexSpacing.MD))
            
            # Typhoon details section
            if typhoon_data:
                typhoon_section = self._create_typhoon_section(typhoon_data)
                body_contents.append(typhoon_section)
                body_contents.append(FlexSeparator(margin=FlexSpacing.MD))
            
            # Weather details section
            if weather_data:
                weather_section = self._create_weather_section(weather_data)
                body_contents.append(weather_section)
                body_contents.append(FlexSeparator(margin=FlexSpacing.MD))
            
            # Warnings section
            if result.get("warnings"):
                warnings_section = self._create_warnings_section(result["warnings"])
                body_contents.append(warnings_section)
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=body_contents,
                spacing=FlexSpacing.MD,
                padding_all=FlexSpacing.MD
            )
            
        except Exception as e:
            logger.error(f"Failed to create body: {e}")
            raise
    
    def _create_risk_assessment_section(self, result: Dict) -> FlexBox:
        """Create risk assessment section"""
        try:
            # Travel risk
            travel_risk_color = self._get_risk_color(result.get("travel_risk", ""))
            travel_row = FlexBox(
                layout=FlexLayout.HORIZONTAL,
                contents=[
                    FlexText(text="✈️ 航班風險:", flex=1, size=FlexSize.SM),
                    FlexText(
                        text=result.get("travel_risk", "未知"),
                        flex=2,
                        size=FlexSize.SM,
                        weight=FlexWeight.BOLD,
                        color=travel_risk_color,
                        align=FlexAlign.END
                    )
                ]
            )
            
            # Checkup risk
            checkup_risk_text = result.get("checkup_risk", "未知")
            if "\n詳細分析:" in checkup_risk_text:
                checkup_risk_text = checkup_risk_text.split("\n詳細分析:")[0]
            
            checkup_risk_color = self._get_risk_color(checkup_risk_text)
            checkup_row = FlexBox(
                layout=FlexLayout.HORIZONTAL,
                contents=[
                    FlexText(text="🏥 體檢風險:", flex=1, size=FlexSize.SM),
                    FlexText(
                        text=checkup_risk_text,
                        flex=2,
                        size=FlexSize.SM,
                        weight=FlexWeight.BOLD,
                        color=checkup_risk_color,
                        align=FlexAlign.END
                    )
                ]
            )
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text="📊 風險評估",
                        size=FlexSize.MD,
                        weight=FlexWeight.BOLD,
                        color=FlexColor.DARK.value
                    ),
                    FlexSpacer(size=FlexSize.SM),
                    travel_row,
                    FlexSpacer(size=FlexSize.XS),
                    checkup_row
                ],
                spacing=FlexSpacing.SM
            )
            
        except Exception as e:
            logger.error(f"Failed to create risk assessment section: {e}")
            raise
    
    def _create_typhoon_section(self, typhoon_data: TyphoonData) -> FlexBox:
        """Create typhoon information section"""
        try:
            contents = [
                FlexText(
                    text="🌀 颱風資訊",
                    size=FlexSize.MD,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.DARK.value
                ),
                FlexSpacer(size=FlexSize.SM)
            ]
            
            # Typhoon name
            if typhoon_data.name:
                name_row = FlexBox(
                    layout=FlexLayout.HORIZONTAL,
                    contents=[
                        FlexText(text="名稱:", flex=1, size=FlexSize.SM),
                        FlexText(
                            text=typhoon_data.name,
                            flex=2,
                            size=FlexSize.SM,
                            weight=FlexWeight.BOLD,
                            align=FlexAlign.END
                        )
                    ]
                )
                contents.append(name_row)
            
            # Wind speed
            if typhoon_data.wind_speed:
                wind_row = FlexBox(
                    layout=FlexLayout.HORIZONTAL,
                    contents=[
                        FlexText(text="💨 風速:", flex=1, size=FlexSize.SM),
                        FlexText(
                            text=f"{typhoon_data.wind_speed} m/s",
                            flex=2,
                            size=FlexSize.SM,
                            align=FlexAlign.END
                        )
                    ]
                )
                contents.append(wind_row)
            
            # Pressure
            if typhoon_data.pressure:
                pressure_row = FlexBox(
                    layout=FlexLayout.HORIZONTAL,
                    contents=[
                        FlexText(text="📊 氣壓:", flex=1, size=FlexSize.SM),
                        FlexText(
                            text=f"{typhoon_data.pressure} hPa",
                            flex=2,
                            size=FlexSize.SM,
                            align=FlexAlign.END
                        )
                    ]
                )
                contents.append(pressure_row)
            
            # Location
            if typhoon_data.location:
                location_row = FlexBox(
                    layout=FlexLayout.HORIZONTAL,
                    contents=[
                        FlexText(text="📍 位置:", flex=1, size=FlexSize.SM),
                        FlexText(
                            text=typhoon_data.location,
                            flex=2,
                            size=FlexSize.SM,
                            align=FlexAlign.END
                        )
                    ]
                )
                contents.append(location_row)
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=contents,
                spacing=FlexSpacing.SM
            )
            
        except Exception as e:
            logger.error(f"Failed to create typhoon section: {e}")
            raise
    
    def _create_weather_section(self, weather_data: List[WeatherData]) -> FlexBox:
        """Create weather information section"""
        try:
            contents = [
                FlexText(
                    text="🌤️ 天氣資訊",
                    size=FlexSize.MD,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.DARK.value
                ),
                FlexSpacer(size=FlexSize.SM)
            ]
            
            for weather in weather_data:
                # Location header
                location_text = FlexText(
                    text=f"📍 {weather.location}",
                    size=FlexSize.SM,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.INFO.value
                )
                contents.append(location_text)
                
                # Weather details
                if weather.weather_description:
                    desc_row = FlexBox(
                        layout=FlexLayout.HORIZONTAL,
                        contents=[
                            FlexText(text="天氣:", flex=1, size=FlexSize.XS),
                            FlexText(
                                text=weather.weather_description,
                                flex=2,
                                size=FlexSize.XS,
                                align=FlexAlign.END
                            )
                        ]
                    )
                    contents.append(desc_row)
                
                if weather.temperature_min and weather.temperature_max:
                    temp_row = FlexBox(
                        layout=FlexLayout.HORIZONTAL,
                        contents=[
                            FlexText(text="溫度:", flex=1, size=FlexSize.XS),
                            FlexText(
                                text=f"{weather.temperature_min}°C - {weather.temperature_max}°C",
                                flex=2,
                                size=FlexSize.XS,
                                align=FlexAlign.END
                            )
                        ]
                    )
                    contents.append(temp_row)
                
                if weather.rain_probability:
                    rain_row = FlexBox(
                        layout=FlexLayout.HORIZONTAL,
                        contents=[
                            FlexText(text="降雨機率:", flex=1, size=FlexSize.XS),
                            FlexText(
                                text=f"{weather.rain_probability}%",
                                flex=2,
                                size=FlexSize.XS,
                                align=FlexAlign.END
                            )
                        ]
                    )
                    contents.append(rain_row)
                
                contents.append(FlexSpacer(size=FlexSize.SM))
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=contents,
                spacing=FlexSpacing.XS
            )
            
        except Exception as e:
            logger.error(f"Failed to create weather section: {e}")
            raise
    
    def _create_warnings_section(self, warnings: List[str]) -> FlexBox:
        """Create warnings section"""
        try:
            contents = [
                FlexText(
                    text="⚠️ 警告訊息",
                    size=FlexSize.MD,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.DANGER.value
                ),
                FlexSpacer(size=FlexSize.SM)
            ]
            
            for warning in warnings:
                warning_text = FlexText(
                    text=f"• {warning}",
                    size=FlexSize.SM,
                    color=FlexColor.DANGER.value,
                    wrap=True
                )
                contents.append(warning_text)
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=contents,
                spacing=FlexSpacing.SM
            )
            
        except Exception as e:
            logger.error(f"Failed to create warnings section: {e}")
            raise
    
    def _create_footer(self) -> FlexBox:
        """Create message footer with action buttons"""
        try:
            refresh_button = FlexButton(
                action={
                    "type": "message",
                    "label": "🔄 更新狀態",
                    "text": "颱風現況"  # Ensure text is explicitly set
                },
                style="primary",
                color=FlexColor.PRIMARY.value
            )
            
            detail_button = FlexButton(
                action={
                    "type": "uri",
                    "label": "📊 詳細資料",
                    "uri": f"https://liff.line.me/{settings.LINE_CHANNEL_ID}"  # Ensure uri is explicitly set
                },
                style="secondary"
            )
            
            return FlexBox(
                layout=FlexLayout.HORIZONTAL,
                contents=[refresh_button, detail_button],
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.SM
            )
            
        except Exception as e:
            logger.error(f"Failed to create footer: {e}")
            raise
    
    def _get_risk_color(self, risk_text: str) -> str:
        """Get color based on risk level"""
        if "高風險" in risk_text or "極高風險" in risk_text:
            return FlexColor.DANGER.value
        elif "中風險" in risk_text:
            return FlexColor.WARNING.value
        elif "低風險" in risk_text:
            return FlexColor.SUCCESS.value
        else:
            return FlexColor.DARK.value
    
    def create_test_message(self) -> FlexMessage:
        """Create a test Flex Message"""
        try:
            body = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text="🧪 LINE Bot 測試",
                        size=FlexSize.LG,
                        weight=FlexWeight.BOLD,
                        color=FlexColor.PRIMARY.value
                    ),
                    FlexSeparator(margin=FlexSpacing.MD),
                    FlexText(
                        text="✅ FlexMessage 功能正常",
                        size=FlexSize.SM,
                        color=FlexColor.SUCCESS.value
                    ),
                    FlexText(
                        text="📡 監控系統運作中",
                        size=FlexSize.SM,
                        color=FlexColor.SUCCESS.value
                    ),
                    FlexText(
                        text="🔔 通知功能正常",
                        size=FlexSize.SM,
                        color=FlexColor.SUCCESS.value
                    ),
                    FlexSeparator(margin=FlexSpacing.MD),
                    FlexText(
                        text=f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        size=FlexSize.XS,
                        color=FlexColor.DARK.value
                    )
                ],
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD
            )
            
            bubble = FlexBubble(body=body)
            return FlexMessage(alt_text="LINE Bot 測試成功", contents=bubble)
            
        except Exception as e:
            logger.error(f"Failed to create test message: {e}")
            raise
    
    def to_json(self, flex_message: FlexMessage) -> str:
        """Convert FlexMessage to JSON string"""
        try:
            message_dict = flex_message.to_dict()
            logger.debug(f"Final FlexMessage dict before JSON serialization: {message_dict}")
            return json.dumps(message_dict, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to convert FlexMessage to JSON: {e}")
            raise
    
    def validate_message(self, flex_message: FlexMessage) -> bool:
        """Validate FlexMessage structure"""
        try:
            # Convert to dict to check structure
            message_dict = flex_message.to_dict()
            
            # Basic validation
            if not isinstance(message_dict, dict):
                logger.error("FlexMessage is not a dictionary")
                return False
            
            if message_dict.get("type") != "flex":
                logger.error(f"FlexMessage type is not 'flex': {message_dict.get('type')}")
                return False
            
            if not message_dict.get("altText"):
                logger.error("FlexMessage altText is missing")
                return False
            
            contents = message_dict.get("contents")
            if not contents:
                logger.error("FlexMessage contents is missing")
                return False
            
            # Validate bubble structure
            if contents.get("type") == "bubble":
                bubble = contents
                has_blocks = False
                
                # Check if bubble has at least one block
                if bubble.get("header"):
                    has_blocks = True
                    logger.debug("Bubble has header block")
                
                if bubble.get("body"):
                    has_blocks = True
                    logger.debug("Bubble has body block")
                
                if bubble.get("footer"):
                    has_blocks = True
                    logger.debug("Bubble has footer block")
                
                if not has_blocks:
                    logger.error("Bubble has no blocks (header, body, or footer)")
                    return False
                
                # Validate body contents if present
                body = bubble.get("body")
                if body and body.get("type") == "box":
                    contents_list = body.get("contents", [])
                    if not contents_list:
                        logger.error("Body box has empty contents")
                        return False
            
            # Log successful validation with structure info
            logger.info(f"FlexMessage validation passed - Type: {contents.get('type')}")
            logger.debug(f"Full message structure: {json.dumps(message_dict, ensure_ascii=False, indent=2)}")
            return True
            
        except Exception as e:
            logger.error(f"FlexMessage validation failed: {e}")
            logger.debug(f"Failed message: {flex_message}")
            return False


class StatusCard:
    """Modular status card component for risk levels"""
    
    def __init__(self, builder: FlexMessageBuilder):
        self.builder = builder
    
    def create_risk_card(self, title: str, risk_level: str, icon: str, 
                        additional_info: Optional[str] = None) -> FlexBox:
        """Create a risk assessment card"""
        try:
            risk_color = self.builder._get_risk_color(risk_level)
            
            contents = [
                FlexText(
                    text=f"{icon} {title}",
                    size=FlexSize.MD,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.DARK.value
                ),
                FlexText(
                    text=risk_level,
                    size=FlexSize.LG,
                    weight=FlexWeight.BOLD,
                    color=risk_color
                )
            ]
            
            if additional_info:
                contents.append(FlexText(
                    text=additional_info,
                    size=FlexSize.SM,
                    color=FlexColor.DARK.value,
                    wrap=True
                ))
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=contents,
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD,
                background_color=FlexColor.LIGHT.value,
                corner_radius="8px"
            )
            
        except Exception as e:
            logger.error(f"Failed to create risk card: {e}")
            raise


class TyphoonInfoCard:
    """Modular typhoon information card component"""
    
    def __init__(self, builder: FlexMessageBuilder):
        self.builder = builder
    
    def create_typhoon_card(self, typhoon_data: TyphoonData) -> FlexBox:
        """Create detailed typhoon information card"""
        try:
            contents = [
                FlexText(
                    text="🌀 颱風詳細資訊",
                    size=FlexSize.MD,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.DANGER.value
                ),
                FlexSeparator(margin=FlexSpacing.SM)
            ]
            
            # Add typhoon details
            if typhoon_data.name:
                contents.append(self._create_info_row("名稱", typhoon_data.name))
            
            if typhoon_data.wind_speed:
                wind_kmh = float(typhoon_data.wind_speed) * 3.6
                contents.append(self._create_info_row("風速", f"{typhoon_data.wind_speed} m/s ({wind_kmh:.1f} km/h)"))
            
            if typhoon_data.max_gust:
                gust_kmh = float(typhoon_data.max_gust) * 3.6
                contents.append(self._create_info_row("最大陣風", f"{typhoon_data.max_gust} m/s ({gust_kmh:.1f} km/h)"))
            
            if typhoon_data.pressure:
                contents.append(self._create_info_row("中心氣壓", f"{typhoon_data.pressure} hPa"))
            
            if typhoon_data.location:
                contents.append(self._create_info_row("位置", typhoon_data.location))
            
            if typhoon_data.direction:
                contents.append(self._create_info_row("移動方向", typhoon_data.direction))
            
            if typhoon_data.speed:
                contents.append(self._create_info_row("移動速度", f"{typhoon_data.speed} km/h"))
            
            if typhoon_data.radius:
                contents.append(self._create_info_row("暴風圈半徑", f"{typhoon_data.radius} km"))
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=contents,
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD,
                background_color=FlexColor.LIGHT.value,
                corner_radius="8px"
            )
            
        except Exception as e:
            logger.error(f"Failed to create typhoon card: {e}")
            raise
    
    def _create_info_row(self, label: str, value: str) -> FlexBox:
        """Create an information row"""
        return FlexBox(
            layout=FlexLayout.HORIZONTAL,
            contents=[
                FlexText(
                    text=f"{label}:",
                    flex=1,
                    size=FlexSize.SM,
                    color=FlexColor.DARK.value
                ),
                FlexText(
                    text=value,
                    flex=2,
                    size=FlexSize.SM,
                    weight=FlexWeight.BOLD,
                    align=FlexAlign.END
                )
            ]
        )


class WeatherCard:
    """Modular weather information card component"""
    
    def __init__(self, builder: FlexMessageBuilder):
        self.builder = builder
    
    def create_weather_card(self, weather_data: WeatherData) -> FlexBox:
        """Create weather information card for a location"""
        try:
            contents = [
                FlexText(
                    text=f"🌤️ {weather_data.location}",
                    size=FlexSize.MD,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.INFO.value
                ),
                FlexSeparator(margin=FlexSpacing.SM)
            ]
            
            if weather_data.weather_description:
                weather_icon = self._get_weather_icon(weather_data.weather_description)
                contents.append(self._create_info_row(
                    "天氣", 
                    f"{weather_icon} {weather_data.weather_description}"
                ))
            
            if weather_data.temperature_min and weather_data.temperature_max:
                contents.append(self._create_info_row(
                    "溫度", 
                    f"{weather_data.temperature_min}°C - {weather_data.temperature_max}°C"
                ))
            
            if weather_data.rain_probability:
                contents.append(self._create_info_row(
                    "降雨機率", 
                    f"{weather_data.rain_probability}%"
                ))
            
            if weather_data.comfort_level:
                contents.append(self._create_info_row(
                    "舒適度", 
                    weather_data.comfort_level
                ))
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=contents,
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD,
                background_color=FlexColor.LIGHT.value,
                corner_radius="8px"
            )
            
        except Exception as e:
            logger.error(f"Failed to create weather card: {e}")
            raise
    
    def _create_info_row(self, label: str, value: str) -> FlexBox:
        """Create an information row"""
        return FlexBox(
            layout=FlexLayout.HORIZONTAL,
            contents=[
                FlexText(
                    text=f"{label}:",
                    flex=1,
                    size=FlexSize.SM,
                    color=FlexColor.DARK.value
                ),
                FlexText(
                    text=value,
                    flex=2,
                    size=FlexSize.SM,
                    align=FlexAlign.END
                )
            ]
        )
    
    def _get_weather_icon(self, description: str) -> str:
        """Get weather icon based on description"""
        for keyword, icon in self.builder.weather_icons.items():
            if keyword in description:
                return icon
        return "🌤️"


class AlertCard:
    """Modular alert/warning card component"""
    
    def __init__(self, builder: FlexMessageBuilder):
        self.builder = builder
    
    def create_alert_card(self, alerts: List[str], alert_type: str = "⚠️ 警告") -> FlexBox:
        """Create alert card with multiple warnings"""
        try:
            contents = [
                FlexText(
                    text=alert_type,
                    size=FlexSize.MD,
                    weight=FlexWeight.BOLD,
                    color=FlexColor.DANGER.value
                ),
                FlexSeparator(margin=FlexSpacing.SM)
            ]
            
            for alert in alerts:
                alert_text = FlexText(
                    text=f"• {alert}",
                    size=FlexSize.SM,
                    color=FlexColor.DANGER.value,
                    wrap=True
                )
                contents.append(alert_text)
            
            return FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=contents,
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD,
                background_color="#FFF5F5",
                border_color=FlexColor.DANGER.value,
                border_width="2px",
                corner_radius="8px"
            )
            
        except Exception as e:
            logger.error(f"Failed to create alert card: {e}")
            raise


class ActionButtonBar:
    """Modular action button bar component"""
    
    def __init__(self, builder: FlexMessageBuilder):
        self.builder = builder
    
    def create_action_buttons(self, buttons: List[Dict[str, Any]]) -> FlexBox:
        """Create action button bar"""
        try:
            button_components = []
            
            for button_config in buttons:
                action_dict = button_config["action"].copy() # Make a copy to avoid modifying original

                # Ensure label is present in action
                if "label" not in action_dict:
                    action_dict["label"] = button_config.get("label", "Action")

                # Ensure text is present for message actions
                if action_dict.get("type") == "message" and "text" not in action_dict:
                    action_dict["text"] = action_dict.get("label", "Message")

                # Ensure uri is present for URI actions
                if action_dict.get("type") == "uri" and "uri" not in action_dict:
                    action_dict["uri"] = "#"

                button = FlexButton(
                    action=action_dict,
                    style=button_config.get("style", "primary"),
                    color=button_config.get("color", FlexColor.PRIMARY.value)
                )
                button_components.append(button)
            
            return FlexBox(
                layout=FlexLayout.HORIZONTAL,
                contents=button_components,
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.SM
            )
            
        except Exception as e:
            logger.error(f"Failed to create action buttons: {e}")
            raise
    
    def create_default_buttons(self) -> FlexBox:
        """Create default action buttons for typhoon monitoring"""
        buttons = [
            {
                "action": {
                    "type": "message",
                    "label": "🔄 更新狀態",
                    "text": "颱風現況"
                },
                "style": "primary",
                "color": FlexColor.PRIMARY.value
            },
            {
                "action": {
                    "type": "uri",
                    "label": "📊 詳細資料",
                    "uri": f"https://liff.line.me/{settings.LINE_CHANNEL_ID}"
                },
                "style": "secondary"
            }
        ]
        return self.create_action_buttons(buttons)


class FlexMessageTemplate:
    """Base class for Flex Message templates"""
    
    def __init__(self, builder: FlexMessageBuilder):
        self.builder = builder
        self.status_card = StatusCard(builder)
        self.typhoon_card = TyphoonInfoCard(builder)
        self.weather_card = WeatherCard(builder)
        self.alert_card = AlertCard(builder)
        self.action_buttons = ActionButtonBar(builder)


class DangerTemplate(FlexMessageTemplate):
    """Template for high-risk typhoon alerts"""
    
    def create_message(self, result: Dict, typhoon_data: Optional[TyphoonData] = None, 
                      weather_data: Optional[List[WeatherData]] = None) -> FlexMessage:
        """Create danger alert message"""
        try:
            # Header with danger status
            header = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text="🚨 颱風危險警報",
                        size=FlexSize.XL,
                        weight=FlexWeight.BOLD,
                        color=FlexColor.DANGER.value
                    ),
                    FlexText(
                        text="請立即採取防護措施",
                        size=FlexSize.MD,
                        color=FlexColor.DANGER.value
                    )
                ],
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD,
                background_color="#FFE6E6"
            )
            
            # Body with risk cards
            body_contents = []
            
            # Travel risk card
            if result.get("travel_risk"):
                travel_card = self.status_card.create_risk_card(
                    "航班風險評估",
                    result["travel_risk"],
                    "✈️"
                )
                body_contents.append(travel_card)
            
            # Checkup risk card
            if result.get("checkup_risk"):
                checkup_risk = result["checkup_risk"]
                if "\n詳細分析:" in checkup_risk:
                    main_risk, details = checkup_risk.split("\n詳細分析:", 1)
                    checkup_card = self.status_card.create_risk_card(
                        "體檢風險評估",
                        main_risk,
                        "🏥",
                        details.strip()
                    )
                else:
                    checkup_card = self.status_card.create_risk_card(
                        "體檢風險評估",
                        checkup_risk,
                        "🏥"
                    )
                body_contents.append(checkup_card)
            
            # Typhoon details card
            if typhoon_data:
                typhoon_detail_card = self.typhoon_card.create_typhoon_card(typhoon_data)
                body_contents.append(typhoon_detail_card)
            
            # Weather cards
            if weather_data:
                for weather in weather_data:
                    weather_detail_card = self.weather_card.create_weather_card(weather)
                    body_contents.append(weather_detail_card)
            
            # Alert card for warnings
            if result.get("warnings"):
                alert_detail_card = self.alert_card.create_alert_card(
                    result["warnings"],
                    "🚨 緊急警告"
                )
                body_contents.append(alert_detail_card)
            
            # Ensure body has at least one component
            if not body_contents:
                # Add a default message if no content
                default_card = FlexBox(
                    layout=FlexLayout.VERTICAL,
                    contents=[
                        FlexText(
                            text="📊 風險評估",
                            size=FlexSize.MD,
                            weight=FlexWeight.BOLD,
                            color=FlexColor.DARK.value
                        ),
                        FlexText(
                            text="正在評估風險中...",
                            size=FlexSize.SM,
                            color=FlexColor.DARK.value
                        )
                    ],
                    spacing=FlexSpacing.SM,
                    padding_all=FlexSpacing.MD,
                    background_color=FlexColor.LIGHT.value,
                    corner_radius="8px"
                )
                body_contents.append(default_card)
            
            body = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=body_contents,
                spacing=FlexSpacing.MD,
                padding_all=FlexSpacing.MD
            )
            
            # Footer with action buttons
            footer = self.action_buttons.create_default_buttons()
            
            # Create bubble
            bubble = FlexBubble(
                header=header,
                body=body,
                footer=footer
            )
            
            return FlexMessage(
                alt_text="🚨 颱風危險警報 - 請立即採取防護措施",
                contents=bubble
            )
            
        except Exception as e:
            logger.error(f"Failed to create danger template message: {e}")
            raise


class SafeTemplate(FlexMessageTemplate):
    """Template for safe/low-risk status messages"""
    
    def create_message(self, result: Dict, typhoon_data: Optional[TyphoonData] = None, 
                      weather_data: Optional[List[WeatherData]] = None) -> FlexMessage:
        """Create safe status message"""
        try:
            # Header with safe status
            header = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text="✅ 颱風監控狀態",
                        size=FlexSize.XL,
                        weight=FlexWeight.BOLD,
                        color=FlexColor.SUCCESS.value
                    ),
                    FlexText(
                        text="目前無明顯風險",
                        size=FlexSize.MD,
                        color=FlexColor.SUCCESS.value
                    )
                ],
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD,
                background_color="#E6F7E6"
            )
            
            # Body with status summary
            body_contents = []
            
            # Status summary
            status_summary = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text="📊 狀態摘要",
                        size=FlexSize.MD,
                        weight=FlexWeight.BOLD,
                        color=FlexColor.DARK.value
                    ),
                    FlexSeparator(margin=FlexSpacing.SM),
                    FlexBox(
                        layout=FlexLayout.HORIZONTAL,
                        contents=[
                            FlexText(text="✈️ 航班風險:", flex=1, size=FlexSize.SM),
                            FlexText(
                                text=result.get("travel_risk") or "未知",
                                flex=1,
                                size=FlexSize.SM,
                                weight=FlexWeight.BOLD,
                                color=FlexColor.SUCCESS.value,
                                align=FlexAlign.END
                            )
                        ]
                    ),
                    FlexBox(
                        layout=FlexLayout.HORIZONTAL,
                        contents=[
                            FlexText(text="🏥 體檢風險:", flex=1, size=FlexSize.SM),
                            FlexText(
                                text=(result.get("checkup_risk") or "未知").split("\n")[0],
                                flex=1,
                                size=FlexSize.SM,
                                weight=FlexWeight.BOLD,
                                color=FlexColor.SUCCESS.value,
                                align=FlexAlign.END
                            )
                        ]
                    )
                ],
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD,
                background_color=FlexColor.LIGHT.value,
                corner_radius="8px"
            )
            body_contents.append(status_summary)
            
            # Current weather summary
            if weather_data:
                weather_summary = FlexBox(
                    layout=FlexLayout.VERTICAL,
                    contents=[
                        FlexText(
                            text="🌤️ 目前天氣",
                            size=FlexSize.MD,
                            weight=FlexWeight.BOLD,
                            color=FlexColor.DARK.value
                        ),
                        FlexSeparator(margin=FlexSpacing.SM)
                    ],
                    spacing=FlexSpacing.SM,
                    padding_all=FlexSpacing.MD,
                    background_color=FlexColor.LIGHT.value,
                    corner_radius="8px"
                )
                
                for weather in weather_data:
                    weather_summary.contents.append(
                        FlexText(
                            text=f"📍 {weather.location}: {weather.weather_description or '正常'}",
                            size=FlexSize.SM,
                            color=FlexColor.DARK.value
                        )
                    )
                
                body_contents.append(weather_summary)
            
            # Ensure body has at least one component
            if not body_contents:
                # Add a default status message if no content
                default_status = FlexBox(
                    layout=FlexLayout.VERTICAL,
                    contents=[
                        FlexText(
                            text="📊 監控狀態",
                            size=FlexSize.MD,
                            weight=FlexWeight.BOLD,
                            color=FlexColor.DARK.value
                        ),
                        FlexText(
                            text="系統正常運作中",
                            size=FlexSize.SM,
                            color=FlexColor.SUCCESS.value
                        )
                    ],
                    spacing=FlexSpacing.SM,
                    padding_all=FlexSpacing.MD,
                    background_color=FlexColor.LIGHT.value,
                    corner_radius="8px"
                )
                body_contents.append(default_status)
            
            body = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=body_contents,
                spacing=FlexSpacing.MD,
                padding_all=FlexSpacing.MD
            )
            
            # Footer with monitoring info
            footer = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text="🔄 持續監控中",
                        size=FlexSize.SM,
                        color=FlexColor.DARK.value,
                        align=FlexAlign.CENTER
                    ),
                    FlexText(
                        text="如有變化將立即通知",
                        size=FlexSize.XS,
                        color=FlexColor.DARK.value,
                        align=FlexAlign.CENTER
                    )
                ],
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.SM
            )
            
            # Create bubble
            bubble = FlexBubble(
                header=header,
                body=body,
                footer=footer
            )
            
            return FlexMessage(
                alt_text="✅ 颱風監控狀態 - 目前無明顯風險",
                contents=bubble
            )
            
        except Exception as e:
            logger.error(f"Failed to create safe template message: {e}")
            raise


class InfoTemplate(FlexMessageTemplate):
    """Template for informational messages"""
    
    def create_message(self, title: str, content: str, icon: str = "ℹ️") -> FlexMessage:
        """Create informational message"""
        try:
            body = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text=f"{icon} {title}",
                        size=FlexSize.LG,
                        weight=FlexWeight.BOLD,
                        color=FlexColor.INFO.value
                    ),
                    FlexSeparator(margin=FlexSpacing.MD),
                    FlexText(
                        text=content,
                        size=FlexSize.SM,
                        color=FlexColor.DARK.value,
                        wrap=True
                    )
                ],
                spacing=FlexSpacing.MD,
                padding_all=FlexSpacing.MD
            )
            
            bubble = FlexBubble(body=body)
            return FlexMessage(alt_text=f"{title}", contents=bubble)
            
        except Exception as e:
            logger.error(f"Failed to create info template message: {e}")
            raise


class TestTemplate(FlexMessageTemplate):
    """Template for system test messages"""
    
    def create_message(self) -> FlexMessage:
        """Create test message"""
        try:
            body = FlexBox(
                layout=FlexLayout.VERTICAL,
                contents=[
                    FlexText(
                        text="🧪 系統測試",
                        size=FlexSize.LG,
                        weight=FlexWeight.BOLD,
                        color=FlexColor.PRIMARY.value
                    ),
                    FlexSeparator(margin=FlexSpacing.MD),
                    FlexText(
                        text="✅ FlexMessage 功能正常",
                        size=FlexSize.SM,
                        color=FlexColor.SUCCESS.value
                    ),
                    FlexText(
                        text="📡 監控系統運作中",
                        size=FlexSize.SM,
                        color=FlexColor.SUCCESS.value
                    ),
                    FlexText(
                        text="🔔 通知功能正常",
                        size=FlexSize.SM,
                        color=FlexColor.SUCCESS.value
                    ),
                    FlexSeparator(margin=FlexSpacing.MD),
                    FlexText(
                        text=f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        size=FlexSize.XS,
                        color=FlexColor.DARK.value,
                        align=FlexAlign.CENTER
                    )
                ],
                spacing=FlexSpacing.SM,
                padding_all=FlexSpacing.MD
            )
            
            # Add test action buttons
            footer = self.action_buttons.create_action_buttons([
                {
                    "action": {"type": "message", "label": "✅ 測試通過", "text": "Test Passed"},
                    "style": "primary",
                    "color": FlexColor.SUCCESS.value
                },
                {
                    "action": {"type": "message", "label": "🔄 重新測試", "text": "Test Again"},
                    "style": "secondary"
                }
            ])
            
            bubble = FlexBubble(body=body, footer=footer)
            return FlexMessage(alt_text="🧪 系統測試 - FlexMessage 功能正常", contents=bubble)
            
        except Exception as e:
            logger.error(f"Failed to create test template message: {e}")
            raise


class FlexMessageFactory:
    """Factory class for creating different types of Flex Messages"""
    
    def __init__(self):
        self.builder = FlexMessageBuilder()
        self.danger_template = DangerTemplate(self.builder)
        self.safe_template = SafeTemplate(self.builder)
        self.info_template = InfoTemplate(self.builder)
        self.test_template = TestTemplate(self.builder)
    
    def create_typhoon_status_message(self, result: Dict, typhoon_data: Optional[TyphoonData] = None,
                                     weather_data: Optional[List[WeatherData]] = None) -> FlexMessage:
        """Create typhoon status message based on risk level"""
        try:
            is_danger = result.get("status") == "DANGER"
            
            if is_danger:
                return self.danger_template.create_message(result, typhoon_data, weather_data)
            else:
                return self.safe_template.create_message(result, typhoon_data, weather_data)
                
        except Exception as e:
            logger.error(f"Failed to create typhoon status message: {e}")
            raise
    
    def create_info_message(self, title: str, content: str, icon: str = "ℹ️") -> FlexMessage:
        """Create informational message"""
        return self.info_template.create_message(title, content, icon)
    
    def create_test_message(self) -> FlexMessage:
        """Create test message"""
        return self.test_template.create_message()
    
    def to_json(self, flex_message: FlexMessage) -> str:
        """Convert FlexMessage to JSON string"""
        return self.builder.to_json(flex_message)
    
    def validate_message(self, flex_message: FlexMessage) -> bool:
        """Validate FlexMessage structure"""
        return self.builder.validate_message(flex_message)