"""
Configuration for Flex Message templates and settings
Provides customizable settings for different message types
"""

from typing import Dict, Any
from models.flex_message_models import FlexColor


class FlexTemplateConfig:
    """Configuration settings for Flex Message templates"""
    
    # Color schemes for different risk levels
    RISK_COLORS = {
        "低風險": FlexColor.SUCCESS.value,
        "中風險": FlexColor.WARNING.value, 
        "高風險": FlexColor.DANGER.value,
        "極高風險": FlexColor.DANGER.value,
        "未知": FlexColor.DARK.value
    }
    
    # Weather condition icons
    WEATHER_ICONS = {
        "晴": "☀️",
        "多雲": "⛅", 
        "陰": "☁️",
        "雨": "🌧️",
        "雷雨": "⛈️",
        "颱風": "🌀",
        "強風": "💨",
        "豪雨": "🌊",
        "大雨": "🌧️",
        "小雨": "🌦️"
    }
    
    # Status icons
    STATUS_ICONS = {
        "DANGER": "🔴",
        "WARNING": "🟡", 
        "SAFE": "🟢",
        "INFO": "🔵",
        "UNKNOWN": "⚪"
    }
    
    # Template backgrounds
    BACKGROUNDS = {
        "danger": "#FFE6E6",
        "warning": "#FFF8E1",
        "safe": "#E6F7E6",
        "info": "#E3F2FD",
        "neutral": "#F8F9FA"
    }
    
    # Default button configurations
    DEFAULT_BUTTONS = {
        "typhoon_monitoring": [
            {
                "text": "🔄 更新狀態",
                "action": "更新狀態",
                "style": "primary",
                "color": FlexColor.PRIMARY.value
            },
            {
                "text": "📊 詳細資料", 
                "action": "詳細資料",
                "style": "secondary"
            }
        ],
        "test_message": [
            {
                "text": "✅ 測試通過",
                "action": "測試通過",
                "style": "primary",
                "color": FlexColor.SUCCESS.value
            },
            {
                "text": "🔄 重新測試",
                "action": "重新測試", 
                "style": "secondary"
            }
        ],
        "info_message": [
            {
                "text": "📖 了解更多",
                "action": "了解更多",
                "style": "primary"
            }
        ]
    }
    
    # Message limits and constraints
    LIMITS = {
        "max_text_length": 2000,
        "max_alt_text_length": 400,
        "max_components_per_box": 12,
        "max_buttons_per_row": 4,
        "max_carousel_bubbles": 12
    }
    
    # Typography settings
    TYPOGRAPHY = {
        "title": {
            "size": "lg",
            "weight": "bold"
        },
        "subtitle": {
            "size": "md", 
            "weight": "bold"
        },
        "body": {
            "size": "sm",
            "weight": "regular"
        },
        "caption": {
            "size": "xs",
            "weight": "regular"
        }
    }
    
    # Spacing and layout
    LAYOUT = {
        "card_padding": "md",
        "section_spacing": "md",
        "item_spacing": "sm",
        "button_spacing": "sm",
        "corner_radius": "8px",
        "border_width": "2px"
    }


class MessageTemplates:
    """Pre-defined message templates for common scenarios"""
    
    @staticmethod
    def get_danger_alert_template() -> Dict[str, Any]:
        """Template for danger level alerts"""
        return {
            "header": {
                "title": "🚨 颱風危險警報",
                "subtitle": "請立即採取防護措施",
                "background_color": FlexTemplateConfig.BACKGROUNDS["danger"],
                "title_color": FlexColor.DANGER.value
            },
            "sections": [
                "risk_assessment",
                "typhoon_details", 
                "weather_details",
                "warnings"
            ],
            "footer": "action_buttons"
        }
    
    @staticmethod
    def get_safe_status_template() -> Dict[str, Any]:
        """Template for safe status messages"""
        return {
            "header": {
                "title": "✅ 颱風監控狀態",
                "subtitle": "目前無明顯風險",
                "background_color": FlexTemplateConfig.BACKGROUNDS["safe"],
                "title_color": FlexColor.SUCCESS.value
            },
            "sections": [
                "status_summary",
                "current_weather"
            ],
            "footer": "monitoring_info"
        }
    
    @staticmethod
    def get_warning_template() -> Dict[str, Any]:
        """Template for warning level alerts"""
        return {
            "header": {
                "title": "⚠️ 颱風警告",
                "subtitle": "請注意相關風險",
                "background_color": FlexTemplateConfig.BACKGROUNDS["warning"],
                "title_color": FlexColor.WARNING.value
            },
            "sections": [
                "risk_assessment",
                "precautions",
                "weather_summary"
            ],
            "footer": "action_buttons"
        }
    
    @staticmethod
    def get_info_template() -> Dict[str, Any]:
        """Template for informational messages"""
        return {
            "header": {
                "title": "ℹ️ 系統資訊",
                "background_color": FlexTemplateConfig.BACKGROUNDS["info"],
                "title_color": FlexColor.INFO.value
            },
            "sections": [
                "content"
            ],
            "footer": "info_buttons"
        }
    
    @staticmethod
    def get_test_template() -> Dict[str, Any]:
        """Template for test messages"""
        return {
            "header": {
                "title": "🧪 系統測試",
                "subtitle": "功能正常性檢查",
                "background_color": FlexTemplateConfig.BACKGROUNDS["neutral"],
                "title_color": FlexColor.PRIMARY.value
            },
            "sections": [
                "test_results",
                "system_status"
            ],
            "footer": "test_buttons"
        }


