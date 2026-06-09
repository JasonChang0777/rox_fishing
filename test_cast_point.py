import json
import tempfile
import unittest
from pathlib import Path

from cast_point import load_cast_point


class CastPointTests(unittest.TestCase):
    def test_load_cast_point(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cast_point.json"
            path.write_text(
                json.dumps({"x_ratio": 0.75, "y_ratio": 0.80}),
                encoding="utf-8",
            )
            self.assertEqual(load_cast_point(path), (0.75, 0.80))


if __name__ == "__main__":
    unittest.main()
