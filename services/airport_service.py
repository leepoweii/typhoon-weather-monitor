"""
Airport monitoring service for Typhoon Weather Monitor - DISABLED
This service is disabled due to API key limitations
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class AirportService:
    """Airport monitoring service - DISABLED due to API limitations"""
    
    def __init__(self):
        logger.warning("Airport service is disabled due to API key limitations")
    
    async def get_departure_info(self) -> Dict:
        """取得機場起飛資訊 - 已禁用"""
        logger.info("Airport departure info is disabled")
        return {}
    
    async def get_arrival_info(self) -> Dict:
        """取得機場抵達資訊 - 已禁用"""
        logger.info("Airport arrival info is disabled")
        return {}
    
    def analyze_flight_status(self, departure_data: Dict, arrival_data: Dict) -> List[str]:
        """分析航班狀態 - 已禁用"""
        logger.info("Flight status analysis is disabled")
        return []
    
    async def check_flight_conditions(self) -> List[str]:
        """檢查航班條件 - 已禁用"""
        logger.info("Flight conditions check is disabled")
        return []
    
    async def close(self):
        """關閉服務（無需操作）"""
        pass