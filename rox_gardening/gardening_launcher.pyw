from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import config as cfg
from window_capture import (
    WindowInfo,
    find_windows,
    get_client_bounds,
    release_mouse_buttons,
)


PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parent
BOT_PATHS = {
    "園藝": PROJECT_DIR / "gardening_bot.py",
    "釣魚": ROOT_DIR / "rox_fishing" / "fishing_bot.py",
}
CREATE_NEW_CONSOLE = 0x00000010
SW_SHOWNORMAL = 1


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin() -> bool:
    executable = str(Path(sys.executable).resolve())
    script = str(Path(__file__).resolve())
    parameters = subprocess.list2cmdline([script])
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        parameters,
        str(PROJECT_DIR),
        SW_SHOWNORMAL,
    )
    return result > 32


def console_python(executable: str | Path = sys.executable) -> Path:
    path = Path(executable)
    if path.name.casefold() == "pythonw.exe":
        candidate = path.with_name("python.exe")
        if candidate.exists():
            return candidate
    return path


def bot_command(
    bot_name: str,
    hwnd: int,
    executable: str | Path = sys.executable,
) -> list[str]:
    try:
        bot_path = BOT_PATHS[bot_name]
    except KeyError as exc:
        raise ValueError(f"Unknown bot: {bot_name}") from exc
    return [
        str(console_python(executable)),
        str(bot_path),
        "--hwnd",
        str(hwnd),
    ]


def normalized_window_title(title: str) -> str:
    return title.strip().casefold().replace("ö", "o")


def is_game_window(window: WindowInfo) -> bool:
    return normalized_window_title(window.title) == "rox"


def describe_window(window: WindowInfo) -> tuple[str, str, str, str, str]:
    bounds = get_client_bounds(window.hwnd)
    size = f"{bounds.width}x{bounds.height}"
    status = "可執行" if bounds.width > 0 and bounds.height > 0 else "已最小化"
    return str(window.hwnd), str(window.process_id), size, status, window.title


class GardeningLauncher:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.windows: dict[str, WindowInfo] = {}
        self.bot_process: subprocess.Popen[str] | None = None
        self.active_bot_name: str | None = None

        root.title("ROX Bot 啟動器")
        root.geometry("820x430")
        root.minsize(680, 360)
        root.protocol("WM_DELETE_WINDOW", self.close)

        heading = ttk.Label(
            root,
            text="選擇要執行 Bot 的 ROX 遊戲視窗",
            font=("", 14, "bold"),
        )
        heading.pack(anchor="w", padx=16, pady=(16, 8))

        columns = ("hwnd", "pid", "size", "status", "title")
        self.tree = ttk.Treeview(
            root,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headings = {
            "hwnd": "視窗 Handle",
            "pid": "PID",
            "size": "大小",
            "status": "狀態",
            "title": "視窗標題",
        }
        widths = {
            "hwnd": 110,
            "pid": 80,
            "size": 90,
            "status": 90,
            "title": 400,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                minwidth=60,
                stretch=column == "title",
            )
        self.tree.pack(fill="both", expand=True, padx=16)

        controls = ttk.Frame(root)
        controls.pack(fill="x", padx=16, pady=12)
        ttk.Button(
            controls,
            text="重新整理",
            command=self.refresh_windows,
        ).pack(side="left")
        self.gardening_button = ttk.Button(
            controls,
            text="啟動園藝",
            command=lambda: self.start_bot("園藝"),
        )
        self.gardening_button.pack(side="left", padx=(8, 0))
        self.fishing_button = ttk.Button(
            controls,
            text="啟動釣魚",
            command=lambda: self.start_bot("釣魚"),
        )
        self.fishing_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(
            controls,
            text="停止 Bot",
            command=self.stop_bot,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        self.status_text = tk.StringVar(value="正在搜尋 ROX 視窗...")
        ttk.Label(root, textvariable=self.status_text).pack(
            anchor="w",
            padx=16,
            pady=(0, 12),
        )

        self.refresh_windows()
        self.poll_process()

    def refresh_windows(self) -> None:
        selected_hwnd = None
        selected = self.tree.selection()
        if selected:
            selected_window = self.windows.get(selected[0])
            if selected_window is not None:
                selected_hwnd = selected_window.hwnd

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.windows.clear()

        matches = [
            window
            for window in find_windows(cfg.WINDOW_TITLE_KEYWORDS)
            if is_game_window(window)
        ]
        for index, window in enumerate(matches):
            item_id = f"window-{index}"
            try:
                values = describe_window(window)
            except OSError:
                continue
            self.windows[item_id] = window
            self.tree.insert("", "end", iid=item_id, values=values)
            if window.hwnd == selected_hwnd:
                self.tree.selection_set(item_id)

        if matches:
            if not self.tree.selection() and self.tree.get_children():
                first = self.tree.get_children()[0]
                self.tree.selection_set(first)
                self.tree.focus(first)
            self.status_text.set(
                f"找到 {len(self.windows)} 個 ROX 遊戲視窗。"
                "選擇後按「啟動園藝」或「啟動釣魚」。"
            )
        else:
            self.status_text.set("找不到 ROX 遊戲視窗，請先開啟遊戲。")

    def selected_window(self) -> WindowInfo | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return self.windows.get(selected[0])

    def start_bot(self, bot_name: str) -> None:
        if self.bot_process is not None and self.bot_process.poll() is None:
            messagebox.showinfo(
                "ROX Bot",
                f"{self.active_bot_name or 'Bot'} 已經在執行中。",
            )
            return

        window = self.selected_window()
        if window is None:
            messagebox.showwarning("ROX Bot", "請先選擇一個 ROX 遊戲視窗。")
            return

        command = bot_command(bot_name, window.hwnd)
        bot_path = BOT_PATHS[bot_name]
        try:
            self.bot_process = subprocess.Popen(
                command,
                cwd=bot_path.parent,
                creationflags=CREATE_NEW_CONSOLE,
            )
        except OSError as exc:
            messagebox.showerror("啟動失敗", str(exc))
            return

        self.active_bot_name = bot_name
        self.gardening_button.configure(state="disabled")
        self.fishing_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_text.set(
            f"{bot_name} Bot 執行中：{window.title} (handle={window.hwnd})"
        )

    def stop_bot(self) -> None:
        if self.bot_process is None or self.bot_process.poll() is not None:
            self.mark_stopped()
            return
        release_mouse_buttons()
        self.bot_process.terminate()
        self.status_text.set(f"正在停止{self.active_bot_name or ''} Bot...")

    def mark_stopped(self) -> None:
        stopped_name = self.active_bot_name
        self.bot_process = None
        self.active_bot_name = None
        self.gardening_button.configure(state="normal")
        self.fishing_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_text.set(f"{stopped_name or 'Bot'} 已停止。")

    def poll_process(self) -> None:
        if self.bot_process is not None and self.bot_process.poll() is not None:
            self.mark_stopped()
        self.root.after(500, self.poll_process)

    def close(self) -> None:
        if self.bot_process is not None and self.bot_process.poll() is None:
            leave_running = messagebox.askyesno(
                "關閉啟動器",
                f"{self.active_bot_name or 'Bot'} 仍在執行。"
                "要讓 Bot 繼續執行並關閉啟動器嗎？",
            )
            if not leave_running:
                return
        self.root.destroy()


def main() -> None:
    if not is_admin():
        if relaunch_as_admin():
            return
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "ROX Bot 啟動器",
            "需要系統管理員權限才能對同樣以管理員權限執行的遊戲送出點擊。",
        )
        root.destroy()
        return

    root = tk.Tk()
    GardeningLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
