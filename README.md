# 🌪️ 颱風警訊播報系統

專為監控金門縣和台南市颱風及天氣警報的自動化系統，使用 FastAPI + LINE Bot 提供即時風險通知。

## ✨ 功能特色

- 🌪️ **智慧監控**：自動監控金門、台南兩地颱風與特殊天氣
- � **LINE Bot 推播**：風險狀態變化時自動推送通知給所有好友
- 🎯 **語音查詢**：支援「颱風現況」關鍵字即時查詢
- 📊 **網頁儀表板**：即時顯示監控狀態與風險分析
- 🔧 **環境變數管理**：完整的配置管理，敏感資料安全處理
- 🚀 **一鍵部署**：Zeabur 平台最佳化，無需 Dockerfile

## 🎯 監控邏輯

### 風速標準（基於實際航班停飛標準）
- **金門機場側風停飛**：25節 (46.3 km/h)
- **暴風圈定義**：34節 (63 km/h)
- **系統警報閾值**：60 km/h（可能影響）、80 km/h（高風險）

### 分析範圍
- **天氣特報**：中央氣象署官方警特報
- **颱風路徑**：最大風速 + 台灣經緯度範圍判斷
- **天氣預報**：36小時內惡劣天氣關鍵字偵測

## 🚀 部署到 Zeabur

### 環境變數設定

```bash
# 中央氣象署 API
CWA_API_KEY=你的API金鑰

# LINE Bot 設定
LINE_CHANNEL_ID=你的CHANNEL_ID
LINE_CHANNEL_SECRET=你的CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=你的ACCESS_TOKEN

# 監控設定
CHECK_INTERVAL=300
SERVER_PORT=8000
TRAVEL_DATE=2025-07-06
CHECKUP_DATE=2025-07-07
MONITOR_LOCATIONS=金門縣,臺南市
```

### 部署步驟

1. **Fork 此 Repository**
2. **Zeabur 部署**：
   - 連接 GitHub 帳號
   - 選擇此 repository
   - 設定上述環境變數
   - 點擊部署
3. **LINE Bot 設定**：
   - 複製 Zeabur 提供的域名
   - 在 LINE Developers 設定 Webhook URL: `https://your-domain.zeabur.app/webhook`

### 部署配置

- **zbpack.json**: 定義 Zeabur 部署配置，無需 Dockerfile
- **requirements.txt**: Python 依賴定義
- **pyproject.toml**: uv 本地開發包管理

## 🔧 本地開發

```bash
# 複製專案
git clone https://github.com/your-username/typhoon-weather-monitor.git
cd typhoon-weather-monitor

# 安裝依賴
uv sync

# 環境變數設定
cp .env.example .env
# 編輯 .env 填入實際參數

# 啟動服務
uv run python app.py
```

## 📊 API 端點

- `GET /` - 監控儀表板
- `GET /api/status` - 即時狀態 JSON
- `GET /api/raw-data` - 原始氣象資料
- `GET /api/line/friends` - LINE 好友管理
- `POST /api/line/test-notification` - 測試通知
- `POST /webhook` - LINE Webhook

## 📁 專案結構

```
typhoon-weather-monitor/
├── app.py              # 主程式 (FastAPI + LINE Bot)
├── zbpack.json         # Zeabur 部署配置
├── requirements.txt    # Python 依賴
├── pyproject.toml     # uv 包管理
├── .env.example       # 環境變數範本
├── .gitignore         # Git 忽略設定
├── README.md          # 專案說明
└── DEPLOYMENT.md      # 詳細部署說明
```

## 🛡️ 安全注意事項

- 🔒 所有敏感參數透過環境變數管理
- � LINE Bot 簽名驗證確保來源安全
- 🚫 `.env` 檔案已加入 `.gitignore`
- ✅ SSL 憑證驗證（生產環境建議啟用）

## � 授權

此專案採用 MIT 授權條款。

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

⚡ **快速開始**：複製此 repository → 設定環境變數 → 部署到 Zeabur → 享受自動颱風監控！
