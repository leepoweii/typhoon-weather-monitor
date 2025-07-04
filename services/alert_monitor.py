"""
Weather Alert Monitor Service
專門監控天氣特報並推送簡潔警告訊息
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)

class AlertMonitor:
    """天氣特報監控服務"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=settings.VERIFY_SSL
        )
        if not settings.VERIFY_SSL:
            logger.warning("SSL certificate verification is disabled for alert monitor")
        
        # 追蹤已發送的警報，避免重複通知
        self.sent_alerts: Set[str] = set()
        
        # 監控位置
        self.monitor_locations = ["金門縣", "臺南市"]
        
    async def get_weather_alerts(self) -> Dict:
        """取得天氣特報資訊"""
        try:
            url = f"{settings.CWA_BASE_URL}/v1/rest/datastore/W-C0033-001"
            params = {
                "Authorization": settings.API_KEY,
                "format": "JSON",
                "locationName": ",".join(self.monitor_locations),
                "phenomena": ""  # 空值表示取得所有現象
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得天氣特報失敗: {e}")
            return {}
    
    def extract_active_alerts(self, alerts_data: Dict) -> List[Dict]:
        """提取當前有效的警報"""
        active_alerts = []
        
        if not alerts_data or 'records' not in alerts_data:
            return active_alerts
        
        try:
            current_time = datetime.now()
            
            for location in alerts_data.get('records', {}).get('location', []):
                location_name = location.get('locationName', '')
                
                if location_name in self.monitor_locations:
                    hazards = location.get('hazardConditions', {}).get('hazards', [])
                    
                    for hazard in hazards:
                        # 檢查警報資訊
                        info = hazard.get('info', {})
                        phenomena = info.get('phenomena', '')
                        significance = info.get('significance', '')
                        
                        # 檢查有效時間
                        valid_time = hazard.get('validTime', {})
                        start_time_str = valid_time.get('startTime', '')
                        end_time_str = valid_time.get('endTime', '')
                        
                        if phenomena and significance:
                            # 檢查警報是否仍在有效期內
                            is_active = True
                            if end_time_str:
                                try:
                                    end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
                                    if current_time > end_time:
                                        is_active = False
                                except:
                                    pass  # 如果時間解析失敗，假設警報仍有效
                            
                            if is_active:
                                alert_id = f"{location_name}_{phenomena}_{significance}_{start_time_str}"
                                
                                active_alerts.append({
                                    'id': alert_id,
                                    'location': location_name,
                                    'phenomena': phenomena,
                                    'significance': significance,
                                    'start_time': start_time_str,
                                    'end_time': end_time_str
                                })
                        
        except Exception as e:
            logger.error(f"提取警報資料失敗: {e}")
        
        return active_alerts
    
    def format_alert_message(self, alerts: List[Dict]) -> str:
        """格式化警報訊息為簡潔文字"""
        if not alerts:
            return ""
        
        # 按地區分組
        location_alerts = {}
        for alert in alerts:
            location = alert['location']
            if location not in location_alerts:
                location_alerts[location] = []
            location_alerts[location].append(alert)
        
        # 建構訊息
        message_parts = ["🚨 天氣特報警告"]
        message_parts.append(f"📅 {datetime.now().strftime('%m/%d %H:%M')}")
        message_parts.append("")
        
        for location, location_alert_list in location_alerts.items():
            message_parts.append(f"📍 {location}")
            for alert in location_alert_list:
                phenomena = alert['phenomena']
                significance = alert['significance']
                
                # 根據警報類型添加適當的圖示
                icon = "⚠️"
                if "颱風" in phenomena:
                    icon = "🌀"
                elif "豪雨" in phenomena or "大雨" in phenomena:
                    icon = "🌧️"
                elif "強風" in phenomena:
                    icon = "💨"
                elif "雷雨" in phenomena:
                    icon = "⛈️"
                
                message_parts.append(f"  {icon} {phenomena}{significance}")
                
                # 添加時間資訊
                if alert['end_time']:
                    try:
                        end_time = datetime.strptime(alert['end_time'], '%Y-%m-%d %H:%M:%S')
                        end_time_str = end_time.strftime('%m/%d %H:%M')
                        message_parts.append(f"     至 {end_time_str}")
                    except:
                        pass
            message_parts.append("")
        
        # 添加提醒
        message_parts.append("請注意安全，做好防護措施")
        
        return "\n".join(message_parts).strip()
    
    def get_new_alerts(self, current_alerts: List[Dict]) -> List[Dict]:
        """取得新的警報（尚未發送通知的）"""
        new_alerts = []
        
        for alert in current_alerts:
            alert_id = alert['id']
            if alert_id not in self.sent_alerts:
                new_alerts.append(alert)
                self.sent_alerts.add(alert_id)
        
        return new_alerts
    
    def cleanup_sent_alerts(self, current_alerts: List[Dict]):
        """清理已過期的警報ID"""
        current_alert_ids = {alert['id'] for alert in current_alerts}
        self.sent_alerts = self.sent_alerts.intersection(current_alert_ids)
    
    async def check_and_format_alerts(self) -> str:
        """檢查警報並格式化為文字訊息"""
        # 取得最新警報資料
        alerts_data = await self.get_weather_alerts()
        
        # 提取有效警報
        active_alerts = self.extract_active_alerts(alerts_data)
        
        # 清理過期的警報追蹤
        self.cleanup_sent_alerts(active_alerts)
        
        # 取得新警報
        new_alerts = self.get_new_alerts(active_alerts)
        
        if new_alerts:
            logger.info(f"發現 {len(new_alerts)} 個新警報")
            return self.format_alert_message(new_alerts)
        
        return ""
    
    async def close(self):
        """關閉HTTP客戶端"""
        await self.client.aclose()
