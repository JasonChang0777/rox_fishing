# ROX Fishing Bot

Windows PC 版 ROX 釣魚畫面辨識工具。它會：

1. 找到標題含 `ROX` 或 `RÖX` 的遊戲視窗。
2. 偵測拋竿按鈕並開始釣魚。
3. 在提竿圓圈變綠時快速點擊三次。
4. 等待完成後繼續下一次。
5. 偵測基本魚餌用完的圖示並停止。

每一輪的順序是：

```text
檢查有限魚餌 → 拋竿 → 等待綠圈 → 收竿 → 再檢查魚餌
```

## 安裝

```powershell
cd D:\ai-agent-project\ROX
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 校準拋竿位置

先讓遊戲顯示可以拋竿的按鈕，再執行：

```powershell
cd D:\ai-agent-project\ROX\rox_fishing
..\.venv\Scripts\python.exe calibrate.py point --delay 5
```

倒數期間把滑鼠移到拋竿按鈕正中央，保持不動。程式會把位置儲存成遊戲
視窗內的比例座標，因此移動視窗不需要重新校準。

校準後請檢查 `debug/cast_point.png`，紅黃標記必須落在釣魚按鈕正中央。

接著單獨測試點擊：

```powershell
..\.venv\Scripts\python.exe test_click.py
```

三秒內切回遊戲。滑鼠應移到拋竿按鈕並完成一次點擊。若滑鼠有移動但遊戲
沒有反應，請關閉 ROX 的系統管理員模式，或用系統管理員權限啟動 PowerShell
和 VS Code，使兩者權限相同。

也可以測試不移動滑鼠、不切換視窗的背景 `PostMessage`：

```powershell
..\.venv\Scripts\python.exe test_background_click.py
```

如果 ROX 與 VS Code 使用相同的系統管理員權限後這個測試有效，可將
`config.py` 的 `CLICK_MODE` 改為 `"background"`。

## 校準魚餌模板

接著讓遊戲顯示「基本魚餌用完」的第四張圖：

```powershell
..\.venv\Scripts\python.exe calibrate.py empty
```

模板會存到 `templates`。請檢查圖片是否包含正確 UI。

## 執行

```powershell
cd D:\ai-agent-project\ROX
.\.venv\Scripts\python.exe .\rox_fishing\fishing_bot.py
```

由於程式使用螢幕擷取，預設不顯示 OpenCV 預覽窗，以免遮住遊戲。請在終端機
按 `Ctrl+C` 結束。

## 待辦功能

- **選填釣魚次數參數**
  - 未指定時維持目前行為，持續釣魚直到魚餌用完或手動停止。
  - 可指定預計完成的釣魚輪數，例如 `python fishing_bot.py --count 20`。
  - 完成指定輪數後記錄統計並正常結束。

- **狀態逾時保護**
  - 為 `CHECKING_BAIT`、`CASTING`、`WAITING_FOR_BITE` 和
    `WAITING_FOR_RESULT` 設定可調整的最長停留時間。
  - 同一狀態停留過久時，視為辨識或操作失敗。
  - 結束前記錄卡住的狀態、持續時間、最後辨識分數，並保存偵錯截圖。

## 背景操作限制

預設使用：

- `CAPTURE_MODE = "screen"`：直接擷取螢幕上的遊戲範圍。
- `CLICK_MODE = "sendinput"`：使用 Windows 實體輸入，這是目前實測最穩定的
  模式。

ROX 的 DirectX 畫面通常不支援 `PrintWindow`，因此遊戲畫面必須保持可見，
不能被其他視窗遮住或最小化。背景點擊仍可運作，但背景畫面辨識通常不可行。

ROX 在非前景狀態會忽略純 `PostMessage`，所以背景模式不可靠。`SendInput`
會短暫移動並使用滑鼠。畫面辨識使用螢幕擷取，因此遊戲不能最小化或被其他
視窗完全遮住。

## 調整辨識

終端機會顯示辨識數值：

- `green`：提竿按鈕中央的綠色比例。
- `empty`：目前魚餌圖示與用完模板的相似度。

發生誤判時，依預覽數值調整 `config.py` 內對應的 threshold。門檻越高越保守。

拋竿不再辨識透明按鈕，而是使用手動校準的比例座標。上鉤則動態搜尋高飽和
綠色圓圈，因此更換水面視角不會影響拋竿位置。
