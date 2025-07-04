# Typhoon Weather Monitor - Development Guide

## Project Overview
A typhoon warning broadcast system that monitors weather alerts for Kinmen County and Tainan City, providing real-time notifications through LINE Bot.

## Environment Management
This project uses `uv` for Python environment management.

### Setup Development Environment
```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run the application
uv run python app.py
```

## Project Structure

```
typhoon-weather-monitor/
├── app.py                          # Main FastAPI application
├── config/
│   ├── __init__.py
│   └── settings.py                 # Configuration management
├── models/
│   ├── __init__.py
│   └── weather_models.py          # Data models and API response types
├── services/
│   ├── __init__.py
│   ├── weather_service.py         # Weather monitoring service
│   ├── typhoon_service.py         # Typhoon monitoring service
│   └── alert_service.py           # Alert monitoring service
├── notifications/
│   ├── __init__.py
│   ├── line_bot.py                # LINE Bot integration
│   └── flex_message_builder.py    # Flex Message builder
├── utils/
│   ├── __init__.py
│   └── helpers.py                 # Utility functions
└── tests/                         # Test files
```

## Module Responsibilities

### config/settings.py
- Environment variable loading
- Configuration validation
- API key management
- Server settings

### services/weather_service.py
- Weather API integration
- Weather data processing
- Weather alert analysis

### services/typhoon_service.py
- Typhoon API integration
- Typhoon path analysis
- Geographic threat assessment
- Risk level calculation

### services/alert_service.py
- Alert API integration
- Alert message processing
- Regional alert filtering

### notifications/line_bot.py
- LINE Bot webhook handling
- Message sending
- User management
- Notification scheduling

### notifications/flex_message_builder.py
- Modular FlexMessage builder with reusable components
- Template system for different message types (danger, safe, info, test)
- Automatic validation and error handling
- Factory pattern for message creation

### models/flex_message_models.py
- Type-safe data structures for FlexMessage components
- Dataclasses for typhoon, weather, and risk assessment data
- Enums for consistent styling and configuration

### config/flex_templates.py
- Configuration for FlexMessage templates and themes
- Validation rules and message limits
- Predefined templates for common scenarios

## Development Guidelines

### Code Style
- Follow PEP 8 conventions
- Use type hints for all functions
- Document functions with docstrings
- Keep functions focused and single-purpose

### API Integration
- Use async/await for all API calls
- Implement proper error handling
- Add retry logic for network failures
- Cache responses when appropriate

### Testing
- Write unit tests for all services
- Test API integrations with mock data
- Validate Flex Message generation
- Test risk assessment logic

### Configuration
- Use environment variables for all secrets
- Provide sensible defaults
- Document all configuration options
- Never commit API keys

## Important Notes

### Airport Functionality
- Airport risk checking is **DISABLED** due to API key limitations
- Airport-related code is preserved but commented out
- Can be re-enabled once API access is obtained

### LINE Bot Integration
- **FLEX MESSAGE SUPPORT**: Comprehensive FlexMessage functionality with text fallback
- System supports rich visual notifications through modular FlexMessage components
- Automatic fallback to text messaging if FlexMessage fails or is disabled
- Reply tokens expire quickly; handle "Invalid reply token" errors gracefully
- FlexMessageBuilder provides modular, reusable components for consistent UI

### Risk Assessment
- Tainan risk assessment includes geographic analysis
- Travel risk assessment focuses on flight safety
- Both assessments combine multiple data sources

### Monitoring
- System runs continuous monitoring every 5 minutes
- Notifications sent only when risk status changes
- Dashboard provides real-time status overview

## Environment Variables

```bash
# Central Weather Administration API
CWA_API_KEY=your_api_key_here

# LINE Bot Configuration
LINE_CHANNEL_ID=your_channel_id
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_access_token

# Monitoring Configuration
MONITOR_LOCATIONS=金門縣,臺南市
CHECK_INTERVAL=300
TRAVEL_DATE=2025-07-06
CHECKUP_DATE=2025-07-07
SERVER_PORT=8000

# FlexMessage Configuration
USE_FLEX_MESSAGES=true  # Enable FlexMessage support
FLEX_FALLBACK_ENABLED=true  # Enable fallback to text messages

# SSL Configuration
VERIFY_SSL=false  # Set to true in production, false for development
```

## Running Tests

```bash
# Run specific test files
uv run python test_typhoon_filtering.py
uv run python analyze_tainan_risk.py
uv run python analyze_travel_risk.py

# Run all tests
uv run python -m pytest tests/
```

## Deployment

The application is configured for deployment on platforms like Zeabur or Railway.

### Local Development
```bash
uv run python app.py
```

### Production Deployment
- Set all environment variables
- Configure port binding
- Enable logging
- Set up monitoring

## Troubleshooting

### Common Issues
1. **API Key Errors**: Ensure CWA_API_KEY is properly set
2. **LINE Bot Issues**: Verify all LINE Bot credentials
3. **FlexMessage Errors**: Check object vs JSON string usage
4. **Geographic Calculations**: Verify coordinate formats
5. **SSL Certificate Errors**: Set `VERIFY_SSL=false` in development environment

