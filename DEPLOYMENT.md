# 🌀 颱風警訊播報系統 + ✈️ 金門機場監控

## 🚀 Zeabur 部署成功！

您的系統已成功部署到 Zeabur！

**部署 URL**: https://zeabur.com/projects/6867c29f3d3c8eb2f89e17d2/services/6867c2a00446dd4191a464fe?envID=6867c29f383ae96484bde431

## ⚙️ 必要設置 - 環境變數

為了讓系統正常運作，請在 Zeabur 控制台設置以下環境變數：

### 🌡️ 中央氣象署 API (可選，但建議設置)
```
CWA_API_KEY=您的氣象署API金鑰
```
> 取得方式：前往 [中央氣象署開放資料平臺](https://opendata.cwa.gov.tw) 註冊並申請 API 金鑰

### 📱 LINE Bot 設定 (用於推送通知)
```
LINE_CHANNEL_ID=您的LINE頻道ID
LINE_CHANNEL_SECRET=您的LINE頻道密鑰
LINE_CHANNEL_ACCESS_TOKEN=您的LINE存取權杖
```
> 取得方式：前往 [LINE Developers](https://developers.line.biz/) 創建 Messaging API 頻道

### 🔧 系統設定 (可選)
```
CHECK_INTERVAL=300
TRAVEL_DATE=2025-07-06
CHECKUP_DATE=2025-07-07
MONITOR_LOCATIONS=金門縣,臺南市
```

## 📋 功能特色

✅ **即時監控**
- 🌪️ 金門縣、台南市颱風警報
- ✈️ 金門機場起降即時資訊
- ⏰ 航班延誤自動檢測
- 🚫 停飛/取消即時通知

✅ **智能警報**
- 延誤超過30分鐘自動警告
- 颱風路徑影響評估
- 航班風險等級分析
- LINE 即時推送通知

✅ **Web 儀表板**
- 即時狀態查看
- 詳細分析邏輯說明
- API 端點查詢

## 🔗 API 端點

- `/` - Web 儀表板
- `/api/status` - 完整監控狀態
- `/api/airport` - 金門機場即時資訊
- `/api/raw-data` - 原始資料
- `/webhook` - LINE Bot Webhook

## 🎯 使用場景

完美適合：
- 金門-台灣航班旅客
- 需要關注天氣的商務人士
- 颱風季節的旅行規劃
- 機場延誤即時監控

## 🚀 重新部署

如需更新代碼：

```bash
cd /path/to/typhoon-weather-monitor
npx zeabur@latest
```

選擇現有專案即可更新部署。
typhoon-app/
├── app.py              # 主程式 - FastAPI 應用
├── zbpack.json         # Zeabur 部署配置 (無需 Dockerfile)
├── requirements.txt    # Python 依賴列表
├── pyproject.toml     # uv 本地開發管理
├── .env.example       # 環境變數範本
├── .gitignore         # Git 忽略配置  
├── README.md          # 完整說明文件
└── DEPLOYMENT.md      # 此部署說明
```

### 部署流程
1. **GitHub 推送**：將 `typhoon-app` 資料夾推送到 GitHub
2. **Zeabur 連接**：連接 GitHub 倉庫，選擇 `typhoon-app` 作為根目錄
3. **環境變數**：在 Zeabur 設定必要的環境變數
4. **自動部署**：Zeabur 會自動識別 Python 專案並依照 `zbpack.json` 部署
5. **LINE Webhook**：部署完成後設定 LINE Bot Webhook URL

### 關鍵檔案說明

#### zbpack.json
```json
{
  "name": "typhoon-monitor",
  "buildCommand": "pip install -r requirements.txt",
  "startCommand": "python app.py", 
  "environment": "python",
  "python": {
    "entry": "app.py",
    "version": "3.11"
  }
}
```

#### 必要環境變數
```bash
CWA_API_KEY=你的中央氣象署API金鑰
LINE_CHANNEL_ID=2007693532
LINE_CHANNEL_SECRET=cc738303673ab568fbc74b0bdaec4928
LINE_CHANNEL_ACCESS_TOKEN=你的LINE_ACCESS_TOKEN
CHECK_INTERVAL=300
SERVER_PORT=8000
TRAVEL_DATE=2025-07-06
CHECKUP_DATE=2025-07-07
MONITOR_LOCATIONS=金門縣,臺南市
```

## 🎯 部署優勢

1. **極簡配置**：無需 Dockerfile，僅需 zbpack.json
2. **自動識別**：Zeabur 自動識別 Python/FastAPI 專案
3. **環境變數管理**：所有敏感參數都透過環境變數管理
4. **一鍵部署**：GitHub 連接後即可自動部署
5. **版本控制**：Python 3.11 版本固定，確保穩定性

## 🚀 準備部署

此專案已準備好進行 Zeabur 部署，所有配置文件都已最佳化。
