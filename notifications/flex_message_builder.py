"""
LINE Flex Message Builder for Typhoon Weather Monitor
Creates visual notification messages for LINE Bot
"""

import logging

import json
from datetime import datetime
from typing import Dict, List
from linebot.v3.messaging import FlexContainer, FlexMessage
from linebot.v3.messaging.models import (
    URIAction, FlexComponent
)
from config.settings import settings

logger = logging.getLogger(__name__)


def validate_uri(uri: str) -> str:
    """
    Validate and fix URI for LINE Bot usage
    LINE Bot requires proper URI schemes (http/https) and rejects localhost
    """
    if not uri:
        return "https://example.com"
    
    # Check if URI already has a scheme
    if not uri.startswith(('http://', 'https://')):
        # Add https scheme if missing
        uri = f"https://{uri}"
    
    # LINE Bot doesn't accept localhost URLs, use a placeholder
    if 'localhost' in uri or '127.0.0.1' in uri:
        return "https://example.com"
    
    return uri


class FlexMessageBuilder:

    def _error_flex_message(self, alt_text: str, main_text: str, sub_text: str) -> FlexMessage:
        """
        Helper to create a simple error FlexMessage.
        """
        error_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": main_text,
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": sub_text,
                        "size": "sm",
                        "color": "#999999",
                        "margin": "md"
                    }
                ]
            }
        }
        try:
            flex_container = FlexContainer.from_json(json.dumps(error_content))
            return FlexMessage(alt_text=alt_text, contents=flex_container)
        except Exception as e:
            logger.error(f"Error creating error flex message: {e}")
            # If FlexContainer creation fails, return a simple text message wrapped in FlexMessage
            simple_error = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": main_text
                        }
                    ]
                }
            }
            flex_container = FlexContainer.from_json(json.dumps(simple_error))
            return FlexMessage(alt_text=alt_text, contents=flex_container)
    # (class-level docstring removed, see __init__ for details)

    def __init__(self, base_url: str = None):
        """
        初始化 FlexMessageBuilder

        Args:
            base_url: 應用程式的基本URL，用於生成連結
        """
        self.base_url = base_url or settings.get_base_url()

    def create_typhoon_status_flex(self, result: Dict) -> FlexMessage:
        """
        創建颱風狀態的 Flex Message

        Args:
            result: 包含颱風監控結果的字典
        Returns:
            FlexMessage: LINE Flex Message 物件
        """
        try:
            timestamp = datetime.fromisoformat(
                result["timestamp"].replace('Z', '+00:00'))
            status_color = "#FF4757" if result["status"] == "DANGER" else "#2ED573"
            status_icon = "🔴" if result["status"] == "DANGER" else "🟢"
            status_text = "有風險" if result["status"] == "DANGER" else "無明顯風險"

            def get_risk_color(risk_text: str) -> str:
                if "高風險" in risk_text:
                    return "#FF4757"
                elif "中風險" in risk_text:
                    return "#FFA726"
                else:
                    return "#2ED573"

            body_contents = [
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
                    ]
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
                            "type": "text",
                            "text": "🎯 風險評估",
                            "weight": "bold",
                            "color": "#333333",
                            "size": "sm"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "xs",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"✈️ 航班風險: {result['travel_risk']}",
                                    "size": "xs",
                                    "color": get_risk_color(result['travel_risk']),
                                    "weight": "bold"
                                },
                                {
                                    "type": "text",
                                    "text": f"🏥 體檢風險: {result['checkup_risk']}",
                                    "size": "xs",
                                    "color": get_risk_color(result['checkup_risk']),
                                    "weight": "bold",
                                    "margin": "xs"
                                }
                            ]
                        }
                    ]
                }
            ]

            # 添加警告訊息
            if result.get("warnings"):
                body_contents.extend([
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
                            } for warning in result["warnings"][:3]  # 最多顯示3個警告
                        ]
                    }
                ])
            else:
                body_contents.extend([
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
                                "text": "✅ 目前無特殊警報",
                                "color": "#2ED573",
                                "size": "sm",
                                "weight": "bold"
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
                    "contents": body_contents
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "詳細資料",
                                "uri": validate_uri(self.base_url)
                            }
                        }
                    ],
                    "margin": "sm"
                }
            }

            try:
                flex_container = FlexContainer.from_json(json.dumps(flex_content))
                return FlexMessage(alt_text="颱風警訊通知", contents=flex_container)
            except Exception as json_error:
                logger.error(f"Error creating FlexContainer from JSON: {json_error}")
                logger.error(f"JSON content: {json.dumps(flex_content, indent=2)}")
                raise

        except KeyError as e:
            logger.error(f"Missing key in result data for flex message: {e}")
            return self._error_flex_message("資料錯誤", f"缺少必要欄位: {e}", "請檢查監控系統的輸出資料。")
        except Exception as e:
            logger.error(
                f"Error creating typhoon status flex message: {e}", exc_info=True)
            return self._error_flex_message("建立失敗", "無法生成颱風狀態通知", "系統發生未預期錯誤，請稍後再試。")

    def create_airport_status_flex(self, airport_data: Dict) -> 'FlexMessage':
        """
        創建機場狀態的 Flex Message (已禁用)

        Args:
            airport_data: 包含機場資訊的字典

        Returns:
            FlexMessage: LINE Flex Message 物件
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
        try:
            flex_container = FlexContainer.from_json(json.dumps(flex_content))
            return FlexMessage(alt_text="機場功能已禁用", contents=flex_container)
        except Exception as json_error:
            logger.error(f"Error creating airport status FlexContainer: {json_error}")
            return self._error_flex_message("建立失敗", "機場功能已禁用", "無法建立機場狀態通知")

    def create_test_notification_flex(self, message: str = "這是測試訊息") -> 'FlexMessage':
        """
        創建測試通知的 Flex Message

        Args:
            message: 測試訊息內容

        Returns:
            FlexMessage: LINE Flex Message 物件
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
                            "uri": validate_uri(self.base_url)
                        },
                        "style": "secondary"
                    }
                ],
                "margin": "sm"
            }
        }
        try:
            flex_container = FlexContainer.from_json(json.dumps(flex_content))
            return FlexMessage(alt_text="系統測試", contents=flex_container)
        except Exception as json_error:
            logger.error(f"Error creating test notification FlexContainer: {json_error}")
            return self._error_flex_message("建立失敗", "系統測試", "無法建立測試通知")

    def create_carousel_flex(self, bubbles: List[Dict]) -> 'FlexMessage':
        """
        創建輪播式 Flex Message

        Args:
            bubbles: 包含多個 bubble 內容的列表

        Returns:
            FlexMessage: LINE Flex Message 物件
        """
        flex_content = {
            "type": "carousel",
            "contents": bubbles
        }
        try:
            flex_container = FlexContainer.from_json(json.dumps(flex_content))
            return FlexMessage(alt_text="多項資訊", contents=flex_container)
        except Exception as json_error:
            logger.error(f"Error creating carousel FlexContainer: {json_error}")
            return self._error_flex_message("建立失敗", "多項資訊", "無法建立輪播訊息")

    def _get_typhoon_details_flex_content(self) -> List[Dict]:
        """獲取颱風詳細資料的 Flex Message 內容"""
        try:
            from utils.helpers import get_global_data
            typhoon_data = get_global_data('typhoon_data')

            if not typhoon_data:
                return [{
                    "type": "text",
                    "text": "目前沒有颱風詳細資料。",
                    "wrap": True,
                    "color": "#666666"
                }]

            contents = []
            for typhoon in typhoon_data:
                contents.append({
                    "type": "box",
                    "layout": "vertical",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"颱風名稱: {typhoon.get('name', 'N/A')}",
                            "weight": "bold"
                        },
                        {
                            "type": "text",
                            "text": f"距離: {typhoon.get('distance', 'N/A')} km",
                            "size": "sm"
                        }
                    ]
                })
            return contents
        except Exception as e:
            logger.error(
                f"Error getting typhoon details for flex content: {e}", exc_info=True)
            return [{
                "type": "text",
                "text": "無法載入颱風詳細資料。",
                "wrap": True,
                "color": "#FF4757"
            }]
