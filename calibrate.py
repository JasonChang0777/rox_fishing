from __future__ import annotations

import argparse
import time

import cv2
import pyautogui

import config as cfg
from cast_point import save_cast_point
from vision import crop_ratio
from window_capture import capture_window, find_window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="擷取 ROX 釣魚狀態模板")
    parser.add_argument("template", choices=("cast", "empty", "point"))
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="擷取前等待秒數，預設 3 秒",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hwnd, title = find_window(cfg.WINDOW_TITLE_KEYWORDS)
    print(f"{args.delay:.1f} 秒後從「{title}」擷取 {args.template} 模板...")
    time.sleep(args.delay)

    if args.template == "point":
        position = pyautogui.position()
        ratio = save_cast_point(hwnd, position.x, position.y)
        frame = capture_window(hwnd, cfg.CAPTURE_MODE)
        height, width = frame.shape[:2]
        client_point = (
            round(width * ratio.x_ratio),
            round(height * ratio.y_ratio),
        )
        cfg.DEBUG_DIR.mkdir(exist_ok=True)
        cv2.circle(frame, client_point, 10, (0, 255, 255), -1)
        cv2.circle(frame, client_point, 18, (0, 0, 255), 3)
        cv2.imwrite(str(cfg.DEBUG_DIR / "cast_point.png"), frame)
        print(
            f"已儲存拋竿位置比例：x={ratio.x_ratio:.4f}, "
            f"y={ratio.y_ratio:.4f}"
        )
        print("請檢查 debug/cast_point.png，標記必須位於釣魚按鈕正中央。")
        return

    try:
        frame = capture_window(hwnd, cfg.CAPTURE_MODE)
    except RuntimeError as error:
        if cfg.CAPTURE_MODE != "printwindow" or "全黑畫面" not in str(error):
            raise
        print("PrintWindow 無法擷取 DirectX 畫面，改用螢幕擷取。")
        frame = capture_window(hwnd, "screen")
    if args.template == "cast":
        region = crop_ratio(frame, cfg.LIFT_BUTTON_ROI)
        output = cfg.CAST_TEMPLATE
    else:
        region = crop_ratio(frame, cfg.BAIT_ICON_ROI)
        output = cfg.EMPTY_BAIT_TEMPLATE

    cfg.TEMPLATE_DIR.mkdir(exist_ok=True)
    if not cv2.imwrite(str(output), region.image):
        raise RuntimeError(f"寫入模板失敗：{output}")
    print(f"已儲存：{output}")
    print("請打開圖片確認框內包含目標 UI；若範圍不準，調整 config.py 的 ROI。")


if __name__ == "__main__":
    main()
