from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import time
from enum import Enum, auto

import cv2

import config as cfg
from cast_point import load_cast_point, resolve_cast_point
from vision import (
    crop_around,
    crop_local_ratio,
    crop_ratio,
    green_ratio,
    image_similarity,
    load_template,
)
from window_capture import (
    capture_client_region,
    capture_window,
    click_client,
    find_window,
    get_client_bounds,
)


logger = logging.getLogger(__name__)


class BotState(Enum):
    CHECKING_BAIT = auto()
    CASTING = auto()
    WAITING_FOR_BITE = auto()
    WAITING_FOR_RESULT = auto()
    OUT_OF_BAIT = auto()


def save_target(frame, region, name: str) -> None:
    if not cfg.SAVE_DEBUG_FRAMES:
        return
    output = frame.copy()
    height, width = region.image.shape[:2]
    cv2.rectangle(
        output,
        (region.left, region.top),
        (region.left + width, region.top + height),
        (0, 0, 255),
        3,
    )
    cv2.circle(output, region.center, 8, (0, 255, 255), -1)
    cv2.imwrite(str(cfg.DEBUG_DIR / name), output)


def configure_logging() -> None:
    cfg.LOG_DIR.mkdir(exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        cfg.LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=(console, file_handler),
        force=True,
    )


