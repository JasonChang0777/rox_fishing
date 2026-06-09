from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

import config as cfg


@dataclass(frozen=True)
class Region:
    image: np.ndarray
    left: int
    top: int

    @property
    def center(self) -> tuple[int, int]:
        height, width = self.image.shape[:2]
        return self.left + width // 2, self.top + height // 2


@dataclass(frozen=True)
class TemplateMatch:
    score: float
    region: Region

    @property
    def center(self) -> tuple[int, int]:
        return self.region.center


@dataclass(frozen=True)
class GreenMatch:
    ratio: float
    region: Region

    @property
    def center(self) -> tuple[int, int]:
        return self.region.center


def crop_ratio(frame: np.ndarray, roi: tuple[float, float, float, float]) -> Region:
    height, width = frame.shape[:2]
    left = max(0, min(width - 1, round(width * roi[0])))
    top = max(0, min(height - 1, round(height * roi[1])))
    right = max(left + 1, min(width, round(width * roi[2])))
    bottom = max(top + 1, min(height, round(height * roi[3])))
    return Region(frame[top:bottom, left:right], left, top)


def crop_local_ratio(
    image: np.ndarray,
    roi: tuple[float, float, float, float],
) -> np.ndarray:
    height, width = image.shape[:2]
    left = max(0, min(width - 1, round(width * roi[0])))
    top = max(0, min(height - 1, round(height * roi[1])))
    right = max(left + 1, min(width, round(width * roi[2])))
    bottom = max(top + 1, min(height, round(height * roi[3])))
    return np.ascontiguousarray(image[top:bottom, left:right])


def crop_around(
    frame: np.ndarray,
    center: tuple[int, int],
    size: tuple[int, int],
) -> Region:
    frame_height, frame_width = frame.shape[:2]
    width, height = size
    left = max(0, min(frame_width - width, center[0] - width // 2))
    top = max(0, min(frame_height - height, center[1] - height // 2))
    right = min(frame_width, left + width)
    bottom = min(frame_height, top + height)
    return Region(frame[top:bottom, left:right], left, top)


def green_ratio(button_image: np.ndarray) -> float:
    hsv = cv2.cvtColor(button_image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array(cfg.GREEN_HSV_LOWER, dtype=np.uint8),
        np.array(cfg.GREEN_HSV_UPPER, dtype=np.uint8),
    )

    height, width = mask.shape
    yy, xx = np.ogrid[:height, :width]
    radius = min(width, height) * 0.34
    center_mask = (xx - width / 2) ** 2 + (yy - height / 2) ** 2 <= radius**2
    if not np.any(center_mask):
        return 0.0
    return float(np.count_nonzero(mask[center_mask]) / np.count_nonzero(center_mask))


def locate_green_button(
    frame: np.ndarray,
    roi: tuple[float, float, float, float],
) -> GreenMatch | None:
    search = crop_ratio(frame, roi)
    hsv = cv2.cvtColor(search.image, cv2.COLOR_BGR2HSV)
    lower = np.array(
        (cfg.GREEN_HSV_LOWER[0], cfg.GREEN_HSV_LOWER[1], 140),
        dtype=np.uint8,
    )
    upper = np.array(cfg.GREEN_HSV_UPPER, dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones((5, 5), dtype=np.uint8),
    )
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best: GreenMatch | None = None
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if area < 500 or perimeter <= 0:
            continue
        circularity = 4.0 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.35:
            continue

        x, y, width, height = cv2.boundingRect(contour)
        side = max(width, height, 80)
        center = (
            search.left + x + width // 2,
            search.top + y + height // 2,
        )
        region = crop_around(frame, center, (side, side))
        ratio = green_ratio(region.image)
        candidate = GreenMatch(ratio, region)
        if best is None or candidate.ratio > best.ratio:
            best = candidate

    return best


def load_template(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    template = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if template is None:
        raise RuntimeError(f"無法讀取模板：{path}")
    return template


def crop_cast_template(template: np.ndarray) -> np.ndarray:
    """Remove water and label text, keeping only the circular cast icon."""
    height, width = template.shape[:2]
    left = round(width * 0.25)
    right = round(width * 0.75)
    top = round(height * 0.12)
    bottom = round(height * 0.65)
    return np.ascontiguousarray(template[top:bottom, left:right])


def image_similarity(image: np.ndarray, template: np.ndarray | None) -> float:
    if template is None or image.size == 0:
        return 0.0
    resized = cv2.resize(template, (image.shape[1], image.shape[0]))
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    image_edges = cv2.Canny(image_gray, 60, 140)
    template_edges = cv2.Canny(template_gray, 60, 140)
    gray_score = float(
        cv2.matchTemplate(image_gray, template_gray, cv2.TM_CCOEFF_NORMED)[0, 0]
    )
    edge_score = float(
        cv2.matchTemplate(image_edges, template_edges, cv2.TM_CCOEFF_NORMED)[0, 0]
    )
    return max(0.0, min(1.0, gray_score * 0.45 + edge_score * 0.55))


def locate_template(
    frame: np.ndarray,
    template: np.ndarray | None,
    roi: tuple[float, float, float, float],
    scales: tuple[float, ...],
) -> TemplateMatch | None:
    if template is None:
        return None

    search = crop_ratio(frame, roi)
    search_gray = cv2.cvtColor(search.image, cv2.COLOR_BGR2GRAY)
    search_edges = cv2.Canny(search_gray, 60, 140)
    best: TemplateMatch | None = None

    for scale in scales:
        width = max(1, round(template.shape[1] * scale))
        height = max(1, round(template.shape[0] * scale))
        if width > search.image.shape[1] or height > search.image.shape[0]:
            continue

        resized = cv2.resize(template, (width, height))
        template_gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        template_edges = cv2.Canny(template_gray, 60, 140)
        gray_map = cv2.matchTemplate(
            search_gray, template_gray, cv2.TM_CCOEFF_NORMED
        )
        edge_map = cv2.matchTemplate(
            search_edges, template_edges, cv2.TM_CCOEFF_NORMED
        )
        score_map = gray_map * 0.45 + edge_map * 0.55
        _, score, _, location = cv2.minMaxLoc(score_map)
        matched = Region(
            image=search.image[
                location[1] : location[1] + height,
                location[0] : location[0] + width,
            ],
            left=search.left + location[0],
            top=search.top + location[1],
        )
        candidate = TemplateMatch(float(score), matched)
        if best is None or candidate.score > best.score:
            best = candidate

    return best


def annotate(
    frame: np.ndarray,
    lift_region: Region,
    bait_region: Region,
    green: float,
    cast_score: float,
    empty_score: float,
    status: str,
) -> np.ndarray:
    output = frame.copy()
    for region, color in ((lift_region, (0, 255, 255)), (bait_region, (255, 180, 0))):
        height, width = region.image.shape[:2]
        cv2.rectangle(
            output,
            (region.left, region.top),
            (region.left + width, region.top + height),
            color,
            2,
        )
    lines = (
        f"state: {status}",
        f"green: {green:.3f} / {cfg.GREEN_PIXEL_RATIO:.3f}",
        f"cast: {cast_score:.3f} / {cfg.CAST_TEMPLATE_THRESHOLD:.3f}",
        f"empty: {empty_score:.3f} / {cfg.EMPTY_BAIT_THRESHOLD:.3f}",
        "Q quit | P pause",
    )
    for index, line in enumerate(lines):
        cv2.putText(
            output,
            line,
            (12, 28 + index * 27),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    return output
