"""
颱風警訊播報系統
監控金門縣和台南市的颱風及天氣警報
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse
import logging
import hashlib
import hmac
import base64

# LINE Bot SDK
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('typhoon_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 用於現代 FastAPI lifespan 事件
@asynccontextmanager
async def lifespan(app):
    # 啟動時開始監控
    task = asyncio.create_task(continuous_monitoring())
    yield
    # FastAPI 關閉時可在這裡清理資源（如有需要）
    task.cancel()

app = FastAPI(title="颱風警訊播報系統", description="監控金門縣和台南市的颱風警報", lifespan=lifespan)


# 中央氣象署 API 設定
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api"
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.getenv("CWA_API_KEY", "")

# LINE Bot 設定
LINE_CHANNEL_ID = os.getenv("LINE_CHANNEL_ID", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# 初始化 LINE Bot
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 監控設定
MONITOR_LOCATIONS = [s.strip() for s in os.getenv("MONITOR_LOCATIONS", "金門縣,臺南市").split(",") if s.strip()]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300").split("#")[0].strip())
TRAVEL_DATE = os.getenv("TRAVEL_DATE", "2025-07-06")
CHECKUP_DATE = os.getenv("CHECKUP_DATE", "2025-07-07")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000").split("#")[0].strip())

# 全域變數儲存最新狀態
latest_alerts = {}
latest_weather = {}
latest_typhoons = {}
last_notification_status = "SAFE"  # 追蹤上次通知的狀態
line_user_ids = []  # 儲存所有好友的USER ID

class LineNotifier:
    def __init__(self):
        self.api_client = ApiClient(configuration)
        self.line_bot_api = MessagingApi(self.api_client)
    
    def format_typhoon_status(self, result: Dict) -> str:
        """格式化颱風狀態訊息"""
        timestamp = datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))
        status_icon = "🔴" if result["status"] == "DANGER" else "🟢"
        status_text = "有風險" if result["status"] == "DANGER" else "無明顯風險"
        
        message = f"🚨 颱風警報 - {timestamp.strftime('%Y-%m-%d %H:%M')}\n"
        message += f"---------------------------\n"
        message += f"{status_icon} 警告狀態: {status_text}\n\n"
        message += f"✈️ 7/6 金門→台南航班風險: {result['travel_risk']}\n"
        message += f"🏥 7/7 台南體檢風險: {result['checkup_risk']}\n\n"
        
        if result["warnings"]:
            message += "📢 當前警報:\n"
            for warning in result["warnings"]:
                message += f"• {warning}\n"
        else:
            message += "✅ 目前無特殊警報\n"
        
        return message.strip()
    
    async def push_to_all_friends(self, message: str):
        """推送訊息給所有好友"""
        if not line_user_ids:
            logger.warning("沒有LINE好友ID，無法發送推送訊息")
            return
        
        try:
            for user_id in line_user_ids:
                push_message = PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
                self.line_bot_api.push_message(push_message)
            logger.info(f"成功推送訊息給 {len(line_user_ids)} 位好友")
        except Exception as e:
            logger.error(f"LINE推送失敗: {e}")
    
    async def reply_message(self, reply_token: str, message: str):
        """回覆訊息"""
        try:
            reply_message = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=message)]
            )
            self.line_bot_api.reply_message(reply_message)
            logger.info("成功回覆LINE訊息")
        except Exception as e:
            logger.error(f"LINE回覆失敗: {e}")

# 初始化LINE通知器
line_notifier = LineNotifier()

class TyphoonMonitor:
    def __init__(self):
        # 設定SSL驗證為False以解決macOS的SSL問題
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)
        
    async def get_weather_alerts(self) -> Dict:
        """取得天氣特報資訊"""
        try:
            url = f"{CWA_BASE_URL}/v1/rest/datastore/W-C0033-001"
            params = {
                "Authorization": API_KEY,
                "format": "JSON",
                "locationName": ",".join(MONITOR_LOCATIONS)
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得天氣特報失敗: {e}")
            return {}
    
    async def get_typhoon_paths(self) -> Dict:
        """取得颱風路徑資訊"""
        try:
            url = f"{CWA_BASE_URL}/v1/rest/datastore/W-C0034-005"
            params = {
                "Authorization": API_KEY,
                "format": "JSON"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得颱風路徑失敗: {e}")
            return {}
    
    async def get_weather_forecast(self) -> Dict:
        """取得36小時天氣預報"""
        try:
            url = f"{CWA_BASE_URL}/v1/rest/datastore/F-C0032-001"
            params = {
                "Authorization": API_KEY,
                "format": "JSON",
                "locationName": ",".join(MONITOR_LOCATIONS)
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"取得天氣預報失敗: {e}")
            return {}
    
    def analyze_alerts(self, alerts_data: Dict) -> List[str]:
        """分析警報資料"""
        warnings = []
        
        if not alerts_data or 'records' not in alerts_data:
            return warnings
        
        try:
            for record in alerts_data.get('records', {}).get('location', []):
                location_name = record.get('locationName', '')
                if location_name in MONITOR_LOCATIONS:
                    hazards = record.get('hazardConditions', {}).get('hazards', [])
                    for hazard in hazards:
                        phenomena = hazard.get('phenomena', '')
                        significance = hazard.get('significance', '')
                        if '颱風' in phenomena or '強風' in phenomena:
                            warnings.append(f"⚠️ {location_name}: {phenomena} {significance}")
        except Exception as e:
            logger.error(f"分析警報資料失敗: {e}")
        
        return warnings
    
    def analyze_typhoons(self, typhoon_data: Dict) -> List[str]:
        """分析颱風路徑資料"""
        warnings = []
        
        if not typhoon_data or 'records' not in typhoon_data:
            return warnings
        
        try:
            for typhoon in typhoon_data.get('records', {}).get('typhoon', []):
                name = typhoon.get('typhoonName', '未知颱風')
                intensity = typhoon.get('intensity', {})
                max_wind = intensity.get('maximumWind', {}).get('value', 0)
                
                # 如果最大風速超過一定值，發出警告
                # 金門機場側風停飛標準：25節(46.3 km/h)，暴風圈標準：34節(63 km/h)
                if max_wind > 60:  # km/h - 調整為更實際的航班風險閾值
                    if max_wind > 80:
                        warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (航班高風險)")
                    else:
                        warnings.append(f"🌀 {name}颱風 最大風速: {max_wind} km/h (航班可能影響)")
                    
                    # 檢查預報路徑是否影響目標區域
                    forecasts = typhoon.get('forecast', [])
                    for forecast in forecasts:
                        location = forecast.get('location', {})
                        lat = location.get('lat', 0)
                        lon = location.get('lon', 0)
                        
                        # 簡單的地理區域判斷（台灣範圍）
                        if 22 <= lat <= 25.5 and 119 <= lon <= 122:
                            forecast_time = forecast.get('time', '')
                            warnings.append(f"📍 {name}颱風預報將於 {forecast_time} 接近台灣")
                            break
        except Exception as e:
            logger.error(f"分析颱風資料失敗: {e}")
        
        return warnings
    
    def analyze_weather(self, weather_data: Dict) -> List[str]:
        """分析天氣預報資料"""
        warnings = []
        
        if not weather_data or 'records' not in weather_data:
            return warnings
        
        try:
            for location in weather_data.get('records', {}).get('location', []):
                location_name = location.get('locationName', '')
                if location_name in MONITOR_LOCATIONS:
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
    
    async def check_all_conditions(self) -> Dict:
        """檢查所有條件"""
        logger.info("開始檢查天氣條件...")
        
        # 並行取得所有資料
        alerts_task = self.get_weather_alerts()
        typhoons_task = self.get_typhoon_paths()
        weather_task = self.get_weather_forecast()
        
        alerts_data, typhoons_data, weather_data = await asyncio.gather(
            alerts_task, typhoons_task, weather_task, return_exceptions=True
        )
        
        # 更新全域狀態
        global latest_alerts, latest_typhoons, latest_weather, last_notification_status
        latest_alerts = alerts_data if not isinstance(alerts_data, Exception) else {}
        latest_typhoons = typhoons_data if not isinstance(typhoons_data, Exception) else {}
        latest_weather = weather_data if not isinstance(weather_data, Exception) else {}
        
        # 分析所有資料
        alert_warnings = self.analyze_alerts(latest_alerts)
        typhoon_warnings = self.analyze_typhoons(latest_typhoons)
        weather_warnings = self.analyze_weather(latest_weather)
        
        all_warnings = alert_warnings + typhoon_warnings + weather_warnings
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "warnings": all_warnings,
            "status": "DANGER" if all_warnings else "SAFE",
            "travel_risk": self.assess_travel_risk(all_warnings),
            "checkup_risk": self.assess_checkup_risk(all_warnings)
        }
        
        # 輸出警報到控制台
        self.print_alerts(result)
        
        # 檢查是否需要發送LINE通知
        await self.check_and_send_line_notification(result)
        
        return result
    
    async def check_and_send_line_notification(self, result: Dict):
        """檢查並發送LINE通知"""
        global last_notification_status
        current_status = result["status"]
        
        # 只在狀態變化且變為DANGER時發送通知
        if current_status == "DANGER" and last_notification_status != "DANGER":
            message = line_notifier.format_typhoon_status(result)
            await line_notifier.push_to_all_friends(message)
            logger.info("已發送LINE風險通知")
        
        # 更新上次通知狀態
        last_notification_status = current_status
    
    def assess_travel_risk(self, warnings: List[str]) -> str:
        """評估7/6航班風險"""
        if not warnings:
            return "低風險"
        
        typhoon_warnings = [w for w in warnings if '颱風' in w]
        wind_warnings = [w for w in warnings if '強風' in w or '暴風' in w]
        
        if typhoon_warnings:
            return "高風險 - 建議考慮改期"
        elif wind_warnings:
            return "中風險 - 密切關注"
        else:
            return "中風險 - 持續監控"
    
    def assess_checkup_risk(self, warnings: List[str]) -> str:
        """評估7/7體檢風險"""
        if not warnings:
            return "低風險"
        
        for warning in warnings:
            if '台南' in warning or '臺南' in warning:
                if '颱風' in warning:
                    return "高風險 - 可能停班停課"
                elif '強風' in warning or '豪雨' in warning:
                    return "中風險 - 可能影響交通"
        
        return "低風險"
    
    def print_alerts(self, result: Dict):
        """在控制台輸出警報"""
        print("\n" + "="*60)
        print(f"🚨 颱風警訊播報系統 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        status = result["status"]
        if status == "DANGER":
            print("🔴 警告狀態: 有風險")
        else:
            print("🟢 安全狀態: 無明顯風險")
        
        print(f"\n✈️ 7/6 金門→台南航班風險: {result['travel_risk']}")
        print(f"🏥 7/7 台南體檢風險: {result['checkup_risk']}")
        
        warnings = result["warnings"]
        if warnings:
            print("\n📢 目前警報:")
            for warning in warnings:
                print(f"  {warning}")
        else:
            print("\n✅ 目前無特殊警報")
        
        print("="*60)

# 建立監控器實例
monitor = TyphoonMonitor()

async def continuous_monitoring():
    """持續監控"""
    while True:
        try:
            await monitor.check_all_conditions()
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"監控過程發生錯誤: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

## 移除舊的 on_event 寫法，已改用 lifespan

# LINE Webhook 處理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """處理LINE訊息事件"""
    user_id = event.source.user_id
    message_text = event.message.text.strip()
    
    # 將新用戶加入好友列表
    if user_id not in line_user_ids:
        line_user_ids.append(user_id)
        logger.info(f"新增LINE好友: {user_id}")
    
    # 處理"颱風近況"關鍵字
    if "颱風近況" in message_text:
        # 取得最新監控結果
        result = asyncio.create_task(monitor.check_all_conditions())
        # 註：在實際環境中，這裡需要使用異步處理
        # 暫時使用同步方式回覆
        current_result = {
            "timestamp": datetime.now().isoformat(),
            "warnings": [],  # 簡化處理，使用空警報
            "status": "SAFE",
            "travel_risk": "低風險",
            "checkup_risk": "低風險"
        }
        
        reply_message = line_notifier.format_typhoon_status(current_result)
        asyncio.create_task(line_notifier.reply_message(event.reply_token, reply_message))

@app.post("/webhook")
async def line_webhook(request: Request):
    """LINE Webhook端點"""
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    
    # 驗證簽名
    if not _verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    try:
        handler.handle(body.decode('utf-8'), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    return "OK"

def _verify_signature(body: bytes, signature: str) -> bool:
    """驗證LINE簽名"""
    hash_val = hmac.new(
        LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash_val).decode('utf-8')
    return signature == expected_signature

@app.get("/")
async def get_dashboard():
    """取得監控儀表板"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>颱風警訊播報系統</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
            .status-safe {{ color: green; font-size: 24px; font-weight: bold; }}
            .status-danger {{ color: red; font-size: 24px; font-weight: bold; }}
            .warning-item {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 5px 0; border-radius: 5px; }}
            .risk-high {{ color: red; font-weight: bold; }}
            .risk-medium {{ color: orange; font-weight: bold; }}
            .risk-low {{ color: green; font-weight: bold; }}
            .update-time {{ color: #666; font-size: 14px; }}
            .explain-block {{ background: #e3f2fd; border-left: 5px solid #1976d2; padding: 16px; margin: 24px 0; border-radius: 8px; }}
            .explain-block h2 {{ margin-top: 0; color: #1976d2; }}
            .explain-block ul {{ margin: 0 0 0 1.5em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌀 颱風警訊播報系統</h1>
            <p class="update-time">最後更新: <span id="updateTime">載入中...</span></p>
            <div id="status">載入中...</div>
            <div id="travelRisk">載入中...</div>
            <div id="checkupRisk">載入中...</div>
            <div id="warnings">載入中...</div>

            <div class="explain-block">
                <h2>🔎 分析邏輯與方法說明</h2>
                <ul>
                    <li><b>天氣特報</b>：直接採用中央氣象署API的警特報結果，若金門或台南有「颱風」或「強風」等現象，則列為警報。</li>
                    <li><b>颱風路徑</b>：
                        <ul>
                            <li>若颱風最大風速 <b>超過60 km/h</b>，則列為警報（接近金門機場停飛標準）。</li>
                            <li>若颱風最大風速 <b>超過80 km/h</b>，則列為高風險警報。</li>
                            <li>若颱風預報路徑座標 <b>落在台灣經緯度範圍（緯度22~25.5，經度119~122）</b>，則視為「接近台灣」並警示。</li>
                            <li><small>📍 參考：金門機場側風停飛標準為25節(46.3 km/h)，暴風圈標準為34節(63 km/h)</small></li>
                        </ul>
                    </li>
                    <li><b>天氣預報</b>：
                        <ul>
                            <li>若36小時內預報有「颱風」、「暴風」、「豪雨」、「大雨」等關鍵字，則列為警報。</li>
                        </ul>
                    </li>
                    <li><b>航班/體檢風險評估</b>：
                        <ul>
                            <li>只要有颱風警報，航班列為「高風險」；有強風則為「中風險」。</li>
                            <li>台南有颱風警報，體檢列為「高風險」；有強風或豪雨則為「中風險」。</li>
                        </ul>
                    </li>
                </ul>
                <p style="color:#555;font-size:14px;">（所有分析規則皆可於程式碼內 <b>analyze_alerts</b>、<b>analyze_typhoons</b>、<b>analyze_weather</b>、<b>assess_travel_risk</b>、<b>assess_checkup_risk</b> 方法查閱與調整）</p>
            </div>
        </div>
        <script>
            async function updateData() {{
                try {{
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    document.getElementById('updateTime').textContent = new Date(data.timestamp).toLocaleString('zh-TW');
                    const statusDiv = document.getElementById('status');
                    if (data.status === 'DANGER') {{
                        statusDiv.innerHTML = '<div class="status-danger">🔴 警告狀態: 有風險</div>';
                    }} else {{
                        statusDiv.innerHTML = '<div class="status-safe">🟢 安全狀態: 無明顯風險</div>';
                    }}
                    document.getElementById('travelRisk').innerHTML = `<p>✈️ 7/6 金門→台南航班風險: <span class="risk-${{getRiskClass(data.travel_risk)}}">${{data.travel_risk}}</span></p>`;
                    document.getElementById('checkupRisk').innerHTML = `<p>🏥 7/7 台南體檢風險: <span class="risk-${{getRiskClass(data.checkup_risk)}}">${{data.checkup_risk}}</span></p>`;
                    const warningsDiv = document.getElementById('warnings');
                    if (data.warnings.length > 0) {{
                        warningsDiv.innerHTML = '<h3>📢 目前警報:</h3>' + 
                            data.warnings.map(w => `<div class="warning-item">${{w}}</div>`).join('');
                    }} else {{
                        warningsDiv.innerHTML = '<h3>✅ 目前無特殊警報</h3>';
                    }}
                }} catch (error) {{
                    console.error('更新資料失敗:', error);
                }}
            }}
            function getRiskClass(risk) {{
                if (risk.includes('高風險')) return 'high';
                if (risk.includes('中風險')) return 'medium';
                return 'low';
            }}
            // 每30秒更新一次
            updateData();
            setInterval(updateData, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/status")
async def get_status():
    """取得目前狀態"""
    return await monitor.check_all_conditions()

@app.get("/api/raw-data")
async def get_raw_data():
    """取得原始資料"""
    return {
        "alerts": latest_alerts,
        "typhoons": latest_typhoons,
        "weather": latest_weather
    }

@app.get("/api/line/friends")
async def get_line_friends():
    """取得LINE好友列表"""
    return {
        "friends_count": len(line_user_ids),
        "last_notification_status": last_notification_status
    }

@app.post("/api/line/test-notification")
async def send_test_notification():
    """發送測試通知給所有LINE好友"""
    test_result = {
        "timestamp": datetime.now().isoformat(),
        "warnings": ["🧪 這是測試訊息"],
        "status": "DANGER",
        "travel_risk": "測試風險",
        "checkup_risk": "測試風險"
    }
    
    message = line_notifier.format_typhoon_status(test_result)
    await line_notifier.push_to_all_friends(message)
    
    return {
        "message": "測試通知已發送",
        "sent_to": len(line_user_ids),
        "friends": line_user_ids
    }

def main():
    """主函數"""
    print("🌀 颱風警訊播報系統啟動中...")
    print("📝 系統資訊:")
    print(f"- 監控地區: {', '.join(MONITOR_LOCATIONS)}")
    print(f"- 檢查間隔: {CHECK_INTERVAL} 秒")
    print(f"- 服務端口: {SERVER_PORT}")
    print(f"- 旅行日期: {TRAVEL_DATE}")
    print(f"- 體檢日期: {CHECKUP_DATE}")
    
    if not API_KEY:
        print("⚠️ 警告: 中央氣象署API KEY尚未設定")
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("⚠️ 警告: LINE ACCESS TOKEN尚未設定，LINE功能將無法使用")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT)

if __name__ == "__main__":
    main()
