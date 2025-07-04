"""
Typhoon monitoring service for Typhoon Weather Monitor
Handles typhoon path analysis and regional threat assessment
"""

import asyncio
import logging
import math
from typing import Dict, List
import httpx
from config.settings import settings
from config.constants import TAIWAN_REGIONS, THREAT_RADII, WARNING_TEMPLATES, KEY_REGIONS

logger = logging.getLogger(__name__)

class TyphoonService:
    """Central Weather Administration typhoon monitoring service"""
    
    def __init__(self):
        # Configure SSL verification based on settings
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=settings.VERIFY_SSL
        )
        if not settings.VERIFY_SSL:
            logger.warning("SSL certificate verification is disabled for typhoon API requests")
        
        # 使用常數配置
        self.taiwan_regions = TAIWAN_REGIONS
        self.threat_radii = THREAT_RADII
    
    async def get_typhoon_paths(self) -> Dict:
        """取得颱風路徑資訊"""
        try:
            url = f"{settings.CWA_BASE_URL}/v1/rest/datastore/W-C0034-005"
            params = {
                "Authorization": settings.API_KEY,
                "format": "JSON"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得颱風路徑失敗: {e}")
            return {}
    
    def analyze_typhoons(self, typhoon_data: Dict) -> List[str]:
        """分析颱風路徑資料（僅考慮會影響台灣金門地區的颱風）"""
        warnings = []
        
        if not typhoon_data or 'records' not in typhoon_data:
            return warnings
        
        try:
            records = typhoon_data.get('records', {})
            
            # 新的颱風資料結構
            if 'tropicalCyclones' in records:
                tropical_cyclones = records['tropicalCyclones']
                typhoons = tropical_cyclones.get('tropicalCyclone', [])
                
                for typhoon in typhoons:
                    if not isinstance(typhoon, dict):
                        continue
                    
                    # 取得颱風名稱
                    typhoon_name = typhoon.get('typhoonName', '')
                    cwa_typhoon_name = typhoon.get('cwaTyphoonName', '')
                    cwa_td_no = typhoon.get('cwaTdNo', '')
                    
                    # 優先使用中文名稱，次選英文名稱，最後使用編號
                    if cwa_typhoon_name:
                        name = cwa_typhoon_name
                    elif typhoon_name:
                        name = typhoon_name  
                    elif cwa_td_no:
                        name = f"熱帶性低氣壓{cwa_td_no}"
                    else:
                        name = "未知熱帶氣旋"
                    
                    # 地理位置威脅評估
                    threat_assessment = self._assess_typhoon_regional_threat(typhoon, name)
                    
                    # 只處理會影響台灣金門地區的颱風
                    if not threat_assessment['will_affect_taiwan']:
                        logger.info(f"颱風 {name} 不會影響台灣金門地區，跳過評估")
                        continue
                    
                    # 從最新分析資料取得風速
                    analysis_data = typhoon.get('analysisData', {})
                    fixes = analysis_data.get('fix', [])
                    
                    if fixes:
                        latest_fix = fixes[-1]  # 取最新的資料
                        max_wind_speed = int(latest_fix.get('maxWindSpeed', 0))
                        coordinate = latest_fix.get('coordinate', '')
                        
                        # 檢查風速是否超過警戒值
                        # 將 m/s 轉換為 km/h (乘以 3.6)
                        max_wind_kmh = max_wind_speed * 3.6
                        
                        # 結合地理威脅和風速強度評估
                        if max_wind_kmh > 60:  # km/h
                            threat_level = threat_assessment['threat_level']
                            distance_info = threat_assessment['distance_info']
                            
                            if threat_level == "high" or max_wind_kmh > 80:
                                warning_msg = WARNING_TEMPLATES["typhoon_current"].format(
                                    name=name,
                                    wind_speed=max_wind_speed,
                                    wind_kmh=max_wind_kmh,
                                    threat_level="高風險",
                                    distance_info=distance_info
                                )
                                warnings.append(warning_msg)
                            elif threat_level == "medium" or max_wind_kmh > 60:
                                warning_msg = WARNING_TEMPLATES["typhoon_current"].format(
                                    name=name,
                                    wind_speed=max_wind_speed,
                                    wind_kmh=max_wind_kmh,
                                    threat_level="可能影響",
                                    distance_info=distance_info
                                )
                                warnings.append(warning_msg)
                        
                        # 檢查預報路徑威脅
                        if threat_assessment['forecast_threat']:
                            warnings.extend(threat_assessment['forecast_warnings'])
                            
                        # 計算關鍵區域的詳細時間預估
                        regional_timing = self._calculate_regional_timing(typhoon, name)
                        if regional_timing:
                            warnings.extend(regional_timing)
            
            # 舊的颱風資料結構（向後兼容）
            elif 'typhoon' in records:
                typhoons = records.get('typhoon', [])
                for typhoon in typhoons:
                    if not isinstance(typhoon, dict):
                        continue
                        
                    name = typhoon.get('typhoonName', '未知颱風')
                    
                    # 對舊格式也進行地理威脅評估
                    # 注意：舊格式可能沒有完整的座標資訊，做基本檢查
                    location = typhoon.get('location', {})
                    if location:
                        lat = location.get('latitude', 0)
                        lon = location.get('longitude', 0)
                        
                        # 簡單檢查是否在台灣周邊區域（擴大範圍以確保不遺漏）
                        if not (115 <= lon <= 125 and 20 <= lat <= 27):
                            logger.info(f"舊格式颱風 {name} 不在台灣周邊區域，跳過評估")
                            continue
                    
                    intensity = typhoon.get('intensity', {})
                    max_wind = intensity.get('maximumWind', {}).get('value', 0)
                    
                    if max_wind > 60:  # km/h
                        if max_wind > 80:
                            warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (高風險)")
                        else:
                            warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (可能影響)")
                            
        except Exception as e:
            logger.error(f"分析颱風資料失敗: {e}")
        
        return warnings
    
    def _assess_typhoon_regional_threat(self, typhoon: dict, typhoon_name: str = None) -> dict:
        """評估颱風是否會影響台灣金門地區"""
        assessment = {
            "will_affect_taiwan": False,
            "threat_level": "none",
            "distance_info": "",
            "forecast_threat": False,
            "forecast_warnings": [],
            "closest_distance": float('inf'),
            "affected_regions": []
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
                        
                        # 計算與各台灣地區的距離
                        min_distance = float('inf')
                        closest_region = ""
                        
                        for region_name, (region_lat, region_lon) in self.taiwan_regions.items():
                            distance = self._calculate_distance(lat, lon, region_lat, region_lon)
                            
                            if distance < min_distance:
                                min_distance = distance
                                closest_region = region_name
                            
                            # 檢查是否在威脅範圍內
                            if distance <= self.threat_radii["direct"]:
                                assessment["affected_regions"].append(f"{region_name}(直接威脅)")
                            elif distance <= self.threat_radii["moderate"]:
                                assessment["affected_regions"].append(f"{region_name}(中等威脅)")
                            elif distance <= self.threat_radii["indirect"]:
                                assessment["affected_regions"].append(f"{region_name}(間接威脅)")
                        
                        assessment["closest_distance"] = min_distance
                        
                        # 判斷威脅等級
                        if min_distance <= self.threat_radii["direct"]:
                            assessment["will_affect_taiwan"] = True
                            assessment["threat_level"] = "high"
                            assessment["distance_info"] = f" (距{closest_region}{min_distance:.0f}km)"
                        elif min_distance <= self.threat_radii["moderate"]:
                            assessment["will_affect_taiwan"] = True
                            assessment["threat_level"] = "medium"  
                            assessment["distance_info"] = f" (距{closest_region}{min_distance:.0f}km)"
                        elif min_distance <= self.threat_radii["indirect"]:
                            assessment["will_affect_taiwan"] = True
                            assessment["threat_level"] = "low"
                            assessment["distance_info"] = f" (距{closest_region}{min_distance:.0f}km)"
                        else:
                            # 颱風距離太遠，不會影響台灣
                            assessment["will_affect_taiwan"] = False
                            assessment["threat_level"] = "none"
                            
                    except (ValueError, IndexError):
                        pass
            
            # 分析預報路徑
            forecast_data = typhoon.get('forecastData', {})
            forecast_fixes = forecast_data.get('fix', [])
            # 使用傳入的颱風名稱，如果沒有則嘗試提取
            if not typhoon_name:
                cwa_typhoon_name = typhoon.get('cwaTyphoonName', '')
                eng_typhoon_name = typhoon.get('typhoonName', '')
                cwa_td_no = typhoon.get('cwaTdNo', '')
                
                if cwa_typhoon_name:
                    typhoon_name = cwa_typhoon_name
                elif eng_typhoon_name:
                    typhoon_name = eng_typhoon_name
                elif cwa_td_no:
                    typhoon_name = f"熱帶性低氣壓{cwa_td_no}"
                else:
                    typhoon_name = "未知熱帶氣旋"
            
            for forecast in forecast_fixes:
                if not isinstance(forecast, dict):
                    continue
                    
                coordinate = forecast.get('coordinate', '')
                tau = forecast.get('tau', '')
                
                if coordinate and tau:
                    try:
                        lon, lat = map(float, coordinate.split(','))
                        
                        # 檢查預報位置是否會影響台灣
                        for region_name, (region_lat, region_lon) in self.taiwan_regions.items():
                            distance = self._calculate_distance(lat, lon, region_lat, region_lon)
                            
                            if distance <= self.threat_radii["moderate"]:
                                assessment["will_affect_taiwan"] = True
                                assessment["forecast_threat"] = True
                                
                                hours = int(tau)
                                if hours <= 72:  # 只關注72小時內的預報
                                    warning_msg = WARNING_TEMPLATES["typhoon_forecast"].format(
                                        name=typhoon_name,
                                        tau=tau,
                                        region=region_name,
                                        distance=distance
                                    )
                                    assessment["forecast_warnings"].append(warning_msg)
                                break
                                
                    except (ValueError, TypeError):
                        continue
        
        except Exception as e:
            logger.error(f"評估颱風區域威脅失敗: {e}")
        
        return assessment

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """計算兩點間距離（公里）- 使用 Haversine 公式"""
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
    
    def _calculate_regional_timing(self, typhoon: dict, typhoon_name: str) -> List[str]:
        """計算颱風接近和離開金門、台南的詳細時間"""
        timing_warnings = []
        
        try:
            from datetime import datetime, timedelta
            
            forecast_data = typhoon.get('forecastData', {})
            forecast_fixes = forecast_data.get('fix', [])
            
            if not forecast_fixes:
                return timing_warnings
            
            # 為每個關鍵區域計算時間
            for region_name, (region_lat, region_lon) in KEY_REGIONS.items():
                approach_data = []
                
                # 分析預報點，找出接近和離開時間
                for forecast in forecast_fixes:
                    if not isinstance(forecast, dict):
                        continue
                    
                    coordinate = forecast.get('coordinate', '')
                    tau = forecast.get('tau', '')
                    
                    if coordinate and tau:
                        try:
                            lon, lat = map(float, coordinate.split(','))
                            distance = self._calculate_distance(lat, lon, region_lat, region_lon)
                            tau_hours = int(tau)
                            
                            # 收集距離數據
                            approach_data.append({
                                'tau': tau_hours,
                                'distance': distance,
                                'coordinate': (lat, lon)
                            })
                        except (ValueError, TypeError):
                            continue
                
                if not approach_data:
                    continue
                
                # 按時間排序
                approach_data.sort(key=lambda x: x['tau'])
                
                # 找出最接近的點
                closest_point = min(approach_data, key=lambda x: x['distance'])
                
                # 只有當最接近距離在威脅範圍內才計算
                if closest_point['distance'] <= self.threat_radii["moderate"]:
                    approach_time, depart_time = self._calculate_approach_depart_times(
                        approach_data, region_name, closest_point
                    )
                    
                    if approach_time and depart_time:
                        # 生成時間預估消息
                        now = datetime.now()
                        approach_dt = now + timedelta(hours=approach_time)
                        depart_dt = now + timedelta(hours=depart_time)
                        
                        summary_msg = WARNING_TEMPLATES["typhoon_summary"].format(
                            name=typhoon_name,
                            region=region_name,
                            approach_time=f"{approach_dt.strftime('%m/%d %H:%M')} ({approach_time}h)",
                            depart_time=f"{depart_dt.strftime('%m/%d %H:%M')} ({depart_time}h)"
                        )
                        timing_warnings.append(summary_msg)
                    
                    elif approach_time:  # 只有接近時間
                        now = datetime.now()
                        approach_dt = now + timedelta(hours=approach_time)
                        
                        timing_msg = WARNING_TEMPLATES["typhoon_timing"].format(
                            name=typhoon_name,
                            action="接近",
                            region=region_name,
                            time_str=approach_dt.strftime('%m/%d %H:%M'),
                            tau=approach_time
                        )
                        timing_warnings.append(timing_msg)
        
        except Exception as e:
            logger.error(f"計算區域時間失敗: {e}")
        
        return timing_warnings
    
    def _calculate_approach_depart_times(self, approach_data: List[dict], region_name: str, closest_point: dict) -> tuple:
        """計算接近和離開時間"""
        try:
            # 影響半徑設定（距離該區域多遠算"影響"）
            influence_radius = self.threat_radii["moderate"]  # 400km
            
            approach_time = None
            depart_time = None
            
            # 按時間排序的數據
            sorted_data = sorted(approach_data, key=lambda x: x['tau'])
            
            # 找接近時間：第一次進入影響範圍
            for data in sorted_data:
                if data['distance'] <= influence_radius:
                    approach_time = data['tau']
                    break
            
            # 找離開時間：最後一次在影響範圍內之後的時間點
            last_inside_index = -1
            for i, data in enumerate(sorted_data):
                if data['distance'] <= influence_radius:
                    last_inside_index = i
            
            if last_inside_index >= 0:
                # 找到最後一個在影響範圍內的點
                if last_inside_index < len(sorted_data) - 1:
                    # 有下一個預報點，檢查是否在影響範圍外
                    next_data = sorted_data[last_inside_index + 1]
                    if next_data['distance'] > influence_radius:
                        depart_time = next_data['tau']
                    else:
                        # 下一個點還在影響範圍內，估算離開時間
                        last_tau = sorted_data[last_inside_index]['tau']
                        depart_time = last_tau + 12  # 估算12小時後離開
                else:
                    # 這是最後一個預報點，估算離開時間
                    last_tau = sorted_data[last_inside_index]['tau']
                    depart_time = last_tau + 12  # 估算12小時後離開
            
            # 如果沒找到接近時間，但最接近點在合理範圍內，給出時間估算
            if not approach_time and closest_point['distance'] <= self.threat_radii["indirect"]:
                approach_time = closest_point['tau']
                depart_time = closest_point['tau'] + 6  # 估算6小時後離開
            
            return approach_time, depart_time
            
        except Exception as e:
            logger.error(f"計算接近離開時間失敗: {e}")
            return None, None
    
    async def close(self):
        """關閉HTTP客戶端"""
        await self.client.aclose()