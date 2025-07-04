"""
Abstract base classes for risk assessment
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RiskAssessment(ABC):
    """Abstract base class for risk assessment"""
    
    @abstractmethod
    def assess_risk(self, warnings: List[str]) -> str:
        """Assess risk based on warnings"""
        pass

class TravelRiskAssessment(RiskAssessment):
    """Travel risk assessment base class"""
    
    def __init__(self, airport_enabled: bool = False):
        self.airport_enabled = airport_enabled
    
    def assess_risk(self, warnings: List[str]) -> str:
        """Assess travel risk"""
        if self.airport_enabled:
            return self._assess_airport_based_risk(warnings)
        else:
            return self._assess_weather_based_risk(warnings)
    
    def _assess_airport_based_risk(self, warnings: List[str]) -> str:
        """Assess risk based on actual airport data"""
        # This would use real airport API data
        typhoon_warnings = [w for w in warnings if '颱風' in w]
        flight_warnings = [w for w in warnings if '停飛' in w or '取消' in w]
        delay_warnings = [w for w in warnings if '延誤' in w]
        
        if flight_warnings:
            return "高風險 - 航班已停飛/取消"
        elif delay_warnings:
            return "中風險 - 航班延誤"
        elif typhoon_warnings:
            return "高風險 - 建議考慮改期"
        else:
            return "低風險"
    
    def _assess_weather_based_risk(self, warnings: List[str]) -> str:
        """Assess risk based on weather forecast only"""
        from config.constants import TRAVEL_RISK_MESSAGES
        
        if not warnings:
            return f"低風險 - {TRAVEL_RISK_MESSAGES['airport_disabled']}"
        
        typhoon_warnings = [w for w in warnings if '颱風' in w]
        wind_warnings = [w for w in warnings if '強風' in w or '暴風' in w]
        forecast_warnings = [w for w in warnings if '預報' in w]
        
        if typhoon_warnings:
            if forecast_warnings:
                return f"{TRAVEL_RISK_MESSAGES['typhoon_forecast']} - {TRAVEL_RISK_MESSAGES['airport_disabled']}"
            return f"{TRAVEL_RISK_MESSAGES['typhoon_high']} - {TRAVEL_RISK_MESSAGES['airport_disabled']}"
        elif wind_warnings:
            return f"{TRAVEL_RISK_MESSAGES['wind_warning']} - {TRAVEL_RISK_MESSAGES['airport_disabled']}"
        else:
            return f"{TRAVEL_RISK_MESSAGES['general_warning']} - {TRAVEL_RISK_MESSAGES['airport_disabled']}"

class CheckupRiskAssessment(RiskAssessment):
    """Medical checkup risk assessment"""
    
    def __init__(self, target_location: tuple, target_date: datetime):
        self.target_location = target_location  # (lat, lon)
        self.target_date = target_date
    
    def assess_risk(self, warnings: List[str]) -> str:
        """Assess checkup risk combining basic and geographic assessment"""
        basic_risk = self._assess_basic_risk(warnings)
        geographic_risk = self._assess_geographic_risk()
        
        return self._combine_risk_assessments(basic_risk, geographic_risk)
    
    def _assess_basic_risk(self, warnings: List[str]) -> str:
        """Basic risk assessment from warnings"""
        from config.constants import CHECKUP_RISK_MESSAGES
        
        if not warnings:
            return "低風險"
        
        for warning in warnings:
            if '台南' in warning or '臺南' in warning:
                if '颱風' in warning:
                    return CHECKUP_RISK_MESSAGES['typhoon_direct']
                elif '強風' in warning or '豪雨' in warning:
                    return CHECKUP_RISK_MESSAGES['typhoon_indirect']
        
        return "低風險"
    
    def _assess_geographic_risk(self) -> Dict:
        """Assess geographic risk from typhoon data"""
        from utils.helpers import get_global_data
        
        # Get data from global storage
        data = get_global_data()
        latest_typhoons = data['latest_typhoons']
        
        risk_assessment = {
            "level": "low",
            "distance": float('inf'),
            "details": "無颱風威脅",
            "forecast_impact": False
        }
        
        if not latest_typhoons:
            return risk_assessment
        
        try:
            records = latest_typhoons.get('records', {})
            if 'tropicalCyclones' in records:
                typhoons = records['tropicalCyclones'].get('tropicalCyclone', [])
                
                for typhoon in typhoons:
                    if not isinstance(typhoon, dict):
                        continue
                    
                    # 評估颱風威脅（需要存取 typhoon service）
                    threat_assessment = self._assess_typhoon_threat(typhoon)
                    
                    if threat_assessment['will_affect_taiwan']:
                        closest_distance = threat_assessment['closest_distance']
                        
                        if closest_distance < risk_assessment["distance"]:
                            risk_assessment["distance"] = closest_distance
                            
                            if threat_assessment["threat_level"] == "high":
                                risk_assessment["level"] = "high"
                                risk_assessment["details"] = f"颱風距離台南 {closest_distance:.0f} km，高度威脅"
                            elif threat_assessment["threat_level"] == "medium":
                                risk_assessment["level"] = "medium"
                                risk_assessment["details"] = f"颱風距離台南 {closest_distance:.0f} km，中等威脅"
                            
                            # 檢查預報威脅
                            if threat_assessment["forecast_threat"]:
                                risk_assessment["forecast_impact"] = True
                                risk_assessment["details"] += "，預報路徑可能影響"
                        
        except Exception as e:
            logger.error(f"評估颱風地理風險失敗: {e}")
        
        return risk_assessment
    
    def _assess_typhoon_threat(self, typhoon: dict) -> dict:
        """Assess typhoon threat for target location"""
        from config.constants import TAIWAN_REGIONS, THREAT_RADII
        import math
        
        assessment = {
            "will_affect_taiwan": False,
            "threat_level": "none",
            "closest_distance": float('inf'),
            "forecast_threat": False
        }
        
        try:
            # 分析當前位置
            analysis_data = typhoon.get('analysisData', {})
            fixes = analysis_data.get('fix', [])
            
            if fixes:
                latest_fix = fixes[-1]
                coordinate = latest_fix.get('coordinate', '')
                
                if coordinate:
                    try:
                        lon, lat = map(float, coordinate.split(','))
                        
                        # 計算與台南的距離
                        tainan_lat, tainan_lon = self.target_location
                        distance = self._calculate_distance(lat, lon, tainan_lat, tainan_lon)
                        
                        assessment["closest_distance"] = distance
                        
                        # 判斷威脅等級
                        if distance <= THREAT_RADII["direct"]:
                            assessment["will_affect_taiwan"] = True
                            assessment["threat_level"] = "high"
                        elif distance <= THREAT_RADII["moderate"]:
                            assessment["will_affect_taiwan"] = True
                            assessment["threat_level"] = "medium"
                        elif distance <= THREAT_RADII["indirect"]:
                            assessment["will_affect_taiwan"] = True
                            assessment["threat_level"] = "low"
                            
                    except (ValueError, IndexError):
                        pass
            
            # 檢查預報路徑威脅
            forecast_data = typhoon.get('forecastData', {})
            forecast_fixes = forecast_data.get('fix', [])
            
            for forecast in forecast_fixes:
                if not isinstance(forecast, dict):
                    continue
                    
                coordinate = forecast.get('coordinate', '')
                tau = forecast.get('tau', '')
                
                if coordinate and tau:
                    try:
                        lon, lat = map(float, coordinate.split(','))
                        
                        # 檢查預報位置是否會影響台南
                        tainan_lat, tainan_lon = self.target_location
                        distance = self._calculate_distance(lat, lon, tainan_lat, tainan_lon)
                        
                        if distance <= THREAT_RADII["moderate"]:
                            assessment["will_affect_taiwan"] = True
                            assessment["forecast_threat"] = True
                            break
                            
                    except (ValueError, TypeError):
                        continue
        
        except Exception as e:
            logger.error(f"評估颱風威脅失敗: {e}")
        
        return assessment
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """計算兩點間距離（公里）- 使用 Haversine 公式"""
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
    
    def _combine_risk_assessments(self, basic_risk: str, geographic_risk: Dict) -> str:
        """Combine basic and geographic risk assessments"""
        from config.constants import CHECKUP_RISK_MESSAGES
        
        # If basic risk is already high, maintain it
        if "高風險" in basic_risk:
            if geographic_risk["level"] == "high":
                return f"{basic_risk}\n詳細分析: {geographic_risk['details']}"
            return basic_risk
        
        # Upgrade based on geographic risk
        if geographic_risk["level"] == "high":
            return f"{CHECKUP_RISK_MESSAGES['geographic_high']}\n詳細分析: {geographic_risk['details']}"
        
        if geographic_risk["level"] == "medium" and "低風險" not in basic_risk:
            return f"{CHECKUP_RISK_MESSAGES['geographic_medium']}\n詳細分析: {geographic_risk['details']}"
        
        # Include geographic details if available
        if geographic_risk["level"] == "medium":
            return f"{basic_risk}\n詳細分析: {geographic_risk['details']}"
        
        return basic_risk