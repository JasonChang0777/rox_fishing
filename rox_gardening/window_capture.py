from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import logging
import time

import mss
import numpy as np

import config as cfg


logger = logging.getLogger(__name__)
user32 = ctypes.windll.user32

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    user32.SetProcessDPIAware()

INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


@dataclass(frozen=True)
class ClientBounds:
    left: int
    top: int
    width: int
    height: int


def _normalized_title(value: str) -> str:
    return value.casefold().replace("ö", "o")


def find_window(title_keywords: tuple[str, ...]) -> tuple[int, str]:
    matches: list[tuple[int, str]] = []
    keywords = tuple(_normalized_title(item) for item in title_keywords)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value
        normalized = _normalized_title(title)
        if any(keyword in normalized for keyword in keywords):
            matches.append((hwnd, title))
        return True

    user32.EnumWindows(callback, 0)
    if not matches:
        raise RuntimeError("找不到 ROX 視窗，請先啟動遊戲並保持視窗可見。")
    return min(matches, key=lambda item: len(item[1]))


def get_client_bounds(hwnd: int) -> ClientBounds:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError()
    point = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        raise ctypes.WinError()
    return ClientBounds(
        point.x,
        point.y,
        rect.right - rect.left,
        rect.bottom - rect.top,
    )


def activate_window(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)
    if user32.GetForegroundWindow() != hwnd:
        # Windows normally blocks background processes from stealing focus.
        # Tapping Alt temporarily permits SetForegroundWindow without clicking.
        user32.keybd_event(VK_MENU, 0, 0, 0)
        try:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(cfg.FOREGROUND_SETTLE_SECONDS)


def is_key_down(virtual_key: int) -> bool:
    return bool(user32.GetAsyncKeyState(virtual_key) & 0x8000)


def capture_window(hwnd: int, mode: str = "screen") -> np.ndarray:
    if mode != "screen":
        raise ValueError(f"不支援的 CAPTURE_MODE: {mode}")
    bounds = get_client_bounds(hwnd)
    if bounds.width <= 0 or bounds.height <= 0:
        raise RuntimeError("遊戲客戶區大小無效，視窗可能已最小化。")
    with mss.mss() as sct:
        shot = sct.grab(
            {
                "left": bounds.left,
                "top": bounds.top,
                "width": bounds.width,
                "height": bounds.height,
            }
        )
    return np.ascontiguousarray(np.asarray(shot)[:, :, :3])


def ratio_point(
    size: tuple[int, int],
    point: tuple[float, float],
) -> tuple[int, int]:
    width, height = size
    return round(width * point[0]), round(height * point[1])


def click_client(hwnd: int, point: tuple[int, int], mode: str) -> None:
    if mode != "sendinput":
        raise ValueError(f"不支援的 CLICK_MODE: {mode}")

    bounds = get_client_bounds(hwnd)
    activate_window(hwnd)

    screen_x = bounds.left + point[0]
    screen_y = bounds.top + point[1]
    virtual_left = user32.GetSystemMetrics(76)
    virtual_top = user32.GetSystemMetrics(77)
    virtual_width = user32.GetSystemMetrics(78)
    virtual_height = user32.GetSystemMetrics(79)
    absolute_x = round(
        (screen_x - virtual_left) * 65535 / max(1, virtual_width - 1)
    )
    absolute_y = round(
        (screen_y - virtual_top) * 65535 / max(1, virtual_height - 1)
    )

    def send(flags: int) -> None:
        item = INPUT(
            type=INPUT_MOUSE,
            union=INPUTUNION(
                mi=MOUSEINPUT(
                    dx=absolute_x,
                    dy=absolute_y,
                    mouseData=0,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=None,
                )
            ),
        )
        sent = user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT))
        if sent != 1:
            raise ctypes.WinError()

    logger.info("點擊 client=(%s, %s)", point[0], point[1])
    send(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
    time.sleep(cfg.MOUSE_MOVE_SETTLE_SECONDS)
    send(MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
    time.sleep(cfg.MOUSE_PRESS_SECONDS)
    send(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
