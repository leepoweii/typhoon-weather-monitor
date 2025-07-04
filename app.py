"""
颱風警訊播報系統
監控金門縣和台南市的颱風及天氣警報
"""

import asyncio
import httpx
import json
import os
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
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, 
    TextMessage, FlexMessage, FlexContainer
)
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

app = FastAPI(title="颱風警訊播報系統", description="監控金門縣和台南市的颱風警報", lifespan=lifespan)


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

class FlexMessageBuilder:
    """LINE Flex Message 建構器類別，用於創建各種視覺化通知訊息"""
    
    def __init__(self, base_url: str = None):
        """
        初始化 FlexMessageBuilder
        
        Args:
            base_url: 應用程式的基本URL，用於生成連結
        """
        self.base_url = base_url or f"http://localhost:{SERVER_PORT}"
    
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
        
        # 分類警告訊息 (暫時隱藏機場功能)
        # flight_warnings = [w for w in result["warnings"] if any(keyword in w for keyword in ['起飛', '抵達', '航班', '停飛', '延誤', '機場API'])]
        # weather_warnings = [w for w in result["warnings"] if w not in flight_warnings]
        weather_warnings = result["warnings"]  # 暫時所有警告都視為天氣警告
        
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
        
        # 暫時隱藏機場功能 - 註解掉機場警告顯示
        # if flight_warnings:
        #     warning_contents.append({
        #         "type": "box",
        #         "layout": "vertical",
        #         "margin": "md",
        #         "contents": [
        #             {
        #                 "type": "text",
        #                 "text": "✈️ 金門機場即時狀況",
        #                 "weight": "bold",
        #                 "color": "#1976D2",
        #                 "size": "sm"
        #             }
        #         ] + [
        #             {
        #                 "type": "text",
        #                 "text": f"• {warning}",
        #                 "size": "xs",
        #                 "color": "#666666",
        #                 "wrap": True,
        #                 "margin": "xs"
        #             } for warning in flight_warnings[:3]  # 最多顯示3個警告
        #         ]
        #     })
        
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
                ] + warning_contents + self._get_typhoon_details_flex_content()
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
        創建機場狀態的 Flex Message
        
        Args:
            airport_data: 包含機場資訊的字典
            
        Returns:
            FlexContainer: LINE Flex Message 容器
        """
        departure_flights = airport_data.get('departure_flights', [])
        arrival_flights = airport_data.get('arrival_flights', [])
        warnings = airport_data.get('warnings', [])
        last_updated = airport_data.get('last_updated', datetime.now().isoformat())
        
        timestamp = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
        
        # 構建航班資訊
        flight_contents = []
        
        if warnings:
            warning_color = "#FF4757"
            for warning in warnings[:3]:  # 最多顯示3個警告
                flight_contents.append({
                    "type": "text",
                    "text": f"⚠️ {warning}",
                    "size": "xs",
                    "color": warning_color,
                    "wrap": True,
                    "margin": "xs"
                })
        else:
            flight_contents.append({
                "type": "text",
                "text": "✅ 航班狀況正常",
                "size": "sm",
                "color": "#2ED573",
                "weight": "bold"
            })
        
        # 添加航班統計
        flight_contents.extend([
            {
                "type": "separator",
                "margin": "md"
            },
            {
                "type": "box",
                "layout": "horizontal",
                "margin": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "✈️ 起飛航班",
                        "size": "sm",
                        "color": "#666666",
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": f"{len(departure_flights) if isinstance(departure_flights, list) else 0} 班",
                        "size": "sm",
                        "color": "#1976D2",
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
                        "text": "🛬 抵達航班",
                        "size": "sm",
                        "color": "#666666",
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": f"{len(arrival_flights) if isinstance(arrival_flights, list) else 0} 班",
                        "size": "sm",
                        "color": "#1976D2",
                        "weight": "bold",
                        "align": "end",
                        "flex": 0
                    }
                ]
            }
        ])
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "✈️ 金門機場監控",
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
                "backgroundColor": "#1976D2",
                "paddingAll": "md"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": flight_contents
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "查看機場詳細資訊",
                            "uri": f"{self.base_url}/api/airport"
                        },
                        "style": "primary",
                        "color": "#1976D2"
                    }
                ],
                "margin": "sm"
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
        
        # 從全域變數中取得颱風資料
        global latest_typhoons, latest_weather, latest_alerts
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
                                detail_items.append(("�", "中心氣壓", f"{pressure} hPa"))
                            
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
                                    detail_items.append(("�️", "暴風圈半徑", f"{radius} km"))
                        
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
            global latest_weather, latest_alerts
            
            # 添加天氣預報資料
            if latest_weather and 'records' in latest_weather:
                weather_items_found = False
                
                for location in latest_weather.get('records', {}).get('location', []):
                    location_name = location.get('locationName', '')
                    if location_name in MONITOR_LOCATIONS:
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
                                start_time = latest_time.get('startTime', '')
                                
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
                    if location_name in MONITOR_LOCATIONS:
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

class LineNotifier:
    def __init__(self):
        self.api_client = ApiClient(configuration)
        self.line_bot_api = MessagingApi(self.api_client)
        # 初始化 FlexMessageBuilder，使用 Zeabur 或本地 URL
        self.flex_builder = FlexMessageBuilder(
            base_url=os.getenv("APP_URL", f"http://localhost:{SERVER_PORT}")
        )
    
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
            # 暫時隱藏機場功能 - 所有警告都視為天氣警告
            # flight_warnings = [w for w in result["warnings"] if any(keyword in w for keyword in ['起飛', '抵達', '航班', '停飛', '延誤', '機場API'])]
            # weather_warnings = [w for w in result["warnings"] if w not in flight_warnings]
            weather_warnings = result["warnings"]
            
            # 暫時隱藏機場狀況顯示
            # if flight_warnings:
            #     message += "✈️ 金門機場即時狀況:\n"
            #     for warning in flight_warnings:
            #         message += f"• {warning}\n"
            #     message += "\n"
            
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
        
        # 從全域變數中取得颱風資料
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
                            details += f"�️ 颱風編號: {cwa_ty_no}\n"
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
            # 從天氣預報資料中提取原始數據
            if latest_weather and 'records' in latest_weather:
                for location in latest_weather.get('records', {}).get('location', []):
                    location_name = location.get('locationName', '')
                    if location_name in MONITOR_LOCATIONS:
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
                                    weather_info += f"  �️ 最高溫: {max_temp}°C\n"
                            
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
                    if location_name in MONITOR_LOCATIONS:
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
        if not line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送推送訊息")
            return
        
        try:
            flex_container = self.flex_builder.create_typhoon_status_flex(result)
            flex_message = FlexMessage(alt_text="颱風警訊播報", contents=flex_container)
            
            for user_id in line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[flex_message]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功推送 Flex Message 給 {len(line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"LINE Flex 推送失敗，嘗試文字版本: {e}")
            # 失敗時回退到文字訊息
            text_message = self.format_typhoon_status(result)
            await self.push_to_all_friends(text_message)
    
    async def push_airport_status_flex(self, airport_data: Dict):
        """推送機場狀態 Flex Message 給所有好友"""
        if not line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送推送訊息")
            return
        
        try:
            flex_container = self.flex_builder.create_airport_status_flex(airport_data)
            flex_message = FlexMessage(alt_text="金門機場即時狀況", contents=flex_container)
            
            for user_id in line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[flex_message]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功推送機場 Flex Message 給 {len(line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"LINE 機場 Flex 推送失敗: {e}")
    
    async def push_to_all_friends(self, message: str):
        """推送文字訊息給所有好友（備用方法）"""
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
            logger.info(f"成功推送文字訊息給 {len(line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"LINE推送失敗: {e}")
    
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
        if not line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送測試訊息")
            return
        
        try:
            flex_container = self.flex_builder.create_test_notification_flex("🧪 LINE Bot Flex Message 測試成功！")
            flex_message = FlexMessage(alt_text="系統測試通知", contents=flex_container)
            
            for user_id in line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[flex_message]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功發送測試 Flex Message 給 {len(line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"測試 Flex Message 發送失敗: {e}")

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
            airport_api_status = "異常"
            return latest_airport_arrival  # 返回最後一次成功的資料
    
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
            records = typhoon_data.get('records', {})
            
            # 新的颱風資料結構
            if 'tropicalCyclones' in records:
                tropical_cyclones = records['tropicalCyclones']
                typhoons = tropical_cyclones.get('tropicalCyclone', [])
                
                for typhoon in typhoons:
                    if not isinstance(typhoon, dict):
                        continue
                    
                    # 取得颱風名稱
                    typhoon_name = typhoon.get('typhoonName', '')
                    cwa_typhoon_name = typhoon.get('cwaTyphoonName', '')
                    name = cwa_typhoon_name or typhoon_name or '未知熱帶氣旋'
                    
                    # 從最新分析資料取得風速
                    analysis_data = typhoon.get('analysisData', {})
                    fixes = analysis_data.get('fix', [])
                    
                    if fixes:
                        latest_fix = fixes[-1]  # 取最新的資料
                        max_wind_speed = int(latest_fix.get('maxWindSpeed', 0))
                        pressure = latest_fix.get('pressure', '')
                        moving_speed = latest_fix.get('movingSpeed', '')
                        moving_direction = latest_fix.get('movingDirection', '')
                        coordinate = latest_fix.get('coordinate', '')
                        fix_time = latest_fix.get('fixTime', '')
                        
                        # 檢查風速是否超過警戒值
                        # 將 m/s 轉換為 km/h (乘以 3.6)
                        max_wind_kmh = max_wind_speed * 3.6
                        
                        if max_wind_kmh > 60:  # km/h
                            if max_wind_kmh > 80:
                                warnings.append(f"🌀 {name}颱風 最大風速: {max_wind_speed} m/s ({max_wind_kmh:.1f} km/h) - 高風險")
                            else:
                                warnings.append(f"🌀 {name}颱風 最大風速: {max_wind_speed} m/s ({max_wind_kmh:.1f} km/h) - 可能影響")
                        
                        # 檢查預報路徑是否接近台灣
                        forecast_data = typhoon.get('forecastData', {})
                        forecast_fixes = forecast_data.get('fix', [])
                        
                        for forecast in forecast_fixes:
                            if not isinstance(forecast, dict):
                                continue
                            coordinate = forecast.get('coordinate', '')
                            if coordinate:
                                try:
                                    lon, lat = map(float, coordinate.split(','))
                                    # 簡單的地理區域判斷（台灣及周邊範圍）
                                    if 119 <= lon <= 122 and 22 <= lat <= 25.5:
                                        tau = forecast.get('tau', '')
                                        warnings.append(f"📍 {name}颱風預報將在 {tau} 小時後接近台灣區域")
                                        break
                                except:
                                    continue
            
            # 舊的颱風資料結構（向後兼容）
            elif 'typhoon' in records:
                typhoons = records.get('typhoon', [])
                for typhoon in typhoons:
                    if not isinstance(typhoon, dict):
                        continue
                        
                    name = typhoon.get('typhoonName', '未知颱風')
                    intensity = typhoon.get('intensity', {})
                    max_wind = intensity.get('maximumWind', {}).get('value', 0)
                    
                    if max_wind > 60:  # km/h
                        if max_wind > 80:
                            warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (高風險)")
                        else:
                            warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (可能影響)")
                            
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
        
        # 並行取得所有資料 (暫時隱藏機場功能)
        alerts_task = self.get_weather_alerts()
        typhoons_task = self.get_typhoon_paths()
        weather_task = self.get_weather_forecast()
        # departure_task = airport_monitor.get_departure_info()
        # arrival_task = airport_monitor.get_arrival_info()
        
        alerts_data, typhoons_data, weather_data = await asyncio.gather(
            alerts_task, typhoons_task, weather_task, return_exceptions=True
        )
        
        # 更新全域狀態 (暫時隱藏機場資料)
        global latest_alerts, latest_typhoons, latest_weather, last_notification_status
        # global latest_airport_departure, latest_airport_arrival
        latest_alerts = alerts_data if not isinstance(alerts_data, Exception) else {}
        latest_typhoons = typhoons_data if not isinstance(typhoons_data, Exception) else {}
        latest_weather = weather_data if not isinstance(weather_data, Exception) else {}
        # latest_airport_departure = departure_data if not isinstance(departure_data, Exception) else {}
        # latest_airport_arrival = arrival_data if not isinstance(arrival_data, Exception) else {}
        
        # 暫時隱藏機場分析
        # flight_warnings = airport_monitor.analyze_flight_status(latest_airport_departure, latest_airport_arrival)
        
        # 分析所有資料
        alert_warnings = self.analyze_alerts(latest_alerts)
        typhoon_warnings = self.analyze_typhoons(latest_typhoons)
        weather_warnings = self.analyze_weather(latest_weather)
        
        # all_warnings = alert_warnings + typhoon_warnings + weather_warnings + flight_warnings
        all_warnings = alert_warnings + typhoon_warnings + weather_warnings
        
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
            await line_notifier.push_typhoon_status_flex(result)
            logger.info("已發送LINE風險 Flex Message 通知")
        
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
        """評估7/7體檢風險（改進版）"""
        from datetime import datetime, timedelta
        import math
        
        # 台南市座標 (約略中心位置)
        tainan_lat = 23.0
        tainan_lon = 120.2
        checkup_date = datetime(2025, 7, 7)
        
        # 基本風險評估（原有邏輯）
        basic_risk = self._assess_basic_risk(warnings)
        
        # 颱風地理風險評估
        typhoon_risk = self._assess_typhoon_geographic_risk(tainan_lat, tainan_lon, checkup_date)
        
        # 綜合評估
        final_risk = self._combine_risk_assessments(basic_risk, typhoon_risk)
        
        return final_risk
    
    def _assess_basic_risk(self, warnings: List[str]) -> str:
        """基本風險評估（保留原有邏輯）"""
        if not warnings:
            return "低風險"
        
        for warning in warnings:
            if '台南' in warning or '臺南' in warning:
                if '颱風' in warning:
                    return "高風險 - 可能停班停課"
                elif '強風' in warning or '豪雨' in warning:
                    return "中風險 - 可能影響交通"
        
        return "低風險"
    
    def _assess_typhoon_geographic_risk(self, tainan_lat: float, tainan_lon: float, target_date: datetime) -> dict:
        """地理位置颱風風險評估"""
        import math
        from datetime import datetime, timedelta
        
        risk_info = {
            "level": "低風險",
            "distance": None,
            "wind_threat": False,
            "time_threat": False,
            "details": []
        }
        
        try:
            global latest_typhoons
            if not latest_typhoons or 'records' not in latest_typhoons:
                return risk_info
            
            records = latest_typhoons.get('records', {})
            if 'tropicalCyclones' not in records:
                return risk_info
            
            tropical_cyclones = records['tropicalCyclones']
            typhoons = tropical_cyclones.get('tropicalCyclone', [])
            
            for typhoon in typhoons:
                if not isinstance(typhoon, dict):
                    continue
                
                name = typhoon.get('cwaTyphoonName') or typhoon.get('typhoonName') or '未知颱風'
                
                # 分析當前位置和強度
                analysis_data = typhoon.get('analysisData', {})
                fixes = analysis_data.get('fix', [])
                
                if fixes:
                    latest_fix = fixes[-1]
                    
                    # 計算距離
                    coordinate = latest_fix.get('coordinate', '')
                    if coordinate:
                        try:
                            lon, lat = map(float, coordinate.split(','))
                            distance = self._calculate_distance(lat, lon, tainan_lat, tainan_lon)
                            risk_info["distance"] = distance
                            
                            # 風速威脅評估
                            max_wind_speed = int(latest_fix.get('maxWindSpeed', 0))
                            wind_speed_kmh = max_wind_speed * 3.6
                            
                            # 暴風圈影響評估
                            storm_circle = latest_fix.get('circleOf15Ms', {})
                            storm_radius = float(storm_circle.get('radius', 0)) if storm_circle else 0
                            
                            # 判斷風速威脅
                            if distance < storm_radius:
                                risk_info["wind_threat"] = True
                                risk_info["details"].append(f"🌪️ {name} 暴風圈影響台南（距離{distance:.0f}km < 半徑{storm_radius}km）")
                            elif distance < 200 and wind_speed_kmh > 80:
                                risk_info["wind_threat"] = True
                                risk_info["details"].append(f"💨 {name} 強風威脅台南（距離{distance:.0f}km，風速{wind_speed_kmh:.0f}km/h）")
                            
                            # 預報路徑時間威脅評估
                            forecast_data = typhoon.get('forecastData', {})
                            forecast_fixes = forecast_data.get('fix', [])
                            
                            for forecast in forecast_fixes:
                                if not isinstance(forecast, dict):
                                    continue
                                
                                tau = forecast.get('tau', '')
                                if not tau:
                                    continue
                                
                                try:
                                    hours_ahead = int(tau)
                                    forecast_time = datetime.now() + timedelta(hours=hours_ahead)
                                    
                                    # 檢查是否在體檢日期附近（前後24小時）
                                    time_diff = abs((forecast_time - target_date).total_seconds() / 3600)
                                    
                                    if time_diff <= 24:  # 24小時內
                                        forecast_coord = forecast.get('coordinate', '')
                                        if forecast_coord:
                                            f_lon, f_lat = map(float, forecast_coord.split(','))
                                            forecast_distance = self._calculate_distance(f_lat, f_lon, tainan_lat, tainan_lon)
                                            
                                            forecast_wind = int(forecast.get('maxWindSpeed', 0)) * 3.6
                                            forecast_circle = forecast.get('circleOf15Ms', {})
                                            forecast_radius = float(forecast_circle.get('radius', 0)) if forecast_circle else 0
                                            
                                            if forecast_distance < forecast_radius or (forecast_distance < 150 and forecast_wind > 60):
                                                risk_info["time_threat"] = True
                                                risk_info["details"].append(f"⏰ {name} 預計{forecast_time.strftime('%m/%d %H時')}影響台南（距離{forecast_distance:.0f}km）")
                                
                                except (ValueError, TypeError):
                                    continue
                        
                        except (ValueError, IndexError):
                            continue
            
            # 綜合判斷風險等級
            if risk_info["wind_threat"] and risk_info["time_threat"]:
                risk_info["level"] = "極高風險"
            elif risk_info["wind_threat"]:
                risk_info["level"] = "高風險"
            elif risk_info["time_threat"]:
                risk_info["level"] = "中風險"
            elif risk_info["distance"] and risk_info["distance"] < 300:
                risk_info["level"] = "低-中風險"
        
        except Exception as e:
            logger.error(f"地理風險評估失敗: {e}")
        
        return risk_info
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """計算兩點間距離（公里）"""
        import math
        
        # 地球半徑（公里）
        R = 6371.0
        
        # 轉換為弧度
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # 計算差值
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine 公式
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _combine_risk_assessments(self, basic_risk: str, typhoon_risk: dict) -> str:
        """綜合風險評估"""
        # 風險等級優先順序
        risk_levels = {
            "低風險": 0,
            "低-中風險": 1,
            "中風險": 2,
            "高風險": 3,
            "極高風險": 4
        }
        
        # 取得基本風險等級
        basic_level = 0
        if "高風險" in basic_risk:
            basic_level = 3
        elif "中風險" in basic_risk:
            basic_level = 2
        else:
            basic_level = 0
        
        # 取得颱風地理風險等級
        geo_level = risk_levels.get(typhoon_risk["level"], 0)
        
        # 取較高的風險等級
        final_level = max(basic_level, geo_level)
        
        # 組合最終風險描述
        if final_level >= 4:
            result = "極高風險 - 強烈建議延期"
        elif final_level >= 3:
            result = "高風險 - 建議考慮延期"
        elif final_level >= 2:
            result = "中風險 - 可能影響交通"
        elif final_level >= 1:
            result = "低-中風險 - 需關注發展"
        else:
            result = "低風險"
        
        # 添加地理威脅詳情
        if typhoon_risk["details"]:
            result += "\n詳細分析: " + "; ".join(typhoon_risk["details"])
        
        return result
    
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
# 暫時隱藏機場監控功能（API 尚未申請）
# airport_monitor = AirportMonitor()

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
    
    # 處理不同關鍵字
    if "颱風近況" in message_text:
        # 使用異步方式處理（在實際環境中需要正確處理）
        async def handle_typhoon_status():
            try:
                result = await monitor.check_all_conditions()
                await line_notifier.reply_typhoon_status_flex(event.reply_token, result)
            except Exception as e:
                logger.error(f"處理颱風近況失敗: {e}")
                # 回退到簡單回覆
                await line_notifier.reply_message(event.reply_token, "系統暫時無法取得資料，請稍後再試。")
        
        asyncio.create_task(handle_typhoon_status())
    
    # 暫時隱藏機場功能
    # elif "機場狀況" in message_text:
    #     async def handle_airport_status():
    #         try:
    #             departure_info = await airport_monitor.get_departure_info()
    #             arrival_info = await airport_monitor.get_arrival_info()
    #             flight_warnings = await airport_monitor.check_flight_conditions()
    #             
    #             airport_data = {
    #                 "departure_flights": departure_info,
    #                 "arrival_flights": arrival_info,
    #                 "warnings": flight_warnings,
    #                 "last_updated": datetime.now().isoformat()
    #             }
    #             
    #             await line_notifier.push_airport_status_flex(airport_data)
    #         except Exception as e:
    #             logger.error(f"處理機場狀況失敗: {e}")
    #             await line_notifier.reply_message(event.reply_token, "無法取得機場資料，請稍後再試。")
    #     
    #     asyncio.create_task(handle_airport_status())
    
    elif "測試" in message_text:
        async def handle_test():
            try:
                await line_notifier.send_test_notification_flex()
            except Exception as e:
                logger.error(f"發送測試訊息失敗: {e}")
        
        asyncio.create_task(handle_test())
    
    elif "幫助" in message_text or "help" in message_text.lower() or "指令" in message_text:
        # 只在用戶明確要求幫助時才回覆指令列表
        help_message = """🌀 颱風警訊播報系統

