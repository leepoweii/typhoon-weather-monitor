"""
颱風警訊播報系統
監控金門縣和台南市的颱風及天氣警報
"""

import asyncio
import hashlib
import hmac
import base64
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# Import modular components
from config.settings import settings
from services.monitoring_service import TyphoonMonitor
from services.alert_monitor import AlertMonitor
from notifications.line_bot import LineNotifier, create_webhook_handler
from utils.helpers import get_global_data

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

# 全域變數儲存最新狀態
latest_alerts = {}
latest_weather = {}
latest_typhoons = {}
last_notification_status = "SAFE"
line_user_ids = []

# 初始化服務
monitor = TyphoonMonitor()
alert_monitor = AlertMonitor()
line_notifier = LineNotifier()
handler = create_webhook_handler()

# 初始化模板
templates = Jinja2Templates(directory="templates")

async def continuous_monitoring():
    """持續監控天氣條件"""
    logger.info("開始持續監控...")
    
    while True:
        try:
            result = await monitor.check_all_conditions()
            
            # 更新全域狀態
            global last_notification_status, latest_alerts, latest_weather, latest_typhoons
            latest_alerts = {}  # Will be updated by monitoring service
            latest_weather = {}  # Will be updated by monitoring service  
            latest_typhoons = {}  # Will be updated by monitoring service
            
            # 檢查是否需要發送通知
            await check_and_send_line_notification(result)
            
        except Exception as e:
            logger.error(f"監控過程中發生錯誤: {e}")
        
        # 等待下次檢查
        await asyncio.sleep(settings.CHECK_INTERVAL)

async def alert_monitoring():
    """每5分鐘檢查天氣特報並推送簡潔警告"""
    logger.info("開始天氣特報監控...")
    
    while True:
        try:
            # 檢查是否有新的警報
            alert_message = await alert_monitor.check_and_format_alerts()
            
            if alert_message:
                logger.info("發現新的天氣特報，準備發送通知")
                
                # 設置用戶ID並發送文字訊息
                line_notifier.set_user_ids(line_user_ids)
                await line_notifier.push_text_message(alert_message)
                
                logger.info("天氣特報通知已發送")
            
        except Exception as e:
            logger.error(f"天氣特報監控過程中發生錯誤: {e}")
        
        # 等待 5 分鐘
        await asyncio.sleep(300)  # 300 秒 = 5 分鐘

async def check_and_send_line_notification(result: dict):
    """檢查是否需要發送LINE通知"""
    global last_notification_status
    
    current_status = result["status"]
    
    # 只在狀態改變時發送通知
    if current_status != last_notification_status:
        logger.info(f"狀態變化：{last_notification_status} -> {current_status}")
        
        # 設置用戶ID
        line_notifier.set_user_ids(line_user_ids)
        
        # 發送文字通知
        await line_notifier.push_typhoon_status(result)
        
        # 更新狀態
        last_notification_status = current_status
    else:
        logger.info(f"狀態未變化：{current_status}")

# LINE Bot 訊息處理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """處理LINE Bot訊息"""
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    
    logger.info(f"收到來自用戶 {user_id} 的訊息: {user_message}")
    
    # 儲存用戶ID
    if user_id not in line_user_ids:
        line_user_ids.append(user_id)
        logger.info(f"新增用戶ID: {user_id}")
    
    # 只回應完全相等的「颱風現況」關鍵字
    if user_message == "颱風現況":
        logger.info(f"觸發關鍵字檢測: {user_message}")
        
        # 創建檢查任務
        async def handle_typhoon_status():
            try:
                result = await monitor.check_all_conditions()
                await line_notifier.reply_typhoon_status(event.reply_token, result)
            except Exception as e:
                logger.error(f"處理颱風狀態失敗: {e}")
                await line_notifier.reply_message(event.reply_token, f"系統暫時無法取得氣象資料，請稍後再試。錯誤: {str(e)}")
        
        # 執行檢查任務
        asyncio.create_task(handle_typhoon_status())
    else:
        logger.info(f"非觸發關鍵字，不回應: {user_message}")

# 用於現代 FastAPI lifespan 事件
@asynccontextmanager
async def lifespan(app):
    # 啟動時開始監控
    task = asyncio.create_task(continuous_monitoring())
    alert_task = asyncio.create_task(alert_monitoring())
    yield
    # FastAPI 關閉時清理資源
    task.cancel()
    alert_task.cancel()
    await monitor.close()

# FastAPI 應用程式
app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan
)

# LINE Bot Webhook
@app.post("/webhook")
async def line_webhook(request: Request):
    """LINE Bot webhook endpoint"""
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    
    if not _verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    return "OK"

def _verify_signature(body: bytes, signature: str) -> bool:
    """驗證LINE Bot簽名"""
    expected_signature = hmac.new(
        settings.LINE_CHANNEL_SECRET.encode(),
        body,
        hashlib.sha256
    ).digest()
    return signature == base64.b64encode(expected_signature).decode()

# API 端點
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """主頁面 - 監控儀表板"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "颱風警訊播報系統"
    })

@app.get("/api/status")
async def get_status():
    """取得目前監控狀態"""
    result = await monitor.check_all_conditions()
    return result

@app.get("/api/raw-data")
async def get_raw_data():
    """取得原始氣象資料"""
    data = get_global_data()
    return {
        "alerts": data['latest_alerts'],
        "typhoons": data['latest_typhoons'],
        "weather": data['latest_weather']
    }

@app.get("/api/line/friends")
async def get_line_friends():
    """取得LINE好友列表"""
    return {
        "friends_count": len(line_user_ids),
        "user_ids": line_user_ids
    }

@app.post("/api/line/test-notification")
async def send_test_notification():
    """發送測試通知"""
    if not line_user_ids:
        raise HTTPException(status_code=400, detail="沒有LINE好友，無法發送測試通知")
    
    try:
        line_notifier.set_user_ids(line_user_ids)
        await line_notifier.send_test_notification()
        return {
            "success": True,
            "message": f"測試通知已發送給 {len(line_user_ids)} 位好友"
        }
    except Exception as e:
        logger.error(f"發送測試通知失敗: {e}")
        raise HTTPException(status_code=500, detail=f"發送失敗: {str(e)}")

def main():
    """主函數"""
    # 驗證配置
    try:
        settings.validate()
        logger.info("配置驗證通過")
    except ValueError as e:
        logger.error(f"配置錯誤: {e}")
        return
    
    # 顯示啟動資訊
    logger.info("=" * 60)
    logger.info("🌀 颱風警訊播報系統")
    logger.info("=" * 60)
    logger.info(f"監控地區: {', '.join(settings.MONITOR_LOCATIONS)}")
    logger.info(f"檢查間隔: {settings.CHECK_INTERVAL} 秒")
    logger.info(f"航班日期: {settings.TRAVEL_DATE}")
    logger.info(f"體檢日期: {settings.CHECKUP_DATE}")
    logger.info(f"伺服器埠口: {settings.SERVER_PORT}")
    logger.info(f"機場監控: {'啟用' if settings.ENABLE_AIRPORT_MONITORING else '禁用'}")
    logger.info("=" * 60)
    logger.info("API 端點:")
    logger.info(f"- 儀表板: http://localhost:{settings.SERVER_PORT}/")
    logger.info(f"- 即時狀態: http://localhost:{settings.SERVER_PORT}/api/status")
    logger.info(f"- 測試通知: POST http://localhost:{settings.SERVER_PORT}/api/line/test-notification")
    logger.info("=" * 60)
    
    # 啟動服務器
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVER_PORT)

if __name__ == "__main__":
    main()