from __future__ import annotations

import argparse
import time

from cast_point import load_cast_point, resolve_cast_point
from window_capture import click_client, find_window
import config as cfg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test ROX background PostMessage clicking without moving the mouse."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds to wait before sending the click (default: 3).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of background clicks to send (default: 1).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    hwnd, title = find_window(cfg.WINDOW_TITLE_KEYWORDS)
    point = resolve_cast_point(hwnd, load_cast_point())

    print(f"Window: {title} (handle={hwnd})")
    print(f"Background click target: client={point}")
    print(
        f"Sending {args.count} PostMessage click(s) in "
        f"{args.delay:.1f} seconds."
    )
    print("The mouse and foreground window should not move.")
    time.sleep(args.delay)

    click_client(
        hwnd,
        point,
        mode="background",
        count=max(1, args.count),
        interval=0.08,
    )
    print("PostMessage sent. Check whether ROX started fishing.")


if __name__ == "__main__":
    main()