可用指令：
• 颱風近況 - 查看完整監控狀況
• 測試 - 發送測試訊息
• 幫助 - 顯示此指令列表

系統會在有風險時主動推送通知！"""
        
        asyncio.create_task(line_notifier.reply_message(event.reply_token, help_message))
    
    # 移除預設回覆 - 只對特定關鍵字回應
    # 不需要對每個訊息都回覆

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
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
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
            .raw-data-section {{ margin: 24px 0; }}
            .raw-data-block {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 16px 0; }}
            .raw-data-title {{ font-size: 18px; font-weight: bold; color: #495057; margin-bottom: 12px; display: flex; align-items: center; }}
            .raw-data-title span {{ margin-right: 8px; }}
            .data-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin: 12px 0; }}
            .data-item {{ background: white; border: 1px solid #e9ecef; border-radius: 6px; padding: 12px; }}
            .data-item-label {{ font-weight: bold; color: #6c757d; font-size: 14px; margin-bottom: 4px; }}
            .data-item-value {{ color: #212529; font-size: 16px; word-wrap: break-word; }}
            .typhoon-data {{ border-left: 4px solid #dc3545; }}
            .weather-data {{ border-left: 4px solid #28a745; }}
            .alert-data {{ border-left: 4px solid #ffc107; }}
            .no-data {{ color: #6c757d; font-style: italic; text-align: center; padding: 20px; }}
            .collapsible {{ cursor: pointer; background: none; border: none; width: 100%; text-align: left; font-size: 18px; font-weight: bold; color: #495057; }}
            .collapsible:hover {{ background-color: #f1f3f4; }}
            .collapsible.active {{ background-color: #e9ecef; }}
            .content {{ display: none; overflow: hidden; }}
            .content.show {{ display: block; }}
            .toggle-icon {{ float: right; transition: transform 0.3s; }}
            .toggle-icon.rotated {{ transform: rotate(90deg); }}
            .risk-explanation {{ background: #fff8e1; border: 1px solid #ffcc02; border-radius: 8px; padding: 16px; margin: 16px 0; }}
            .risk-explanation h3 {{ margin-top: 0; color: #f57c00; }}
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

            <!-- 原始氣象資料區塊 -->
            <div class="raw-data-section">
                <h2>📊 原始氣象資料</h2>
                
                <!-- 颱風資料 -->
                <div class="raw-data-block">
                    <button class="collapsible" onclick="toggleContent('typhoon-content')">
                        <span>🌀</span> 颱風詳細資料
                        <span class="toggle-icon" id="typhoon-toggle">▶</span>
                    </button>
                    <div class="content" id="typhoon-content">
                        <div id="typhoonData" class="typhoon-data">載入中...</div>
                    </div>
                </div>

                <!-- 天氣預報資料 -->
                <div class="raw-data-block">
                    <button class="collapsible" onclick="toggleContent('weather-content')">
                        <span>🌤️</span> 天氣預報資料
                        <span class="toggle-icon" id="weather-toggle">▶</span>
                    </button>
                    <div class="content" id="weather-content">
                        <div id="weatherData" class="weather-data">載入中...</div>
                    </div>
                </div>

                <!-- 特報資料 -->
                <div class="raw-data-block">
                    <button class="collapsible" onclick="toggleContent('alert-content')">
                        <span>⚠️</span> 天氣特報資料
                        <span class="toggle-icon" id="alert-toggle">▶</span>
                    </button>
                    <div class="content" id="alert-content">
                        <div id="alertData" class="alert-data">載入中...</div>
                    </div>
                </div>

                <!-- 風險評估說明 -->
                <div class="risk-explanation">
                    <h3>📋 風險評估依據</h3>
                    <ul>
                        <li><strong>颱風風速 &gt;80km/h</strong> = 高風險</li>
                        <li><strong>颱風風速 60-80km/h</strong> = 中風險</li>
                        <li><strong>大雨/豪雨預報</strong> = 中-高風險</li>
                        <li><strong>強風特報</strong> = 中風險</li>
                        <li><strong>暴風圈範圍</strong> = 高度關注</li>
                    </ul>
                </div>
            </div>

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
            function toggleContent(contentId) {{
                const content = document.getElementById(contentId);
                const toggleIcon = document.getElementById(contentId.replace('-content', '-toggle'));
                
                if (content.classList.contains('show')) {{
                    content.classList.remove('show');
                    toggleIcon.classList.remove('rotated');
                }} else {{
                    content.classList.add('show');
                    toggleIcon.classList.add('rotated');
                }}
            }}

            function formatRawData(data, type) {{
                if (!data || Object.keys(data).length === 0) {{
                    return '<div class="no-data">目前無資料</div>';
                }}

                if (type === 'typhoon') {{
                    return formatTyphoonData(data);
                }} else if (type === 'weather') {{
                    return formatWeatherData(data);
                }} else if (type === 'alert') {{
                    return formatAlertData(data);
                }}
                
                return '<div class="no-data">無法解析資料</div>';
            }}

            function formatTyphoonData(data) {{
                let html = '';
                try {{
                    const records = data.records || {{}};
                    
                    if (records.tropicalCyclones && records.tropicalCyclones.tropicalCyclone) {{
                        const typhoons = records.tropicalCyclones.tropicalCyclone;
                        
                        typhoons.forEach((typhoon, index) => {{
                            const name = typhoon.cwaTyphoonName || typhoon.typhoonName || '未知熱帶氣旋';
                            const tyNo = typhoon.cwaTyNo || typhoon.cwaTdNo || '';
                            
                            html += `<div class="data-grid">`;
                            html += `<div class="data-item"><div class="data-item-label">🌀 颱風名稱</div><div class="data-item-value">${{name}}</div></div>`;
                            
                            if (tyNo) {{
                                html += `<div class="data-item"><div class="data-item-label">🏷️ 編號</div><div class="data-item-value">${{tyNo}}</div></div>`;
                            }}
                            
                            const analysisData = typhoon.analysisData || {{}};
                            const fixes = analysisData.fix || [];
                            
                            if (fixes.length > 0) {{
                                const latestFix = fixes[fixes.length - 1];
                                
                                if (latestFix.maxWindSpeed) {{
                                    const windKmh = (parseInt(latestFix.maxWindSpeed) * 3.6).toFixed(1);
                                    html += `<div class="data-item"><div class="data-item-label">💨 最大風速</div><div class="data-item-value">${{latestFix.maxWindSpeed}} m/s (${{windKmh}} km/h)</div></div>`;
                                }}
                                
                                if (latestFix.maxGustSpeed) {{
                                    const gustKmh = (parseInt(latestFix.maxGustSpeed) * 3.6).toFixed(1);
                                    html += `<div class="data-item"><div class="data-item-label">💨 最大陣風</div><div class="data-item-value">${{latestFix.maxGustSpeed}} m/s (${{gustKmh}} km/h)</div></div>`;
                                }}
                                
                                if (latestFix.pressure) {{
                                    html += `<div class="data-item"><div class="data-item-label">📊 中心氣壓</div><div class="data-item-value">${{latestFix.pressure}} hPa</div></div>`;
                                }}
                                
                                if (latestFix.movingSpeed) {{
                                    html += `<div class="data-item"><div class="data-item-label">🏃 移動速度</div><div class="data-item-value">${{latestFix.movingSpeed}} km/h</div></div>`;
                                }}
                                
                                if (latestFix.movingDirection) {{
                                    const directionMap = {{
                                        'N': '北', 'NNE': '北北東', 'NE': '東北', 'ENE': '東北東',
                                        'E': '東', 'ESE': '東南東', 'SE': '東南', 'SSE': '南南東',
                                        'S': '南', 'SSW': '南南西', 'SW': '西南', 'WSW': '西南西',
                                        'W': '西', 'WNW': '西北西', 'NW': '西北', 'NNW': '北北西'
                                    }};
                                    const directionZh = directionMap[latestFix.movingDirection] || latestFix.movingDirection;
                                    html += `<div class="data-item"><div class="data-item-label">➡️ 移動方向</div><div class="data-item-value">${{directionZh}}</div></div>`;
                                }}
                                
                                if (latestFix.coordinate) {{
                                    try {{
                                        const [lon, lat] = latestFix.coordinate.split(',');
                                        html += `<div class="data-item"><div class="data-item-label">📍 座標位置</div><div class="data-item-value">${{lat}}°N, ${{lon}}°E</div></div>`;
                                    }} catch (e) {{
                                        html += `<div class="data-item"><div class="data-item-label">📍 座標位置</div><div class="data-item-value">${{latestFix.coordinate}}</div></div>`;
                                    }}
                                }}
                                
                                if (latestFix.circleOf15Ms && latestFix.circleOf15Ms.radius) {{
                                    html += `<div class="data-item"><div class="data-item-label">🌪️ 暴風圈半徑</div><div class="data-item-value">${{latestFix.circleOf15Ms.radius}} km</div></div>`;
                                }}
                                
                                if (latestFix.fixTime) {{
                                    html += `<div class="data-item"><div class="data-item-label">🕐 觀測時間</div><div class="data-item-value">${{latestFix.fixTime.substring(0, 16)}}</div></div>`;
                                }}
                            }}
                            
                            html += `</div>`;
                            if (index < typhoons.length - 1) html += '<hr style="margin: 20px 0;">';
                        }});
                    }} else {{
                        html = '<div class="no-data">🌀 目前無活躍颱風</div>';
                    }}
                }} catch (error) {{
                    console.error('解析颱風資料失敗:', error);
                    html = '<div class="no-data">解析颱風資料失敗</div>';
                }}
                
                return html;
            }}

            function formatWeatherData(data) {{
                let html = '';
                try {{
                    const records = data.records || {{}};
                    const locations = records.location || [];
                    
                    if (locations.length === 0) {{
                        return '<div class="no-data">無天氣預報資料</div>';
                    }}
                    
                    locations.forEach((location, index) => {{
                        const locationName = location.locationName || '未知地區';
                        const elements = location.weatherElement || [];
                        
                        html += `<h4>${{locationName}}</h4>`;
                        html += `<div class="data-grid">`;
                        
                        elements.forEach(element => {{
                            const elementName = element.elementName || '';
                            const times = element.time || [];
                            
                            if (times.length > 0) {{
                                const latestTime = times[0];
                                const value = latestTime.parameter?.parameterName || '';
                                const startTime = latestTime.startTime || '';
                                
                                if (elementName === 'Wx' && value) {{
                                    html += `<div class="data-item"><div class="data-item-label">🌤️ 天氣現象</div><div class="data-item-value">${{value}}</div></div>`;
                                    html += `<div class="data-item"><div class="data-item-label">🕐 預報時間</div><div class="data-item-value">${{startTime.substring(0, 16)}}</div></div>`;
                                }} else if (elementName === 'PoP' && value) {{
                                    html += `<div class="data-item"><div class="data-item-label">🌧️ 降雨機率</div><div class="data-item-value">${{value}}%</div></div>`;
                                }} else if (elementName === 'MinT' && value) {{
                                    html += `<div class="data-item"><div class="data-item-label">🌡️ 最低溫度</div><div class="data-item-value">${{value}}°C</div></div>`;
                                }} else if (elementName === 'MaxT' && value) {{
                                    html += `<div class="data-item"><div class="data-item-label">🌡️ 最高溫度</div><div class="data-item-value">${{value}}°C</div></div>`;
                                }} else if (elementName === 'CI' && value) {{
                                    html += `<div class="data-item"><div class="data-item-label">😌 舒適度</div><div class="data-item-value">${{value}}</div></div>`;
                                }}
                            }}
                        }});
                        
                        html += `</div>`;
                        if (index < locations.length - 1) html += '<hr style="margin: 20px 0;">';
                    }});
                }} catch (error) {{
                    console.error('解析天氣資料失敗:', error);
                    html = '<div class="no-data">解析天氣資料失敗</div>';
                }}
                
                return html;
            }}

            function formatAlertData(data) {{
                let html = '';
                try {{
                    const records = data.records || {{}};
                    const locations = records.location || [];
                    
                    if (locations.length === 0) {{
                        return '<div class="no-data">無特報資料</div>';
                    }}
                    
                    locations.forEach((location, index) => {{
                        const locationName = location.locationName || '未知地區';
                        const hazards = location.hazardConditions?.hazards || [];
                        
                        if (hazards.length > 0) {{
                            html += `<h4>${{locationName}}</h4>`;
                            html += `<div class="data-grid">`;
                            
                            hazards.forEach(hazard => {{
                                const phenomena = hazard.phenomena || '';
                                const significance = hazard.significance || '';
                                const effectiveTime = hazard.effectiveTime || '';
                                
                                if (phenomena) {{
                                    html += `<div class="data-item"><div class="data-item-label">📢 特報類型</div><div class="data-item-value">${{phenomena}} ${{significance}}</div></div>`;
                                    if (effectiveTime) {{
                                        html += `<div class="data-item"><div class="data-item-label">🕐 生效時間</div><div class="data-item-value">${{effectiveTime.substring(0, 16)}}</div></div>`;
                                    }}
                                }}
                            }});
                            
                            html += `</div>`;
                        }}
                        
                        if (index < locations.length - 1) html += '<hr style="margin: 20px 0;">';
                    }});
                    
                    if (html === '') {{
                        html = '<div class="no-data">目前無特報資料</div>';
                    }}
                }} catch (error) {{
                    console.error('解析特報資料失敗:', error);
                    html = '<div class="no-data">解析特報資料失敗</div>';
                }}
                
                return html;
            }}

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

                    // 更新原始資料
                    const rawDataResponse = await fetch('/api/raw-data');
                    const rawData = await rawDataResponse.json();
                    
                    document.getElementById('typhoonData').innerHTML = formatRawData(rawData.typhoons, 'typhoon');
                    document.getElementById('weatherData').innerHTML = formatRawData(rawData.weather, 'weather');
                    document.getElementById('alertData').innerHTML = formatRawData(rawData.alerts, 'alert');
                    
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
    await line_notifier.send_test_notification_flex()
    
    return {
        "message": "測試 Flex Message 已發送",
        "sent_to": len(line_user_ids),
        "friends": line_user_ids
    }

# 暫時隱藏機場測試端點
# @app.post("/api/line/test-airport-notification")
# async def send_test_airport_notification():
#     """發送機場狀況測試通知給所有LINE好友"""
#     try:
#         departure_info = await airport_monitor.get_departure_info()
#         arrival_info = await airport_monitor.get_arrival_info()
#         flight_warnings = await airport_monitor.check_flight_conditions()
#         
#         airport_data = {
#             "departure_flights": departure_info,
#             "arrival_flights": arrival_info,
#             "warnings": flight_warnings,
#             "last_updated": datetime.now().isoformat()
#         }
#         
#         await line_notifier.push_airport_status_flex(airport_data)
#         
#         return {
#             "message": "機場狀況 Flex Message 已發送",
#             "sent_to": len(line_user_ids),
#             "airport_data": {
#                 "departure_count": len(departure_info) if isinstance(departure_info, list) else 0,
#                 "arrival_count": len(arrival_info) if isinstance(arrival_info, list) else 0,
#                 "warnings_count": len(flight_warnings)
#             }
#         }
#     except Exception as e:
#         logger.error(f"發送機場測試通知失敗: {e}")
#         return {
#             "error": "發送失敗",
#             "message": str(e)
#         }

# 暫時隱藏機場端點
# @app.get("/api/airport")
# async def get_airport_status():
#     """取得金門機場即時起降資訊"""
#     departure_info = await airport_monitor.get_departure_info()
#     arrival_info = await airport_monitor.get_arrival_info()
#     flight_warnings = await airport_monitor.check_flight_conditions()
#     
#     return {
#         "departure_flights": departure_info,
#         "arrival_flights": arrival_info,
#         "warnings": flight_warnings,
#         "last_updated": datetime.now().isoformat()
#     }

def main():
    """主函數"""
    print("🌀 颱風警訊播報系統啟動中...")
    print("📝 系統資訊:")
    print(f"- 監控地區: {', '.join(MONITOR_LOCATIONS)}")
    print(f"- 檢查間隔: {CHECK_INTERVAL} 秒")
    print(f"- 服務端口: {SERVER_PORT}")
    print(f"- 旅行日期: {TRAVEL_DATE}")
    print(f"- 體檢日期: {CHECKUP_DATE}")
    # print("- 機場監控: 金門機場 (KNH) 起降資訊")  # 暫時隱藏
    print("- 通知方式: LINE Bot Flex Message (支援視覺化通知)")
    
    if not API_KEY:
        print("⚠️ 警告: 中央氣象署API KEY尚未設定")
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("⚠️ 警告: LINE ACCESS TOKEN尚未設定，LINE功能將無法使用")
    
    print("\n📱 LINE Bot 觸發關鍵字:")
    print("- '颱風近況' - 查看完整監控狀況 (Flex Message)")
    # print("- '機場狀況' - 查看金門機場即時資訊 (Flex Message)")  # 暫時隱藏
    print("- '測試' - 發送測試訊息 (Flex Message)")
    print("- '幫助' / 'help' / '指令' - 顯示指令列表")
    print("📝 注意: Bot 只回應特定關鍵字，不會回覆所有訊息")
    
    print("\n🔗 API 端點:")
    print(f"- 監控儀表板: http://localhost:{SERVER_PORT}/")
    print(f"- 測試 Flex 通知: POST http://localhost:{SERVER_PORT}/api/line/test-notification")
    # print(f"- 測試機場 Flex 通知: POST http://localhost:{SERVER_PORT}/api/line/test-airport-notification")  # 暫時隱藏
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)

if __name__ == "__main__":
    main()
