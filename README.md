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

釣魚：

```powershell
cd D:\ai-agent-project\ROX
.\.venv\Scripts\python.exe .\rox_fishing\fishing_bot.py
```

園藝：

```powershell
cd D:\ai-agent-project\ROX
.\.venv\Scripts\python.exe .\rox_gardening\gardening_bot.py
```

各功能的校準與使用方式請參考子目錄內的 README。
