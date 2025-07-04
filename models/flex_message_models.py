"""
Data models for LINE Flex Message components
Provides type-safe structures for building Flex Messages
"""

from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum


class FlexColor(Enum):
    """Predefined colors for Flex Message components"""
    PRIMARY = "#1E90FF"
    SUCCESS = "#28A745"
    WARNING = "#FFC107"
    DANGER = "#DC3545"
    INFO = "#17A2B8"
    LIGHT = "#F8F9FA"
    DARK = "#343A40"
    WHITE = "#FFFFFF"
    BLACK = "#000000"


class FlexSize(Enum):
    """Size options for Flex Message components"""
    XXS = "xxs"
    XS = "xs"
    SM = "sm"
    MD = "md"
    LG = "lg"
    XL = "xl"
    XXL = "xxl"
    FULL = "full"


class FlexWeight(Enum):
    """Font weight options"""
    REGULAR = "regular"
    BOLD = "bold"


class FlexAlign(Enum):
    """Alignment options"""
    START = "start"
    END = "end"
    CENTER = "center"


class FlexLayout(Enum):
    """Layout options for boxes"""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BASELINE = "baseline"


class FlexSpacing(Enum):
    """Spacing options"""
    NONE = "none"
    XS = "xs"
    SM = "sm"
    MD = "md"
    LG = "lg"
    XL = "xl"
    XXL = "xxl"


@dataclass
class FlexText:
    """Text component for Flex Messages"""
    text: str
    size: Optional[FlexSize] = None
    weight: Optional[FlexWeight] = None
    color: Optional[str] = None
    align: Optional[FlexAlign] = None
    wrap: Optional[bool] = None
    max_lines: Optional[int] = None
    flex: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        # Ensure text is never None or empty
        text_value = self.text if self.text is not None else ""
        if text_value == "":
            text_value = " "  # Use space instead of empty string to avoid LINE API issues
        
        result = {"type": "text", "text": text_value}
        
        if self.size:
            result["size"] = self.size.value
        if self.weight:
            result["weight"] = self.weight.value
        if self.color:
            result["color"] = self.color
        if self.align:
            result["align"] = self.align.value
        if self.wrap is not None:
            result["wrap"] = self.wrap
        if self.max_lines is not None:
            result["maxLines"] = self.max_lines
        if self.flex is not None:
            result["flex"] = self.flex
        
        return result


@dataclass
class FlexIcon:
    """Icon component for Flex Messages"""
    url: str
    size: Optional[FlexSize] = None
    aspect_ratio: Optional[str] = None
    margin: Optional[FlexSpacing] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {"type": "icon", "url": self.url}
        
        if self.size:
            result["size"] = self.size.value
        if self.aspect_ratio:
            result["aspectRatio"] = self.aspect_ratio
        if self.margin:
            result["margin"] = self.margin.value
        
        return result


@dataclass
class FlexImage:
    """Image component for Flex Messages"""
    url: str
    size: Optional[FlexSize] = None
    aspect_ratio: Optional[str] = None
    aspect_mode: Optional[str] = None
    background_color: Optional[str] = None
    margin: Optional[FlexSpacing] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {"type": "image", "url": self.url}
        
        if self.size:
            result["size"] = self.size.value
        if self.aspect_ratio:
            result["aspectRatio"] = self.aspect_ratio
        if self.aspect_mode:
            result["aspectMode"] = self.aspect_mode
        if self.background_color:
            result["backgroundColor"] = self.background_color
        if self.margin:
            result["margin"] = self.margin.value
        
        return result


@dataclass
class FlexButton:
    """Button component for Flex Messages"""
    action: Dict[str, Any]
    style: Optional[str] = None
    color: Optional[str] = None
    height: Optional[str] = None
    margin: Optional[FlexSpacing] = None
    flex: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        # Make a copy of the action dictionary to avoid modifying the original
        action_dict = self.action.copy()

        # Ensure 'label' is present in the action dictionary
        if "label" not in action_dict:
            action_dict["label"] = "Action" # Default label

        # Ensure 'text' is present for message actions
        if action_dict.get("type") == "message" and "text" not in action_dict:
            action_dict["text"] = action_dict.get("label", "Message") # Fallback to label or default

        # Ensure 'uri' is present for URI actions
        if action_dict.get("type") == "uri" and "uri" not in action_dict:
            action_dict["uri"] = "#" # Fallback to a placeholder URI

        result = {
            "type": "button",
            "action": action_dict # Use the potentially modified copy
        }
        
        if self.style:
            result["style"] = self.style
        if self.color:
            result["color"] = self.color
        if self.height:
            result["height"] = self.height
        if self.margin:
            result["margin"] = self.margin.value
        if self.flex is not None:
            result["flex"] = self.flex
        
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        logger.debug(f"FlexButton.to_dict() output: {result}")

        return result


