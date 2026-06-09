from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import config as cfg
from window_capture import get_client_bounds


@dataclass(frozen=True)
class CastPoint:
    x_ratio: float
    y_ratio: float
    bottom_offset: int | None = None
    reference_width: int | None = None
    reference_height: int | None = None


def save_cast_point(hwnd: int, screen_x: int, screen_y: int) -> CastPoint:
    bounds = get_client_bounds(hwnd)
    client_x = screen_x - bounds.left
    client_y = screen_y - bounds.top
    if not (0 <= client_x < bounds.width and 0 <= client_y < bounds.height):
        raise RuntimeError("滑鼠不在 ROX 遊戲內容範圍內。")

    point = CastPoint(
        x_ratio=client_x / bounds.width,
        y_ratio=client_y / bounds.height,
        bottom_offset=bounds.height - client_y,
        reference_width=bounds.width,
        reference_height=bounds.height,
    )
    cfg.CAST_POINT_FILE.write_text(
        json.dumps(
            {
                "version": 2,
                "x_ratio": point.x_ratio,
                "y_ratio": point.y_ratio,
                "bottom_offset": point.bottom_offset,
                "reference_width": point.reference_width,
                "reference_height": point.reference_height,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return point


def load_cast_point(path: Path = cfg.CAST_POINT_FILE) -> CastPoint:
    if not path.exists():
        raise RuntimeError(
            "尚未校準拋竿位置，請先執行：python calibrate.py point"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return CastPoint(
        x_ratio=float(data["x_ratio"]),
        y_ratio=float(data["y_ratio"]),
        bottom_offset=(
            int(data["bottom_offset"])
            if data.get("bottom_offset") is not None
            else None
        ),
        reference_width=data.get("reference_width"),
        reference_height=data.get("reference_height"),
    )


def resolve_cast_point(hwnd: int, point: CastPoint) -> tuple[int, int]:
    bounds = get_client_bounds(hwnd)
    x = round(bounds.width * point.x_ratio)
    if point.bottom_offset is None:
        y = round(bounds.height * point.y_ratio)
    elif point.reference_height:
        height_scale = bounds.height / point.reference_height
        scaled_bottom_offset = round(point.bottom_offset * height_scale)
        y = bounds.height - scaled_bottom_offset
    else:
        y = bounds.height - point.bottom_offset
    return (
        max(0, min(bounds.width - 1, x)),
        max(0, min(bounds.height - 1, y)),
    )
