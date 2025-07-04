"""
LINE Flex Message Builder for Typhoon Weather Monitor
Creates visual notification messages for LINE Bot
"""

import logging
from datetime import datetime
from typing import Dict, List
from linebot.v3.messaging import FlexContainer
from config.settings import settings

logger = logging.getLogger(__name__)

class FlexMessageBuilder:
    """LINE Flex Message 建構器類別，用於創建各種視覺化通知訊息"""
    
    def __init__(self, base_url: str = None):
        """
        初始化 FlexMessageBuilder
        
        Args:
            base_url: 應用程式的基本URL，用於生成連結
        """
        self.base_url = base_url or settings.get_base_url()
    
    def create_typhoon_status_flex(self, result: Dict) -> FlexContainer:
        """
        創建颱風狀態的 Flex Message
        
        Args:
            result: 包含颱風監控結果的字典
            
        Returns:
            FlexContainer: LINE Flex Message 容器
        """
        timestamp = datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))
        status_color = "#FF4757" if result["status"] == "DANGER" else "#2ED573"
        status_icon = "🔴" if result["status"] == "DANGER" else "🟢"
        status_text = "有風險" if result["status"] == "DANGER" else "無明顯風險"
        
        # 分類警告訊息 (機場功能已禁用)
        weather_warnings = result["warnings"]  # 所有警告都視為天氣警告
        
        # 風險等級顏色
        def get_risk_color(risk_text: str) -> str:
            if "高風險" in risk_text:
                return "#FF4757"
            elif "中風險" in risk_text:
                return "#FFA726"
            else:
                return "#2ED573"
        
        # 構建警告區塊
        warning_contents = []
        
        if weather_warnings:
            warning_contents.append({
                "type": "box",
                "layout": "vertical",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "🌪️ 天氣警報",
                        "weight": "bold",
                        "color": "#F57C00",
                        "size": "sm"
                    }
                ] + [
                    {
                        "type": "text",
                        "text": f"• {warning}",
                        "size": "xs",
                        "color": "#666666",
                        "wrap": True,
                        "margin": "xs"
                    } for warning in weather_warnings[:3]  # 最多顯示3個警告
                ]
            })
        
        if not result["warnings"]:
            warning_contents.append({
                "type": "box",
                "layout": "vertical",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "✅ 目前無特殊警報",
                        "color": "#2ED573",
                        "size": "sm",
                        "weight": "bold"
                    }
                ]
            })
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🌀 颱風警訊播報",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#FFFFFF"
                    },
                    {
                        "type": "text",
                        "text": timestamp.strftime('%Y-%m-%d %H:%M'),
                        "size": "xs",
                        "color": "#FFFFFF",
                        "margin": "xs"
                    }
                ],
                "backgroundColor": status_color,
                "paddingAll": "md"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": status_icon,
                                "size": "xl",
                                "flex": 0
                            },
                            {
                                "type": "text",
                                "text": f"警告狀態: {status_text}",
                                "weight": "bold",
                                "size": "md",
                                "color": status_color,
                                "margin": "sm",
                                "flex": 1
                            }
                        ],
                        "margin": "none"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "✈️",
                                        "size": "sm",
                                        "flex": 0
                                    },
                                    {
                                        "type": "text",
                                        "text": "7/6 金門→台南航班風險",
                                        "size": "sm",
                                        "color": "#666666",
                                        "margin": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": result['travel_risk'],
                                        "size": "sm",
                                        "color": get_risk_color(result['travel_risk']),
                                        "weight": "bold",
                                        "align": "end",
                                        "flex": 0
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "🏥",
                                        "size": "sm",
                                        "flex": 0
                                    },
                                    {
                                        "type": "text",
                                        "text": "7/7 台南體檢風險",
                                        "size": "sm",
                                        "color": "#666666",
                                        "margin": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": result['checkup_risk'],
                                        "size": "sm",
                                        "color": get_risk_color(result['checkup_risk']),
                                        "weight": "bold",
                                        "align": "end",
                                        "flex": 0
                                    }
                                ]
                            }
                        ]
                    }
                ] + warning_contents + self._get_tainan_weekly_weather() + self._get_typhoon_timing_info() + self._get_typhoon_details_flex_content()
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "查看詳細儀表板",
                            "uri": self.base_url
                        },
                        "style": "primary",
                        "color": "#1976D2"
                    }
                ],
                "margin": "sm"
            }
        }
        
        return FlexContainer.from_dict(flex_content)
    
    def create_airport_status_flex(self, airport_data: Dict) -> FlexContainer:
        """
        創建機場狀態的 Flex Message (已禁用)
        
        Args:
            airport_data: 包含機場資訊的字典
            
        Returns:
            FlexContainer: LINE Flex Message 容器
        """
        logger.warning("Airport functionality is disabled")
        
        # 返回禁用通知
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "✈️ 機場功能已禁用",
                        "size": "md",
                        "color": "#666666"
                    },
                    {
                        "type": "text",
                        "text": "機場風險檢查功能因 API 限制暫時禁用",
                        "size": "sm",
                        "color": "#999999",
                        "wrap": True,
                        "margin": "sm"
                    }
                ]
            }
        }
        
        return FlexContainer.from_dict(flex_content)
    
    def create_test_notification_flex(self, message: str = "這是測試訊息") -> FlexContainer:
        """
        創建測試通知的 Flex Message
        
        Args:
            message: 測試訊息內容
            
        Returns:
            FlexContainer: LINE Flex Message 容器
        """
        timestamp = datetime.now()
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🧪 系統測試",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#FFFFFF"
                    },
                    {
                        "type": "text",
                        "text": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        "size": "xs",
                        "color": "#FFFFFF",
                        "margin": "xs"
                    }
                ],
                "backgroundColor": "#9C27B0",
                "paddingAll": "md"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": message,
                        "size": "md",
                        "color": "#333333",
                        "wrap": True
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": "✅ LINE Bot 連線正常\n📡 監控系統運作中\n🔔 通知功能正常",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "返回監控儀表板",
                            "uri": self.base_url
                        },
                        "style": "secondary"
                    }
                ],
                "margin": "sm"
            }
        }
        
        return FlexContainer.from_dict(flex_content)
    
    def create_carousel_flex(self, bubbles: List[Dict]) -> FlexContainer:
        """
        創建輪播式 Flex Message
        
        Args:
            bubbles: 包含多個 bubble 內容的列表
            
        Returns:
            FlexContainer: LINE Flex Message 容器
        """
        flex_content = {
            "type": "carousel",
            "contents": bubbles
        }
        
        return FlexContainer.from_dict(flex_content)

    def _get_typhoon_details_flex_content(self) -> List[Dict]:
        """獲取颱風詳細資料的 Flex Message 內容"""
        typhoon_contents = []
        
        # Get data from global storage
        from utils.helpers import get_global_data
        data = get_global_data()
        latest_typhoons = data['latest_typhoons']
        latest_weather = data['latest_weather']
        latest_alerts = data['latest_alerts']
        typhoon_found = False
        
        if latest_typhoons:
            try:
                records = latest_typhoons.get('records', {})
                
                # 新的颱風資料結構
                if 'tropicalCyclones' in records:
                    tropical_cyclones = records['tropicalCyclones']
                    typhoons = tropical_cyclones.get('tropicalCyclone', [])
                    
                    for typhoon in typhoons:
                        if not isinstance(typhoon, dict):
                            continue
                        
                        # 添加分隔線
                        typhoon_contents.append({
                            "type": "separator",
                            "margin": "md"
                        })
                        
                        # 颱風基本資訊
                        typhoon_name = typhoon.get('typhoonName', '')
                        cwa_typhoon_name = typhoon.get('cwaTyphoonName', '')
                        cwa_td_no = typhoon.get('cwaTdNo', '')
                        
                        name = cwa_typhoon_name or typhoon_name or f"熱帶性低氣壓 {cwa_td_no}"
                        
                        # 添加颱風詳細資料標題
                        typhoon_contents.append({
                            "type": "box",
                            "layout": "vertical",
                            "margin": "md",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"📊 {name} 詳細資料",
                                    "weight": "bold",
                                    "color": "#1976D2",
                                    "size": "sm"
                                }
                            ]
                        })
                        
                        typhoon_found = True
                        detail_items = []
                        
                        # 從最新分析資料取得詳細資訊
                        analysis_data = typhoon.get('analysisData', {})
                        fixes = analysis_data.get('fix', [])
                        
                        if fixes:
                            latest_fix = fixes[-1]  # 取最新的資料
                            
                            # 風速資訊
                            max_wind_speed = latest_fix.get('maxWindSpeed', '')
                            max_gust_speed = latest_fix.get('maxGustSpeed', '')
                            if max_wind_speed:
                                max_wind_kmh = int(max_wind_speed) * 3.6
                                detail_items.append(("💨", "最大風速", f"{max_wind_speed} m/s ({max_wind_kmh:.1f} km/h)"))
                            if max_gust_speed:
                                max_gust_kmh = int(max_gust_speed) * 3.6
                                detail_items.append(("💨", "最大陣風", f"{max_gust_speed} m/s ({max_gust_kmh:.1f} km/h)"))
                            
                            # 中心氣壓
                            pressure = latest_fix.get('pressure', '')
                            if pressure:
                                detail_items.append(("🌀", "中心氣壓", f"{pressure} hPa"))
                            
                            # 移動資訊
                            moving_speed = latest_fix.get('movingSpeed', '')
                            moving_direction = latest_fix.get('movingDirection', '')
                            if moving_speed:
                                detail_items.append(("🏃", "移動速度", f"{moving_speed} km/h"))
                            if moving_direction:
                                direction_map = {
                                    'N': '北', 'NNE': '北北東', 'NE': '東北', 'ENE': '東北東',
                                    'E': '東', 'ESE': '東南東', 'SE': '東南', 'SSE': '南南東',
                                    'S': '南', 'SSW': '南南西', 'SW': '西南', 'WSW': '西南西',
                                    'W': '西', 'WNW': '西北西', 'NW': '西北', 'NNW': '北北西'
                                }
                                direction_zh = direction_map.get(moving_direction, moving_direction)
                                detail_items.append(("➡️", "移動方向", f"{direction_zh}"))
                            
                            # 座標位置
                            coordinate = latest_fix.get('coordinate', '')
                            if coordinate:
                                try:
                                    lon, lat = coordinate.split(',')
                                    detail_items.append(("📍", "座標位置", f"{lat}°N, {lon}°E"))
                                except:
                                    detail_items.append(("📍", "座標位置", coordinate))
                            
                            # 暴風圈資訊
                            circle_of_15ms = latest_fix.get('circleOf15Ms', {})
                            if circle_of_15ms:
                                radius = circle_of_15ms.get('radius', '')
                                if radius:
                                    detail_items.append(("🌪️", "暴風圈半徑", f"{radius} km"))
                        
                        # 生成詳細資料的 Flex 內容
                        for icon, label, value in detail_items[:6]:  # 最多顯示6項避免過長
                            typhoon_contents.append({
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "xs",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": icon,
                                        "size": "xs",
                                        "flex": 0
                                    },
                                    {
                                        "type": "text",
                                        "text": label,
                                        "size": "xs",
                                        "color": "#666666",
                                        "margin": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": str(value),
                                        "size": "xs",
                                        "color": "#333333",
                                        "weight": "bold",
                                        "align": "end",
                                        "flex": 1,
                                        "wrap": True
                                    }
                                ]
                            })
                        
                        # 只顯示第一個颱風資訊
                        break
            except Exception as e:
                logger.warning(f"解析颱風詳細資料失敗: {e}")
        
        # 如果沒有颱風資料，顯示提示
        if not typhoon_found:
            typhoon_contents.extend([
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📊 氣象資料",
                            "weight": "bold",
                            "color": "#1976D2",
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": "🌀 目前無活躍颱風",
                            "size": "xs",
                            "color": "#666666",
                            "margin": "xs"
                        }
                    ]
                }
            ])
        
        # 添加天氣原始資料
        weather_data = self._get_weather_raw_data_flex()
        if weather_data:
            typhoon_contents.extend(weather_data)
        
        # 添加風險評估說明
        typhoon_contents.extend([
            {
                "type": "separator",
                "margin": "md"
            },
            {
                "type": "box",
                "layout": "vertical",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "📋 風險評估依據",
                        "weight": "bold",
                        "color": "#FF6B35",
                        "size": "sm"
                    },
                    {
                        "type": "text",
                        "text": "• 颱風風速 >80km/h = 高風險\n• 颱風風速 60-80km/h = 中風險\n• 大雨/豪雨預報 = 中-高風險\n• 強風特報 = 中風險\n• 暴風圈範圍 = 高度關注",
                        "size": "xs",
                        "color": "#666666",
                        "margin": "xs",
                        "wrap": True
                    }
                ]
            }
        ])
        
        return typhoon_contents
    
    def _get_weather_raw_data_flex(self) -> List[Dict]:
        """取得天氣原始資料的 Flex 內容"""
        weather_contents = []
        
        try:
            # Get data from global storage
            from utils.helpers import get_global_data
            data = get_global_data()
            latest_weather = data['latest_weather']
            latest_alerts = data['latest_alerts']
            
            # 添加天氣預報資料
            if latest_weather and 'records' in latest_weather:
                weather_items_found = False
                
                for location in latest_weather.get('records', {}).get('location', []):
                    location_name = location.get('locationName', '')
                    if location_name in settings.MONITOR_LOCATIONS:
                        if not weather_items_found:
                            weather_contents.extend([
                                {
                                    "type": "separator",
                                    "margin": "md"
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "margin": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"🌤️ {location_name} 天氣資料",
                                            "weight": "bold",
                                            "color": "#2E8B57",
                                            "size": "sm"
                                        }
                                    ]
                                }
                            ])
                            weather_items_found = True
                        
                        elements = location.get('weatherElement', [])
                        weather_items = []
                        
                        for element in elements:
                            element_name = element.get('elementName', '')
                            times = element.get('time', [])
                            
                            if times:
                                latest_time = times[0]
                                value = latest_time.get('parameter', {}).get('parameterName', '')
                                
                                if element_name == 'Wx' and value:  # 天氣現象
                                    weather_items.append(("🌤️", "天氣", f"{value}"))
                                elif element_name == 'PoP' and value:  # 降雨機率
                                    weather_items.append(("🌧️", "降雨機率", f"{value}%"))
                                elif element_name == 'MinT' and value:  # 最低溫度
                                    weather_items.append(("🌡️", "最低溫", f"{value}°C"))
                                elif element_name == 'MaxT' and value:  # 最高溫度
                                    weather_items.append(("🌡️", "最高溫", f"{value}°C"))
                        
                        # 生成天氣資料的 Flex 內容
                        for icon, label, value in weather_items[:4]:  # 最多顯示4項
                            weather_contents.append({
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "xs",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": icon,
                                        "size": "xs",
                                        "flex": 0
                                    },
                                    {
                                        "type": "text",
                                        "text": label,
                                        "size": "xs",
                                        "color": "#666666",
                                        "margin": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": str(value),
                                        "size": "xs",
                                        "color": "#333333",
                                        "weight": "bold",
                                        "align": "end",
                                        "flex": 1,
                                        "wrap": True
                                    }
                                ]
                            })
                        
                        # 只顯示第一個地區的資料
                        break
            
            # 添加特報資料
            if latest_alerts and 'records' in latest_alerts:
                alert_items_found = False
                
                for record in latest_alerts.get('records', {}).get('location', []):
                    location_name = record.get('locationName', '')
                    if location_name in settings.MONITOR_LOCATIONS:
                        hazards = record.get('hazardConditions', {}).get('hazards', [])
                        if hazards and not alert_items_found:
                            weather_contents.extend([
                                {
                                    "type": "separator",
                                    "margin": "md"
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "margin": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"⚠️ {location_name} 特報",
                                            "weight": "bold",
                                            "color": "#FF4757",
                                            "size": "sm"
                                        }
                                    ]
                                }
                            ])
                            alert_items_found = True
                            
                            for hazard in hazards[:2]:  # 最多顯示2個特報
                                phenomena = hazard.get('phenomena', '')
                                significance = hazard.get('significance', '')
                                if phenomena:
                                    weather_contents.append({
                                        "type": "text",
                                        "text": f"📢 {phenomena} {significance}",
                                        "size": "xs",
                                        "color": "#FF4757",
                                        "margin": "xs",
                                        "wrap": True
                                    })
                            break
                            
        except Exception as e:
            logger.warning(f"解析天氣原始資料失敗: {e}")
        
        return weather_contents
    
    def _get_tainan_weekly_weather(self) -> List[Dict]:
        """取得台南市一週天氣預報，表格型橫顯示"""
        forecast_contents = []
        
        try:
            # Get data from global storage
            from utils.helpers import get_global_data
            from datetime import datetime, timedelta
            import asyncio
            from services.weather_service import WeatherService
            
            # 日期範圍：7/6-7/10
            target_dates = [
                "2025-07-06", "2025-07-07", "2025-07-08", 
                "2025-07-09", "2025-07-10"
            ]
            
            forecast_contents.extend([
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🌧️ 台南市天氣預報 (7/6-7/10)",
                            "weight": "bold",
                            "color": "#1976D2",
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": "重點關注：風雨狀況",
                            "size": "xs",
                            "color": "#666666",
                            "margin": "xs"
                        }
                    ]
                }
            ])
            
            # 取得全域天氣資料
            data = get_global_data()
            tainan_weather = data.get('tainan_weekly_weather', {})
            
            if tainan_weather and 'records' in tainan_weather:
                tainan_data = None
                
                # 找到台南的天氣資料
                for location in tainan_weather.get('records', {}).get('location', []):
                    location_name = location.get('locationName', '')
                    if '台南' in location_name or '臺南' in location_name:
                        tainan_data = location
                        break
                
                if tainan_data:
                    # 處理天氣元素
                    elements = tainan_data.get('weatherElement', [])
                    
                    # 按日期組織資料
                    daily_forecast = {}
                    
                    for element in elements:
                        element_name = element.get('elementName', '')
                        times = element.get('time', [])
                        
                        # 只關注天氣現象和降雨機率，忽略溫度
                        if element_name in ['天氣現象', '降雨機率']:
                            for time_data in times:
                                start_time = time_data.get('startTime', '')
                                if start_time:
                                    date_str = start_time[:10]  # 取YYYY-MM-DD
                                    if date_str in target_dates:
                                        if date_str not in daily_forecast:
                                            daily_forecast[date_str] = {}
                                        
                                        value = time_data.get('parameter', {}).get('parameterName', '')
                                        daily_forecast[date_str][element_name] = value
                    
                    # 生成表格式顯示
                    if daily_forecast:
                        # 排序日期
                        sorted_dates = sorted([d for d in target_dates if d in daily_forecast])
                        
                        # 表頭 - 日期行
                        date_headers = []
                        for date_str in sorted_dates:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            date_display = f"{date_obj.month}/{date_obj.day}"
                            date_headers.append({
                                "type": "text",
                                "text": date_display,
                                "size": "xs",
                                "color": "#1976D2",
                                "weight": "bold",
                                "flex": 1,
                                "align": "center"
                            })
                        
                        # 天氣現象行
                        weather_row = []
                        for date_str in sorted_dates:
                            daily_data = daily_forecast[date_str]
                            weather_desc = daily_data.get('天氣現象', '無資料')
                            # 只取前4個字節省空間
                            short_desc = weather_desc[:4] if len(weather_desc) > 4 else weather_desc
                            weather_row.append({
                                "type": "text",
                                "text": short_desc,
                                "size": "xs",
                                "color": self._get_weather_color(weather_desc),
                                "flex": 1,
                                "align": "center",
                                "wrap": True
                            })
                        
                        # 降雨機率行
                        rain_row = []
                        for date_str in sorted_dates:
                            daily_data = daily_forecast[date_str]
                            rain_prob = daily_data.get('降雨機率', '0')
                            rain_row.append({
                                "type": "text",
                                "text": f"{rain_prob}%",
                                "size": "xs",
                                "color": "#666666",
                                "flex": 1,
                                "align": "center"
                            })
                        
                        # 添加表格內容
                        forecast_contents.extend([
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "sm",
                                "contents": date_headers
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "xs",
                                "contents": weather_row
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "margin": "xs",
                                "contents": rain_row
                            }
                        ])
                
                # 如果沒有找到台南資料，顯示提示
                if not tainan_data:
                    forecast_contents.append({
                        "type": "text",
                        "text": "⚠️ 無法取得台南天氣預報資料",
                        "size": "xs",
                        "color": "#FF4757",
                        "margin": "sm"
                    })
            else:
                forecast_contents.append({
                    "type": "text",
                    "text": "⚠️ 天氣預報資料暫時無法取得",
                    "size": "xs",
                    "color": "#FF4757",
                    "margin": "sm"
                })
                
        except Exception as e:
            logger.warning(f"取得台南天氣預報失敗: {e}")
            forecast_contents.append({
                "type": "text",
                "text": "⚠️ 天氣預報載入失敗",
                "size": "xs",
                "color": "#FF4757",
                "margin": "sm"
            })
        
        return forecast_contents
    
    def _get_typhoon_timing_info(self) -> List[Dict]:
        """取得颱風影響金門、台南的時間資訊"""
        timing_contents = []
        
        try:
            # Get data from global storage
            from utils.helpers import get_global_data
            data = get_global_data()
            latest_typhoons = data['latest_typhoons']
            
            if not latest_typhoons:
                return timing_contents
            
            # 找出是否有時間預估資訊
            has_timing_info = False
            timing_data = {}
            
            records = latest_typhoons.get('records', {})
            if 'tropicalCyclones' in records:
                typhoons = records['tropicalCyclones'].get('tropicalCyclone', [])
                
                for typhoon in typhoons:
                    if not isinstance(typhoon, dict):
                        continue
                    
                    # 取得颱風名稱
                    typhoon_name = typhoon.get('typhoonName', '')
                    cwa_typhoon_name = typhoon.get('cwaTyphoonName', '')
                    cwa_td_no = typhoon.get('cwaTdNo', '')
                    
                    if cwa_typhoon_name:
                        name = cwa_typhoon_name
                    elif typhoon_name:
                        name = typhoon_name  
                    elif cwa_td_no:
                        name = f"熱帶性低氣壓{cwa_td_no}"
                    else:
                        name = "未知熱帶氣旋"
                    
                    # 計算時間資訊
                    from services.typhoon_service import TyphoonService
                    service = TyphoonService()
                    regional_timing = service._calculate_regional_timing(typhoon, name)
                    
                    if regional_timing:
                        has_timing_info = True
                        # 解析時間資訊
                        for timing in regional_timing:
                            if '金門' in timing:
                                timing_data['kinmen'] = timing
                            elif '台南' in timing:
                                timing_data['tainan'] = timing
                    
                    break  # 只處理第一個颱風
            
            if has_timing_info:
                timing_contents.extend([
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": "⏰ 颱風影響時間預估",
                                "weight": "bold",
                                "color": "#FF6B35",
                                "size": "sm"
                            }
                        ]
                    }
                ])
                
                # 添加金門時間資訊
                if 'kinmen' in timing_data:
                    timing_line = timing_data['kinmen'].replace('📊 ', '').replace('影響', '')
                    timing_contents.append({
                        "type": "text",
                        "text": f"🏝️ 金門: {timing_line.split('時間預估: ')[-1] if '時間預估: ' in timing_line else timing_line}",
                        "size": "xs",
                        "color": "#FF4757",
                        "margin": "xs",
                        "wrap": True
                    })
                
                # 添加台南時間資訊
                if 'tainan' in timing_data:
                    timing_line = timing_data['tainan'].replace('📊 ', '').replace('影響', '')
                    timing_contents.append({
                        "type": "text",
                        "text": f"🏙️ 台南: {timing_line.split('時間預估: ')[-1] if '時間預估: ' in timing_line else timing_line}",
                        "size": "xs",
                        "color": "#FF4757",
                        "margin": "xs",
                        "wrap": True
                    })
                
                # 添加說明
                timing_contents.append({
                    "type": "text",
                    "text": "* 基於400km影響半徑計算",
                    "size": "xs",
                    "color": "#999999",
                    "margin": "sm",
                    "style": "italic"
                })
                
        except Exception as e:
            logger.warning(f"取得颱風時間資訊失敗: {e}")
        
        return timing_contents