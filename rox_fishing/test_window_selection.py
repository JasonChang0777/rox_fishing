import unittest

from window_capture import WindowInfo, ratio_point, select_window


class WindowSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.windows = [
            WindowInfo(100, "RöX", 10),
            WindowInfo(200, "RöX", 20),
        ]

    def test_selects_single_window_by_default(self) -> None:
        self.assertEqual(select_window(self.windows[:1]).hwnd, 100)

    def test_requires_selection_when_multiple_windows_exist(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "--list-windows"):
            select_window(self.windows)

    def test_selects_window_by_index(self) -> None:
        self.assertEqual(
            select_window(self.windows, window_index=2).hwnd,
            200,
        )

    def test_selects_window_by_handle(self) -> None:
        self.assertEqual(
            select_window(self.windows, hwnd=200).process_id,
            20,
        )

    def test_rejects_invalid_index(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "1 到 2"):
            select_window(self.windows, window_index=3)

    def test_fixed_cast_ratio_scales_with_client_size(self) -> None:
        self.assertEqual(
            ratio_point((1280, 720), (0.84921875, 0.7333333333333333)),
            (1087, 528),
        )


if __name__ == "__main__":
    unittest.main()
