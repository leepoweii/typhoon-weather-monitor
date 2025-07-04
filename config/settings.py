"""
Configuration management for Typhoon Weather Monitor
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # API Settings
    CWA_BASE_URL: str = "https://opendata.cwa.gov.tw/api"
    API_KEY: str = os.getenv("CWA_API_KEY", "")
    
    # LINE Bot Settings
    LINE_CHANNEL_ID: str = os.getenv("LINE_CHANNEL_ID", "")
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    
    # Monitoring Settings
    MONITOR_LOCATIONS: List[str] = [
        s.strip() for s in os.getenv("MONITOR_LOCATIONS", "金門縣,臺南市").split(",") 
        if s.strip()
    ]
    CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "300").split("#")[0].strip())
    TRAVEL_DATE: str = os.getenv("TRAVEL_DATE", "2025-07-06")
    CHECKUP_DATE: str = os.getenv("CHECKUP_DATE", "2025-07-07")
    
    # Server Settings
    SERVER_PORT: int = int(os.getenv("PORT", os.getenv("SERVER_PORT", "8000")).split("#")[0].strip())
    
    # Application Settings
    APP_TITLE: str = "颱風警訊播報系統"
    APP_DESCRIPTION: str = "監控金門縣和台南市的颱風警報"
    
    # Feature Flags
    ENABLE_AIRPORT_MONITORING: bool = False  # Disabled due to API key limitations
    
    # SSL Settings
    VERIFY_SSL: bool = os.getenv("VERIFY_SSL", "false").lower() == "true"  # Default False for development
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_fields = [
            'API_KEY',
            'LINE_CHANNEL_ID', 
            'LINE_CHANNEL_SECRET',
            'LINE_CHANNEL_ACCESS_TOKEN'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
        
        return True
    
    @classmethod
    def get_base_url(cls) -> str:
        """Get the base URL for the application"""
        return f"http://localhost:{cls.SERVER_PORT}"

# Global settings instance
settings = Settings()