import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cast_point import CastPoint, load_cast_point, resolve_cast_point
from window_capture import ClientBounds


class CastPointTests(unittest.TestCase):
    def test_load_cast_point(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cast_point.json"
            path.write_text(
                json.dumps({"x_ratio": 0.75, "y_ratio": 0.80}),
                encoding="utf-8",
            )
            self.assertEqual(
                load_cast_point(path),
                CastPoint(x_ratio=0.75, y_ratio=0.80),
            )

    def test_resolve_new_point_scales_bottom_anchor_with_ui(self) -> None:
        point = CastPoint(
            x_ratio=0.85,
            y_ratio=0.74,
            bottom_offset=190,
            reference_width=1400,
            reference_height=740,
        )
        with patch(
            "cast_point.get_client_bounds",
            return_value=ClientBounds(0, 0, 1920, 1012),
        ):
            self.assertEqual(resolve_cast_point(1, point), (1632, 752))

    def test_resolve_new_point_keeps_original_calibration_position(self) -> None:
        point = CastPoint(
            x_ratio=0.8573,
            y_ratio=0.7322,
            bottom_offset=199,
            reference_width=1402,
            reference_height=743,
        )
        with patch(
            "cast_point.get_client_bounds",
            return_value=ClientBounds(0, 0, 1402, 743),
        ):
            self.assertEqual(resolve_cast_point(1, point), (1202, 544))


if __name__ == "__main__":
    unittest.main()
