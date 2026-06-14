# ROX Gardening Bot

## 點擊啟動與選擇視窗

直接雙擊：

```text
D:\ai-agent-project\ROX\啟動ROX Bot.bat
```

啟動器只會列出標題為 `ROX` 或 `RöX` 的遊戲視窗，不會列出啟動器、
檔案總管或其他名稱包含 ROX 的視窗。選擇遊戲視窗後，可按
「啟動園藝」或「啟動釣魚」。執行期間可按「停止 Bot」，也可以在
遊戲視窗按 `Q` 停止。

若清單沒有出現遊戲視窗，請確認 ROX 已開啟且視窗可見，再按
「重新整理」。最小化的遊戲視窗需要先還原。

啟動器會要求 Windows 系統管理員權限，讓 Bot 與以管理員權限執行的
ROX 使用相同權限層級。看到 UAC 視窗時，請確認程式路徑位於本專案的
`ROX\.venv\Scripts\pythonw.exe`。

Bot 不再模擬 `Alt` 鍵來切換前景視窗，避免程序被強制停止時留下按鍵
狀態。滑鼠點擊也使用 `finally` 保證送出左鍵放開；從啟動器停止 Bot
時會額外再送一次左鍵放開。

驗證答案會先點選輸入框，等待遊戲內數字鍵盤出現，再點擊校準後的
按鍵中心。每輸入一位數都會重新讀取答案框確認結果；若畫面沒有更新，
Bot 會安全停止，不會重複亂點或送出未確認的答案。

ROX 會忽略 Windows `PostMessage` 背景點擊，因此園藝使用較可靠的
`CLICK_MODE = "sendinput"`。每次點擊會短暫將游標移到遊戲按鈕，完成後
立即還原到原本位置。遊戲仍會取得前景焦點，而且視窗必須保持可見、
不可被其他視窗遮住，因為畫面辨識使用螢幕擷取。

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

## 多開 ROX

先列出目前可見的 ROX 視窗：

```powershell
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py --list-windows
```

再用清單序號或視窗 handle 指定要控制的角色：

```powershell
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py --window-index 2
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py --hwnd 1508906
```

偵測到多個 ROX 視窗但未指定時，程式會拒絕啟動，避免點錯角色。
目前點擊使用前景 `SendInput`，不建議同時執行多個 bot 程序，否則視窗會互相搶焦點。

## 驗證保護

程式支援 `+`、`-`、`*` 題型。偵測到驗證視窗後：

1. 最多等待 4 秒，避開短暫的系統訊息遮罩。
2. 連續兩次辨識到相同算式後才作答。
3. 輸入每一位數字後，重新讀取答案框。
4. 答案框內容完整正確後，才按下確認。

若算式或答案框無法可靠辨識，程式會停止且不送出答案。相關畫面會儲存在
`debug` 目錄。
