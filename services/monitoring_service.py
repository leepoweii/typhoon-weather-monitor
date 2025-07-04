"""
Main monitoring service for Typhoon Weather Monitor
Coordinates weather, typhoon, and risk assessment
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict
from services.weather_service import WeatherService
from services.typhoon_service import TyphoonService
from services.airport_service import AirportService
from services.risk_assessment import TravelRiskAssessment, CheckupRiskAssessment
from config.settings import settings
from utils.helpers import update_global_data

logger = logging.getLogger(__name__)

class TyphoonMonitor:
    """Main typhoon and weather monitoring service"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.typhoon_service = TyphoonService()
        self.airport_service = AirportService()  # Disabled service
        
        # Initialize risk assessment modules
        self.travel_risk_assessor = TravelRiskAssessment(
            airport_enabled=settings.ENABLE_AIRPORT_MONITORING
        )
        self.tainan_coordinates = (23.0, 120.2)  # 台南市座標
        self.checkup_date = datetime.strptime(settings.CHECKUP_DATE, '%Y-%m-%d')
        self.checkup_risk_assessor = CheckupRiskAssessment(
            target_location=self.tainan_coordinates,
            target_date=self.checkup_date
        )
    
    async def check_all_conditions(self) -> Dict:
        """檢查所有條件"""
        logger.info("開始檢查天氣條件...")
        
        # 並行取得所有資料（機場功能已禁用）
        alerts_task = self.weather_service.get_weather_alerts()
        typhoons_task = self.typhoon_service.get_typhoon_paths()
        weather_task = self.weather_service.get_weather_forecast()
        tainan_weekly_task = self.weather_service.get_tainan_weekly_weather()
        
        alerts_data, typhoons_data, weather_data, tainan_weekly_data = await asyncio.gather(
            alerts_task, typhoons_task, weather_task, tainan_weekly_task, return_exceptions=True
        )
        
        # 更新全域狀態 - 將資料暴露給其他模組使用
        update_global_data(alerts_data, typhoons_data, weather_data, tainan_weekly_data)
        
        # 分析所有資料
        alert_warnings = self.weather_service.analyze_alerts(
            alerts_data if not isinstance(alerts_data, Exception) else {}
        )
        typhoon_warnings = self.typhoon_service.analyze_typhoons(
            typhoons_data if not isinstance(typhoons_data, Exception) else {}
        )
        weather_warnings = self.weather_service.analyze_weather(
            weather_data if not isinstance(weather_data, Exception) else {}
        )
        
        all_warnings = alert_warnings + typhoon_warnings + weather_warnings
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "warnings": all_warnings,
            "status": "DANGER" if all_warnings else "SAFE",
            "travel_risk": self.travel_risk_assessor.assess_risk(all_warnings),
            "checkup_risk": self.checkup_risk_assessor.assess_risk(all_warnings)
        }
        
        # 輸出警報到控制台
        self.print_alerts(result)
        
        return result
    
    
    def print_alerts(self, result: Dict):
        """輸出警報到控制台"""
        timestamp = datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))
        status_icon = "🔴" if result["status"] == "DANGER" else "🟢"
        
        print(f"\n{'='*60}")
        print(f"🌀 颱風警訊播報 - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"{status_icon} 狀態: {result['status']}")
        print(f"✈️ 航班風險: {result['travel_risk']}")
        print(f"🏥 體檢風險: {result['checkup_risk']}")
        
        if result["warnings"]:
            print(f"\n⚠️ 警告訊息:")
            for i, warning in enumerate(result["warnings"], 1):
                print(f"  {i}. {warning}")
        else:
            print(f"\n✅ 無特殊警報")
        
        print(f"{'='*60}\n")
    
    async def close(self):
        """關閉所有服務"""
        await self.weather_service.close()
        await self.typhoon_service.close()
        await self.airport_service.close()