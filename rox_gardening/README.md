# ROX Gardening Bot

Windows PC 版 ROX 園藝採集工具。

## 功能

- 每 0.1 秒檢查園藝按鈕，連續辨識到兩幀後才點擊
- 採集中按鈕消失時不會重複點擊
- 支援 Bot 驗證題的加法、減法與乘法
- 驗證畫面被系統訊息遮住時，會等待並重新擷取
- 連續兩次讀到相同算式後才開始輸入答案
- 每輸入一位數字都會讀回答案框
- 完整答案正確後才會送出
- 驗證完成後，園藝按鈕重新出現便立即繼續採集
- 按 `Q` 可隨時停止

## 環境

- Windows
- 遊戲視窗必須保持可見，不可最小化
- 建議固定使用相同的遊戲視窗大小
- 開發基準解析度為 `1280x720`

程式使用比例座標，因此 Windows DPI 縮放後顯示為 `1600x900` 也可運作。

## 安裝

```powershell
cd D:\ai-agent-project\ROX
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

釣魚與園藝共用 `ROX\.venv`。

## 畫面檢查

以下指令只會擷取和分析畫面，不會點擊：

```powershell
cd D:\ai-agent-project\ROX
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py --inspect
```

結果會儲存至 `debug\inspect.png`。

## 執行

```powershell
cd D:\ai-agent-project\ROX
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py
```

- 按 `Q` 停止 Bot
- 終端內也可按 `Ctrl+C` 停止
- 日誌位於 `logs\gardening_bot.log`

## 驗證保護

程式支援 `+`、`-`、`*` 題型。偵測到驗證視窗後：

1. 最多等待 4 秒，避開短暫的系統訊息遮罩。
2. 連續兩次辨識到相同算式後才作答。
3. 輸入每一位數字後，重新讀取答案框。
4. 答案框內容完整正確後，才按下確認。

若算式或答案框無法可靠辨識，程式會停止且不送出答案。相關畫面會儲存在
`debug` 目錄。