### SSL Certificate Issues
If you encounter SSL certificate verification errors:

```bash
# For development/testing - disable SSL verification
export VERIFY_SSL=false

# For production - enable SSL verification (default)
export VERIFY_SSL=true
```

**Note**: Disabling SSL verification should only be done in development environments. Always use SSL verification in production.

### Debug Mode
Set logging level to DEBUG in the application for detailed logs.

### Certificate Troubleshooting
- **macOS**: Certificate issues are common due to system certificate management
- **Development**: Use `VERIFY_SSL=false` to bypass certificate verification
- **Production**: Ensure proper certificate chain is available and use `VERIFY_SSL=true`

## FlexMessage System

### Overview
The FlexMessage system provides rich, interactive visual notifications with automatic fallback to text messaging. It uses a modular architecture for reusable components and consistent styling.

### Architecture

#### Core Components
- **FlexMessageBuilder**: Main builder class with JSON handling and validation
- **FlexMessageFactory**: Factory for creating different message types
- **Template Classes**: DangerTemplate, SafeTemplate, InfoTemplate, TestTemplate
- **Component Classes**: StatusCard, TyphoonInfoCard, WeatherCard, AlertCard, ActionButtonBar

#### Modular Components
```python
# Status Card - Risk level indicators with color coding
status_card = StatusCard(builder)
risk_card = status_card.create_risk_card("航班風險", "高風險", "✈️")

# Typhoon Info Card - Detailed typhoon information
typhoon_card = TyphoonInfoCard(builder)
info_card = typhoon_card.create_typhoon_card(typhoon_data)

# Weather Card - Location-specific weather data
weather_card = WeatherCard(builder)
weather_info = weather_card.create_weather_card(weather_data)

# Alert Card - Warning messages
alert_card = AlertCard(builder)
alerts = alert_card.create_alert_card(warnings, "🚨 緊急警告")
```

### Usage Examples

#### Creating a Typhoon Status Message
```python
from notifications.flex_message_builder import FlexMessageFactory
from models.flex_message_models import TyphoonData, WeatherData

# Initialize factory
factory = FlexMessageFactory()

# Create message with data
typhoon_data = TyphoonData(name="颱風凱米", wind_speed="35", pressure="980")
weather_data = [WeatherData(location="金門縣", weather_description="多雲")]

flex_message = factory.create_typhoon_status_message(
    result=risk_assessment_result,
    typhoon_data=typhoon_data,
    weather_data=weather_data
)

# Convert to JSON for debugging
json_output = factory.to_json(flex_message)
print(json_output)
```

#### Template Selection
The system automatically selects templates based on risk level:
- **DangerTemplate**: For high-risk situations (status="DANGER")
- **SafeTemplate**: For low-risk situations (status="SAFE")
- **InfoTemplate**: For general information
- **TestTemplate**: For system testing

### Configuration

#### Feature Flags
```bash
# Enable/disable FlexMessage functionality
USE_FLEX_MESSAGES=true

# Enable automatic fallback to text messages
FLEX_FALLBACK_ENABLED=true
```

#### Template Configuration
Templates can be customized through `config/flex_templates.py`:
- **Colors**: Risk level color coding
- **Icons**: Weather condition icons
- **Layouts**: Spacing and typography settings
- **Themes**: Different visual themes for various scenarios

### LINE Bot Integration

#### Automatic Fallback
The LINE Bot service automatically handles FlexMessage failures:
1. Attempts to send FlexMessage if enabled
2. Falls back to text message if FlexMessage fails
3. Logs appropriate error messages for debugging

#### Usage in LINE Bot
```python
# The LINE Bot automatically uses FlexMessages
await line_notifier.push_typhoon_status(result)
await line_notifier.reply_typhoon_status(reply_token, result)
await line_notifier.send_test_notification()
```

### Validation and Error Handling

#### Built-in Validation
- Text length limits (2000 characters for content, 400 for alt text)
- Component count limits (12 components per box)
- Button count limits (4 buttons per row)
- Carousel size limits (12 bubbles maximum)

#### Error Handling
- Graceful degradation to text messages
- Comprehensive logging for debugging
- Validation before sending to LINE API

### Troubleshooting FlexMessages

#### Common Issues
1. **Validation Errors**: Check component structure and limits
2. **JSON Serialization**: Ensure proper data types
3. **LINE API Errors**: Verify FlexMessage format compliance
4. **Fallback Triggered**: Check logs for specific error details

#### Debug Mode
Enable detailed logging for FlexMessage debugging:
```python
import logging
logging.getLogger('notifications.flex_message_builder').setLevel(logging.DEBUG)
```

#### Testing FlexMessages
Use the test message functionality to verify FlexMessage operation:
```python
# Create and validate test message
test_message = factory.create_test_message()
is_valid = factory.validate_message(test_message)
print(f"Message valid: {is_valid}")
```

## Contributing

1. Follow the modular structure
2. Write tests for new features
3. Update documentation
4. Use type hints
5. Follow existing code patterns