@dataclass
class FlexSeparator:
    """Separator component for Flex Messages"""
    margin: Optional[FlexSpacing] = None
    color: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {"type": "separator"}
        
        if self.margin:
            result["margin"] = self.margin.value
        if self.color:
            result["color"] = self.color
        
        return result


@dataclass
class FlexSpacer:
    """Spacer component for Flex Messages"""
    size: Optional[FlexSize] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {"type": "spacer"}
        
        if self.size:
            result["size"] = self.size.value
        
        return result


@dataclass
class FlexBox:
    """Box component for Flex Messages"""
    layout: FlexLayout
    contents: List[Union[FlexText, FlexIcon, FlexImage, FlexButton, FlexSeparator, FlexSpacer, 'FlexBox']]
    spacing: Optional[FlexSpacing] = None
    margin: Optional[FlexSpacing] = None
    padding_all: Optional[FlexSpacing] = None
    padding_top: Optional[FlexSpacing] = None
    padding_bottom: Optional[FlexSpacing] = None
    padding_start: Optional[FlexSpacing] = None
    padding_end: Optional[FlexSpacing] = None
    background_color: Optional[str] = None
    border_color: Optional[str] = None
    border_width: Optional[str] = None
    corner_radius: Optional[str] = None
    flex: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "type": "box",
            "layout": self.layout.value,
            "contents": [content.to_dict() for content in self.contents]
        }
        
        if self.spacing:
            result["spacing"] = self.spacing.value
        if self.margin:
            result["margin"] = self.margin.value
        if self.padding_all:
            result["paddingAll"] = self.padding_all.value
        if self.padding_top:
            result["paddingTop"] = self.padding_top.value
        if self.padding_bottom:
            result["paddingBottom"] = self.padding_bottom.value
        if self.padding_start:
            result["paddingStart"] = self.padding_start.value
        if self.padding_end:
            result["paddingEnd"] = self.padding_end.value
        if self.background_color:
            result["backgroundColor"] = self.background_color
        if self.border_color:
            result["borderColor"] = self.border_color
        if self.border_width:
            result["borderWidth"] = self.border_width
        if self.corner_radius:
            result["cornerRadius"] = self.corner_radius
        if self.flex is not None:
            result["flex"] = self.flex
        
        return result


@dataclass
class FlexBubble:
    """Bubble container for Flex Messages"""
    body: FlexBox
    header: Optional[FlexBox] = None
    hero: Optional[FlexImage] = None
    footer: Optional[FlexBox] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "type": "bubble",
            "body": self.body.to_dict()
        }
        
        if self.header:
            result["header"] = self.header.to_dict()
        if self.hero:
            result["hero"] = self.hero.to_dict()
        if self.footer:
            result["footer"] = self.footer.to_dict()
        
        return result


@dataclass
class FlexCarousel:
    """Carousel container for Flex Messages"""
    contents: List[FlexBubble]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": "carousel",
            "contents": [bubble.to_dict() for bubble in self.contents]
        }


@dataclass
class FlexMessage:
    """Complete Flex Message structure"""
    alt_text: str
    contents: Union[FlexBubble, FlexCarousel]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": "flex",
            "altText": self.alt_text,
            "contents": self.contents.to_dict()
        }


class RiskLevel(Enum):
    """Risk level classifications for typhoon monitoring"""
    LOW = "低風險"
    MEDIUM = "中風險"
    HIGH = "高風險"
    EXTREME = "極高風險"


@dataclass
class TyphoonData:
    """Typhoon information data structure"""
    name: str
    wind_speed: Optional[str] = None
    max_gust: Optional[str] = None
    pressure: Optional[str] = None
    location: Optional[str] = None
    direction: Optional[str] = None
    speed: Optional[str] = None
    radius: Optional[str] = None
    time: Optional[str] = None


@dataclass
class WeatherData:
    """Weather information data structure"""
    location: str
    temperature_min: Optional[str] = None
    temperature_max: Optional[str] = None
    weather_description: Optional[str] = None
    rain_probability: Optional[str] = None
    comfort_level: Optional[str] = None


@dataclass
class RiskAssessment:
    """Risk assessment data structure"""
    travel_risk: str
    checkup_risk: str
    overall_status: str
    warnings: List[str]