# LINE Flex Message Guide

## Introduction to Flex Messages

Flex Messages are a powerful message type for the LINE platform that allows you to create richly formatted messages with complex layouts. Unlike traditional message types, Flex Messages give you precise control over the appearance and layout of your content.

## Proper Flex Message Implementation

The LINE Bot SDK for Python requires specific steps to correctly create and send Flex Messages:

### 1. Create a JSON-like structure for your content

```python
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
                "size": "lg"
            }
        ]
    },
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            # Content elements here
        ]
    }
}
```

### 2. Convert to FlexContainer and wrap in FlexMessage

```python
import json
from linebot.v3.messaging import FlexMessage, FlexContainer

# Convert dictionary to FlexContainer
flex_container = FlexContainer.from_json(json.dumps(flex_content))

# Wrap in FlexMessage with alt_text
flex_message = FlexMessage(alt_text="颱風警訊通知", contents=flex_container)

# Now you can send this message
line_bot_api.reply_message(
    ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[flex_message]
    )
)
```

## Fixing Common Issues

### Issue: Returning dictionaries instead of FlexMessage objects

❌ **Incorrect approach:**
```python
def create_typhoon_status_flex(self, result: Dict) -> Dict:
    flex_content = {
        "type": "bubble",
        # content here
    }
    return flex_content  # Returning a raw dictionary
```

✅ **Correct approach:**
```python
def create_typhoon_status_flex(self, result: Dict) -> FlexMessage:
    import json
    flex_content = {
        "type": "bubble",
        # content here
    }
    flex_container = FlexContainer.from_json(json.dumps(flex_content))
    return FlexMessage(alt_text="颱風警訊通知", contents=flex_container)
```

### Issue: Syntax errors in JSON structure

Watch for proper nesting of JSON objects. Make sure each opening bracket has a matching closing bracket and that all commas are properly placed.

## Flex Message Examples

### Example 1: Simple Notification

```python
def create_notification_flex(message: str) -> FlexMessage:
    import json
    flex_content = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "系統通知",
                    "weight": "bold",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": message,
                    "wrap": True,
                    "margin": "md"
                }
            ]
        }
    }
    
    flex_container = FlexContainer.from_json(json.dumps(flex_content))
    return FlexMessage(alt_text="系統通知", contents=flex_container)
```

### Example 2: Creating a Carousel

```python
def create_carousel_flex(bubbles: List[Dict]) -> FlexMessage:
    import json
    flex_content = {
        "type": "carousel",
        "contents": bubbles
    }
    
    flex_container = FlexContainer.from_json(json.dumps(flex_content))
    return FlexMessage(alt_text="多項資訊", contents=flex_container)
```

## Best Practices

1. **Always include alt_text** - This is shown when the Flex Message cannot be displayed
2. **Test on different devices** - Appearance may vary between devices
3. **Keep content concise** - Too much content can make messages hard to read
4. **Handle errors gracefully** - Provide fallback content when data is missing
5. **Use appropriate colors and spacing** - For better readability

## Debugging Tips

1. Use the [Flex Message Simulator](https://developers.line.biz/flex-simulator/) to test your layouts
2. Check for proper JSON structure and nesting
3. Validate your Flex Message structure against LINE's specifications
4. Use try/except blocks when building Flex Messages to handle potential errors

## Complete Implementation Example

```python
from linebot.v3.messaging import FlexMessage, FlexContainer
from typing import Dict
import json

def create_typhoon_status_flex(result: Dict) -> FlexMessage:
    try:
        # Build your flex content dictionary
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
                    }
                ],
                "backgroundColor": "#FF4757"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "颱風資訊更新",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": result.get("message", "無詳細資訊"),
                        "wrap": True,
                        "margin": "md"
                    }
                ]
            }
        }
        
        # Convert to FlexContainer and wrap in FlexMessage
        flex_container = FlexContainer.from_json(json.dumps(flex_content))
        return FlexMessage(alt_text="颱風警訊通知", contents=flex_container)
            
    except Exception as e:
        # Create a simple error message
        error_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "颱風警訊播報系統",
                        "weight": "bold",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": "暫時無法顯示詳細資訊",
                        "size": "sm",
                        "color": "#999999",
                        "margin": "md"
                    }
                ]
            }
        }
        flex_container = FlexContainer.from_json(json.dumps(error_content))
        return FlexMessage(alt_text="系統錯誤通知", contents=flex_container)
```
