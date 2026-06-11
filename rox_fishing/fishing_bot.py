from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import time
from enum import Enum, auto

import cv2

import config as cfg
from cast_point import load_cast_point, resolve_cast_point
from vision import (
    bait_foreground_similarity,
    bite_change_ratio,
    classify_bait_scores,
    crop_local_ratio,
    crop_ratio,
    green_ratio,
    infinity_symbol_similarity,
    load_template,
    locate_template,
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


def locate_bait_panel(frame, template):
    match = locate_template(
        frame,
        template,
        cfg.BAIT_PANEL_SEARCH_ROI,
        cfg.BAIT_PANEL_TEMPLATE_SCALES,
    )
    if match is None or match.score < cfg.BAIT_PANEL_MATCH_THRESHOLD:
        return None
    return match


def region_ratio(frame, region) -> tuple[float, float, float, float]:
    frame_height, frame_width = frame.shape[:2]
    region_height, region_width = region.image.shape[:2]
    return (
        region.left / frame_width,
        region.top / frame_height,
        (region.left + region_width) / frame_width,
        (region.top + region_height) / frame_height,
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
        cast_ratio.x_ratio,
        cast_ratio.y_ratio,
    )
    initial_bounds = get_client_bounds(hwnd)
    logger.info(
        "Client size: %sx%s",
        initial_bounds.width,
        initial_bounds.height,
    )
    if cast_ratio.bottom_offset is None:
        logger.warning(
            "Legacy cast calibration detected. It still works, but run "
            "'python calibrate.py point --delay 5' once to improve "
            "portability across window heights."
        )
    else:
        logger.info(
            "Cast anchor: bottom=%spx, reference=%sx%s",
            cast_ratio.bottom_offset,
            cast_ratio.reference_width,
            cast_ratio.reference_height,
        )
        if cast_ratio.reference_width and cast_ratio.reference_height:
            old_aspect = (
                cast_ratio.reference_width / cast_ratio.reference_height
            )
            new_aspect = initial_bounds.width / initial_bounds.height
            if abs(new_aspect / old_aspect - 1.0) > 0.15:
                logger.warning(
                    "Window aspect ratio differs significantly from "
                    "calibration (%.3f -> %.3f). Verify the first cast.",
                    old_aspect,
                    new_aspect,
                )
    button_size = max(
        80,
        round(
            min(initial_bounds.width, initial_bounds.height)
            * cfg.GREEN_BUTTON_SIZE_RATIO
        ),
    )
    logger.info("Fast green ROI: %sx%s", button_size, button_size)

    startup_frame = capture_window(hwnd, cfg.CAPTURE_MODE)
    bait_match = locate_bait_panel(startup_frame, empty_template)
    if bait_match is None:
        bait_panel_roi = cfg.BAIT_ICON_ROI
        logger.warning(
            "Dynamic bait panel location failed; using fallback ROI=%s",
            bait_panel_roi,
        )
    else:
        bait_panel_roi = region_ratio(startup_frame, bait_match.region)
        logger.info(
            "Dynamic bait panel: score=%.3f roi=(%.4f, %.4f, %.4f, %.4f) "
            "size=%sx%s",
            bait_match.score,
            *bait_panel_roi,
            bait_match.region.image.shape[1],
            bait_match.region.image.shape[0],
        )
        save_target(
            startup_frame,
            bait_match.region,
            "bait_panel_target.png",
        )

    state = BotState.CHECKING_BAIT
    previous_state = state
    last_action = 0.0
    last_diagnostic = 0.0
    green_hits = 0
    green_peak = 0.0
    bite_baseline = None
    empty_hits = 0
    bait_present_hits = 0
    unknown_bait_hits = 0

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
                bite_change = bite_change_ratio(lift_image, bite_baseline)
                green_hits = (
                    green_hits + 1
                    if bite_change >= cfg.BITE_CHANGE_RATIO
                    else 0
                )
                if bite_change > green_peak:
                    green_peak = bite_change
                    if cfg.SAVE_DEBUG_FRAMES:
                        cv2.imwrite(
                            str(cfg.DEBUG_DIR / "green_peak.png"),
                            lift_image,
                        )

                if now - last_diagnostic >= cfg.DIAGNOSTIC_INTERVAL_SECONDS:
                    logger.info(
                        "Detect: state=%s bite=%.3f green=%.3f "
                        "baseline=%s button_center=%s",
                        state.name,
                        bite_change,
                        green,
                        bite_baseline is not None,
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
                    bite_baseline = None
                    state = BotState.WAITING_FOR_RESULT
                    logger.info(
                        "Lift click: bite=%.3f green=%.3f, client=%s",
                        bite_change,
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

            if state == BotState.WAITING_FOR_RESULT:
                if now - last_diagnostic >= cfg.DIAGNOSTIC_INTERVAL_SECONDS:
                    logger.info("Detect: state=%s", state.name)
                    last_diagnostic = now
                if now - last_action >= cfg.RESULT_WAIT_SECONDS:
                    empty_hits = 0
                    bait_present_hits = 0
                    state = BotState.CHECKING_BAIT
                    logger.info(
                        "State: %s -> %s",
                        previous_state.name,
                        state.name,
                    )
                    previous_state = state
                time.sleep(cfg.POLL_INTERVAL_SECONDS)
                continue

            if state == BotState.CASTING:
                bite_baseline = capture_client_region(
                    hwnd,
                    cast_point,
                    (button_size, button_size),
                )
                if cfg.SAVE_DEBUG_FRAMES:
                    cv2.imwrite(
                        str(cfg.DEBUG_DIR / "bite_baseline.png"),
                        bite_baseline,
                    )
                click_client(hwnd, cast_point, cfg.CLICK_MODE)
                last_action = now
                state = BotState.WAITING_FOR_BITE
                green_hits = 0
                green_peak = 0.0
                logger.info(
                    "Cast click: client=%s, pre-cast baseline captured",
                    cast_point,
                )
                logger.info(
                    "State: %s -> %s",
                    previous_state.name,
                    state.name,
                )
                previous_state = state
                time.sleep(cfg.POLL_INTERVAL_SECONDS)
                continue

            # Bait is checked only here, immediately before entering CASTING.
            frame = capture_window(hwnd, cfg.CAPTURE_MODE)

            bait_region = crop_ratio(frame, bait_panel_roi)
            bait_icon = crop_local_ratio(
                bait_region.image,
                cfg.EMPTY_BAIT_ICON_CROP,
            )
            worm_score = bait_foreground_similarity(
                bait_icon,
                empty_icon_template,
            )
            infinity_score = infinity_symbol_similarity(
                bait_icon,
                empty_icon_template,
            )
            bait_kind = classify_bait_scores(worm_score, infinity_score)
            empty_hits = (
                empty_hits + 1 if bait_kind == "starter" else 0
            )
            bait_present_hits = (
                bait_present_hits + 1 if bait_kind == "limited" else 0
            )
            if bait_kind == "unknown":
                empty_hits = 0
                bait_present_hits = 0
                unknown_bait_hits += 1
            else:
                unknown_bait_hits = 0

            if unknown_bait_hits >= cfg.BAIT_RELOCATE_UNKNOWN_FRAMES:
                relocated = locate_bait_panel(frame, empty_template)
                unknown_bait_hits = 0
                if relocated is not None:
                    bait_panel_roi = region_ratio(frame, relocated.region)
                    logger.info(
                        "Bait panel relocated: score=%.3f "
                        "roi=(%.4f, %.4f, %.4f, %.4f)",
                        relocated.score,
                        *bait_panel_roi,
                    )
                    save_target(
                        frame,
                        relocated.region,
                        "bait_panel_target.png",
                    )
                    continue
                logger.warning(
                    "Bait panel relocation failed; waiting for a clear frame."
                )

            if now - last_diagnostic >= cfg.DIAGNOSTIC_INTERVAL_SECONDS:
                logger.info(
                    f"Detect: state={state.name} button_center={cast_point} "
                    f"worm={worm_score:.3f} infinity={infinity_score:.3f} "
                    f"bait={bait_kind}"
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
                    "Limited bait confirmed: worm=%.3f infinity=%.3f",
                    worm_score,
                    infinity_score,
                )

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
