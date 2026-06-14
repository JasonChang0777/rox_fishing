import unittest
from unittest.mock import patch

import window_capture
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

    @patch.object(window_capture, "_send_mouse_input")
    def test_release_mouse_buttons_sends_left_up(self, send_mouse) -> None:
        window_capture.release_mouse_buttons()

        send_mouse.assert_called_once_with(window_capture.MOUSEEVENTF_LEFTUP)

    @patch.object(window_capture.time, "sleep")
    @patch.object(window_capture, "activate_window")
    @patch.object(window_capture, "_send_mouse_input")
    @patch.object(window_capture.user32, "PostMessageW", return_value=1)
    def test_background_click_does_not_take_mouse_or_focus(
        self,
        post_message,
        send_mouse,
        activate,
        _sleep,
    ) -> None:
        window_capture.click_client(101, (25, 50), "background")

        packed = (50 << 16) | 25
        self.assertEqual(
            post_message.call_args_list,
            [
                unittest.mock.call(
                    101,
                    window_capture.WM_LBUTTONDOWN,
                    window_capture.MK_LBUTTON,
                    packed,
                ),
                unittest.mock.call(
                    101,
                    window_capture.WM_LBUTTONUP,
                    0,
                    packed,
                ),
            ],
        )
        activate.assert_not_called()
        send_mouse.assert_not_called()

    @patch.object(window_capture.time, "sleep", side_effect=RuntimeError("stop"))
    @patch.object(window_capture.user32, "PostMessageW", return_value=1)
    def test_background_click_posts_button_up_when_interrupted(
        self,
        post_message,
        _sleep,
    ) -> None:
        with self.assertRaisesRegex(RuntimeError, "stop"):
            window_capture.click_client(101, (25, 50), "background")

        self.assertEqual(
            post_message.call_args_list[-1].args[1],
            window_capture.WM_LBUTTONUP,
        )

    @patch.object(
        window_capture.time,
        "sleep",
        side_effect=[None, RuntimeError("stop"), None],
    )
    @patch.object(window_capture.user32, "SetCursorPos", return_value=1)
    @patch.object(window_capture.user32, "GetCursorPos", return_value=1)
    @patch.object(window_capture, "activate_window")
    @patch.object(
        window_capture,
        "get_client_bounds",
        return_value=window_capture.ClientBounds(0, 0, 1280, 720),
    )
    @patch.object(window_capture, "_send_mouse_input")
    def test_click_releases_left_button_when_interrupted(
        self,
        send_mouse,
        _bounds,
        _activate,
        _get_cursor,
        set_cursor,
        _sleep,
    ) -> None:
        original_x = 777
        original_y = 333

        def save_cursor(point_pointer) -> int:
            point = point_pointer._obj
            point.x = original_x
            point.y = original_y
            return 1

        _get_cursor.side_effect = save_cursor
        with self.assertRaisesRegex(RuntimeError, "stop"):
            window_capture.click_client(101, (100, 200), "sendinput")

        flags = [call.args[0] for call in send_mouse.call_args_list]
        self.assertEqual(
            flags[-1] & window_capture.MOUSEEVENTF_LEFTUP,
            window_capture.MOUSEEVENTF_LEFTUP,
        )
        set_cursor.assert_called_once_with(original_x, original_y)


if __name__ == "__main__":
    unittest.main()