def main() -> None:
    configure_logging()
    cfg.DEBUG_DIR.mkdir(exist_ok=True)
    cast_ratio = load_cast_point()
    empty_template = load_template(cfg.EMPTY_BAIT_TEMPLATE)
    if empty_template is None:
        raise RuntimeError(
            "Missing empty_bait.png. Run: python calibrate.py empty"
        )
    empty_icon_template = crop_local_ratio(
        empty_template,
        cfg.EMPTY_BAIT_ICON_CROP,
    )

    hwnd, title = find_window(cfg.WINDOW_TITLE_KEYWORDS)
    logger.info("=== ROX Fishing Bot started ===")
    logger.info("Game window: %s (handle=%s)", title, hwnd)
    logger.info("Capture=%s, click=%s", cfg.CAPTURE_MODE, cfg.CLICK_MODE)
    logger.info(
        "Cast point ratio: x=%.4f, y=%.4f",
        cast_ratio[0],
        cast_ratio[1],
    )
    initial_bounds = get_client_bounds(hwnd)
    button_size = max(
        80,
        round(
            min(initial_bounds.width, initial_bounds.height)
            * cfg.GREEN_BUTTON_SIZE_RATIO
        ),
    )
    logger.info("Fast green ROI: %sx%s", button_size, button_size)

    state = BotState.CHECKING_BAIT
    previous_state = state
    last_action = 0.0
    last_diagnostic = 0.0
    green_hits = 0
    green_peak = 0.0
    empty_hits = 0
    bait_present_hits = 0

    try:
        while True:
            now = time.perf_counter()
            cast_point = resolve_cast_point(hwnd, cast_ratio)

            if state == BotState.WAITING_FOR_BITE:
                lift_image = capture_client_region(
                    hwnd,
                    cast_point,
                    (button_size, button_size),
                )
                green = green_ratio(lift_image)
                green_hits = (
                    green_hits + 1
                    if green >= cfg.GREEN_PIXEL_RATIO
                    else 0
                )
                if green > green_peak:
                    green_peak = green
                    if cfg.SAVE_DEBUG_FRAMES:
                        cv2.imwrite(
                            str(cfg.DEBUG_DIR / "green_peak.png"),
                            lift_image,
                        )

                if now - last_diagnostic >= cfg.DIAGNOSTIC_INTERVAL_SECONDS:
                    logger.info(
                        "Detect: state=%s green=%.3f button_center=%s",
                        state.name,
                        green,
                        cast_point,
                    )
                    last_diagnostic = now

                if (
                    green_hits >= cfg.GREEN_REQUIRED_FRAMES
                    and now - last_action >= cfg.LIFT_COOLDOWN_SECONDS
                ):
                    click_client(
                        hwnd,
                        cast_point,
                        cfg.CLICK_MODE,
                        count=cfg.LIFT_CLICK_COUNT,
                        interval=cfg.CLICK_INTERVAL_SECONDS,
                    )
                    last_action = now
                    green_hits = 0
                    green_peak = 0.0
                    state = BotState.WAITING_FOR_RESULT
                    logger.info(
                        "Lift click: green=%.3f, client=%s",
                        green,
                        cast_point,
                    )

                if state != previous_state:
                    logger.info(
                        "State: %s -> %s",
                        previous_state.name,
                        state.name,
                    )
                    previous_state = state

                time.sleep(cfg.POLL_INTERVAL_SECONDS)
                continue

            frame = capture_window(hwnd, cfg.CAPTURE_MODE)

            bait_region = crop_ratio(frame, cfg.BAIT_ICON_ROI)
            bait_icon = crop_local_ratio(
                bait_region.image,
                cfg.EMPTY_BAIT_ICON_CROP,
            )
            empty_score = image_similarity(bait_icon, empty_icon_template)
            empty_hits = (
                empty_hits + 1 if empty_score >= cfg.EMPTY_BAIT_THRESHOLD else 0
            )
            bait_present_hits = (
                bait_present_hits + 1
                if empty_score < cfg.EMPTY_BAIT_THRESHOLD
                else 0
            )

            lift_region = crop_around(
                frame,
                cast_point,
                (button_size, button_size),
            )
            green = (
                green_ratio(lift_region.image)
                if state == BotState.WAITING_FOR_BITE
                else 0.0
            )
            green_hits = (
                green_hits + 1 if green >= cfg.GREEN_PIXEL_RATIO else 0
            )
            if state == BotState.WAITING_FOR_BITE and green > green_peak:
                green_peak = green
                if cfg.SAVE_DEBUG_FRAMES:
                    cv2.imwrite(
                        str(cfg.DEBUG_DIR / "green_peak.png"),
                        lift_region.image,
                    )

            if now - last_diagnostic >= cfg.DIAGNOSTIC_INTERVAL_SECONDS:
                logger.info(
                    f"Detect: state={state.name} green={green:.3f} "
                    f"button_center={cast_point} empty={empty_score:.3f}"
                )
                last_diagnostic = now

            if empty_hits >= cfg.EMPTY_BAIT_REQUIRED_FRAMES:
                state = BotState.OUT_OF_BAIT

            elif (
                state == BotState.CHECKING_BAIT
                and bait_present_hits >= cfg.BAIT_PRESENT_REQUIRED_FRAMES
            ):
                empty_hits = 0
                bait_present_hits = 0
                state = BotState.CASTING
                logger.info(
                    "Limited bait confirmed: empty_score=%.3f",
                    empty_score,
                )

            elif state == BotState.CASTING:
                click_client(hwnd, cast_point, cfg.CLICK_MODE)
                last_action = now
                state = BotState.WAITING_FOR_BITE
                green_hits = 0
                green_peak = 0.0
                logger.info("Cast click: client=%s", cast_point)

            elif (
                state == BotState.WAITING_FOR_RESULT
                and now - last_action >= cfg.RESULT_WAIT_SECONDS
            ):
                empty_hits = 0
                bait_present_hits = 0
                state = BotState.CHECKING_BAIT

            if state != previous_state:
                logger.info("State: %s -> %s", previous_state.name, state.name)
                previous_state = state

            if state == BotState.OUT_OF_BAIT:
                if cfg.SAVE_DEBUG_FRAMES:
                    cv2.imwrite(
                        str(cfg.DEBUG_DIR / "out_of_bait.png"),
                        bait_icon,
                    )
                logger.info(
                    "Starter bait detected. Limited bait is exhausted; stopping."
                )
                break

            time.sleep(cfg.POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        cv2.destroyAllWindows()
        logger.info("=== ROX Fishing Bot stopped ===")


if __name__ == "__main__":
    main()
