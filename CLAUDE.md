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
- Flex Message creation
- Visual notification design
- Status card generation

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
- FlexMessage objects must be returned as objects, not JSON strings
- Use `FlexContainer.from_json()` for proper object creation from JSON strings
- FlexMessageBuilder returns FlexMessage objects directly, not dictionaries
- Avoid serializing objects to JSON unnecessarily
- Reply tokens expire quickly; handle "Invalid reply token" errors gracefully

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

## Contributing

1. Follow the modular structure
2. Write tests for new features
3. Update documentation
4. Use type hints
5. Follow existing code patterns