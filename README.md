# ROX Bots

ROX 遊戲自動化工具集合。釣魚與園藝共用同一個 Python 虛擬環境。

## 目錄

```text
ROX/
├─ .venv/
├─ requirements.txt
├─ rox_fishing/
└─ rox_gardening/
```

## 共用環境

首次建立或重建環境：

```powershell
cd D:\ai-agent-project\ROX
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 執行

### 釣魚

```powershell
cd D:\ai-agent-project\ROX
.\.venv\Scripts\python.exe .\rox_fishing\fishing_bot.py
```

### 園藝

```powershell
cd D:\ai-agent-project\ROX
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py
```

## 多開 ROX

釣魚與園藝都支援列出視窗，並使用清單序號或 HWND 指定角色。偵測到多個
ROX 視窗但未指定時，Bot 會拒絕啟動，避免操作錯角色。

### 釣魚選窗

```powershell
cd D:\ai-agent-project\ROX

# 列出所有 ROX 視窗
.\.venv\Scripts\python.exe .\rox_fishing\fishing_bot.py --list-windows

# 使用清單中的序號
.\.venv\Scripts\python.exe .\rox_fishing\fishing_bot.py --window-index 2

# 使用 Windows 視窗 handle
.\.venv\Scripts\python.exe .\rox_fishing\fishing_bot.py --hwnd 8585488
```

### 園藝選窗

```powershell
cd D:\ai-agent-project\ROX

# 列出所有 ROX 視窗
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py --list-windows

# 使用清單中的序號
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py --window-index 2

# 使用 Windows 視窗 handle
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py --hwnd 8585488
```

`--window-index` 是 `--list-windows` 顯示的 1 起算序號。`--hwnd` 是 Windows
視窗識別碼，ROX 關閉重開後可能改變，因此平常使用 `--window-index` 較方便。

兩個 Bot 都使用前景螢幕擷取與 `SendInput`，不建議同時執行多個 Bot 程序，
否則視窗可能互相搶焦點。

各功能的詳細設定請參考子目錄內的 README。