class ValidationRules:
    """Validation rules for Flex Messages"""
    
    @staticmethod
    def validate_text_length(text: str, max_length: int = 2000) -> bool:
        """Validate text length"""
        return len(text) <= max_length
    
    @staticmethod
    def validate_alt_text(alt_text: str) -> bool:
        """Validate alt text"""
        return len(alt_text) <= FlexTemplateConfig.LIMITS["max_alt_text_length"]
    
    @staticmethod
    def validate_component_count(components: list) -> bool:
        """Validate component count in a box"""
        return len(components) <= FlexTemplateConfig.LIMITS["max_components_per_box"]
    
    @staticmethod
    def validate_button_count(buttons: list) -> bool:
        """Validate button count in a row"""
        return len(buttons) <= FlexTemplateConfig.LIMITS["max_buttons_per_row"]
    
    @staticmethod
    def validate_carousel_size(bubbles: list) -> bool:
        """Validate carousel bubble count"""
        return len(bubbles) <= FlexTemplateConfig.LIMITS["max_carousel_bubbles"]


class ThemeConfig:
    """Theme configuration for different scenarios"""
    
    THEMES = {
        "emergency": {
            "primary_color": FlexColor.DANGER.value,
            "background": FlexTemplateConfig.BACKGROUNDS["danger"],
            "accent_color": "#FF1744",
            "text_color": FlexColor.DARK.value
        },
        "warning": {
            "primary_color": FlexColor.WARNING.value,
            "background": FlexTemplateConfig.BACKGROUNDS["warning"],
            "accent_color": "#FF8F00",
            "text_color": FlexColor.DARK.value
        },
        "safe": {
            "primary_color": FlexColor.SUCCESS.value,
            "background": FlexTemplateConfig.BACKGROUNDS["safe"],
            "accent_color": "#00C853",
            "text_color": FlexColor.DARK.value
        },
        "info": {
            "primary_color": FlexColor.INFO.value,
            "background": FlexTemplateConfig.BACKGROUNDS["info"],
            "accent_color": "#0091EA",
            "text_color": FlexColor.DARK.value
        },
        "neutral": {
            "primary_color": FlexColor.DARK.value,
            "background": FlexTemplateConfig.BACKGROUNDS["neutral"],
            "accent_color": "#546E7A",
            "text_color": FlexColor.DARK.value
        }
    }
    
    @staticmethod
    def get_theme_by_risk_level(risk_text: str) -> Dict[str, str]:
        """Get theme based on risk level"""
        if "高風險" in risk_text or "極高風險" in risk_text:
            return ThemeConfig.THEMES["emergency"]
        elif "中風險" in risk_text:
            return ThemeConfig.THEMES["warning"]
        elif "低風險" in risk_text:
            return ThemeConfig.THEMES["safe"]
        else:
            return ThemeConfig.THEMES["neutral"]
    
    @staticmethod
    def get_theme_by_status(status: str) -> Dict[str, str]:
        """Get theme based on status"""
        status_map = {
            "DANGER": "emergency",
            "WARNING": "warning", 
            "SAFE": "safe",
            "INFO": "info"
        }
        return ThemeConfig.THEMES.get(status_map.get(status, "neutral"), ThemeConfig.THEMES["neutral"])


# Export main configuration classes
__all__ = [
    'FlexTemplateConfig',
    'MessageTemplates', 
    'ValidationRules',
    'ThemeConfig'
]