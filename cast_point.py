from __future__ import annotations

import json
from pathlib import Path

import config as cfg
from window_capture import get_client_bounds


def save_cast_point(hwnd: int, screen_x: int, screen_y: int) -> tuple[float, float]:
    bounds = get_client_bounds(hwnd)
    client_x = screen_x - bounds.left
    client_y = screen_y - bounds.top
    if not (0 <= client_x < bounds.width and 0 <= client_y < bounds.height):
        raise RuntimeError("滑鼠不在 ROX 遊戲內容範圍內。")

    ratio = (client_x / bounds.width, client_y / bounds.height)
    cfg.CAST_POINT_FILE.write_text(
        json.dumps({"x_ratio": ratio[0], "y_ratio": ratio[1]}, indent=2),
        encoding="utf-8",
    )
    return ratio


def load_cast_point(path: Path = cfg.CAST_POINT_FILE) -> tuple[float, float]:
    if not path.exists():
        raise RuntimeError(
            "尚未校準拋竿位置，請先執行：python calibrate.py point"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return float(data["x_ratio"]), float(data["y_ratio"])


def resolve_cast_point(hwnd: int, ratio: tuple[float, float]) -> tuple[int, int]:
    bounds = get_client_bounds(hwnd)
    return round(bounds.width * ratio[0]), round(bounds.height * ratio[1])
