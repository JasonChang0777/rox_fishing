import unittest

from window_capture import WindowInfo, select_window


class WindowSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.windows = [
            WindowInfo(101, "ROX A", 1001),
            WindowInfo(202, "ROX B", 1002),
        ]

    def test_requires_selection_when_multiple_windows_exist(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Found 2 ROX windows"):
            select_window(self.windows)

    def test_selects_window_by_index(self) -> None:
        self.assertEqual(
            select_window(self.windows, window_index=2),
            self.windows[1],
        )

    def test_selects_window_by_handle(self) -> None:
        self.assertEqual(
            select_window(self.windows, hwnd=101),
            self.windows[0],
        )

    def test_rejects_unknown_handle(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "999"):
            select_window(self.windows, hwnd=999)


if __name__ == "__main__":
    unittest.main()
