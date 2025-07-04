"""
Weather monitoring service for Typhoon Weather Monitor
Handles weather forecast and alert data from Central Weather Administration API
"""

import asyncio
import logging
from typing import Dict, List
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)

class WeatherService:
    """Central Weather Administration weather monitoring service"""
    
    def __init__(self):
        # Configure SSL verification based on settings
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=settings.VERIFY_SSL
        )
        if not settings.VERIFY_SSL:
            logger.warning("SSL certificate verification is disabled for weather API requests")
    
    async def get_weather_alerts(self) -> Dict:
        """取得天氣特報資訊"""
        try:
            url = f"{settings.CWA_BASE_URL}/v1/rest/datastore/W-C0033-001"
            params = {
                "Authorization": settings.API_KEY,
                "format": "JSON",
                "locationName": ",".join(settings.MONITOR_LOCATIONS)
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得天氣特報失敗: {e}")
            return {}
    
    async def get_weather_forecast(self) -> Dict:
        """取得36小時天氣預報"""
        try:
            url = f"{settings.CWA_BASE_URL}/v1/rest/datastore/F-C0032-001"
            params = {
                "Authorization": settings.API_KEY,
                "format": "JSON",
                "locationName": ",".join(settings.MONITOR_LOCATIONS)
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得天氣預報失敗: {e}")
            return {}
    
    async def get_tainan_weekly_weather(self) -> Dict:
        """取得台南市一週天氣預報"""
        try:
            url = f"{settings.CWA_BASE_URL}/v1/rest/datastore/F-D0047-091"
            params = {
                "Authorization": settings.API_KEY,
                "format": "JSON",
                "LocationName": "臺南市",
                "ElementName": "天氣現象,降雨機率"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得台南市週預報失敗: {e}")
            return {}
    
    def analyze_alerts(self, alerts_data: Dict) -> List[str]:
        """分析警報資料"""
        warnings = []
        
        if not alerts_data or 'records' not in alerts_data:
            return warnings
        
        try:
            for record in alerts_data.get('records', {}).get('location', []):
                location_name = record.get('locationName', '')
                if location_name in settings.MONITOR_LOCATIONS:
                    hazards = record.get('hazardConditions', {}).get('hazards', [])
                    for hazard in hazards:
                        phenomena = hazard.get('phenomena', '')
                        significance = hazard.get('significance', '')
                        if phenomena:
                            warnings.append(f"⚠️ {location_name}: {phenomena} {significance}")
        except Exception as e:
            logger.error(f"分析警報資料失敗: {e}")
        
        return warnings
    
    def analyze_weather(self, weather_data: Dict) -> List[str]:
        """分析天氣預報資料"""
        warnings = []
        
        if not weather_data or 'records' not in weather_data:
            return warnings
        
        try:
            for location in weather_data.get('records', {}).get('location', []):
                location_name = location.get('locationName', '')
                if location_name in settings.MONITOR_LOCATIONS:
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
    
    async def close(self):
        """關閉HTTP客戶端"""
        await self.client.aclose()