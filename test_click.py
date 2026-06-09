from __future__ import annotations

import time

import config as cfg
from cast_point import load_cast_point, resolve_cast_point
from window_capture import click_client, find_window


def main() -> None:
    hwnd, title = find_window(cfg.WINDOW_TITLE_KEYWORDS)
    point = resolve_cast_point(hwnd, load_cast_point())
    print(f"3 秒後測試點擊「{title}」的 client={point}。")
    time.sleep(3.0)
    click_client(hwnd, point, cfg.CLICK_MODE)
    print("SendInput 已送出。若遊戲沒有反應，請用系統管理員權限啟動終端機。")


if __name__ == "__main__":
    main()
