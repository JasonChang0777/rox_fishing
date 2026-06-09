import unittest

import cv2
import numpy as np

import config as cfg
from vision import (
    crop_around,
    crop_cast_template,
    crop_local_ratio,
    crop_ratio,
    green_ratio,
    image_similarity,
    locate_green_button,
    locate_template,
)


class VisionTests(unittest.TestCase):
    def test_crop_ratio_returns_expected_area(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        region = crop_ratio(frame, (0.25, 0.20, 0.75, 0.80))
        self.assertEqual(region.image.shape, (60, 100, 3))
        self.assertEqual(region.center, (100, 50))

    def test_green_circle_crosses_threshold(self) -> None:
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.circle(image, (100, 100), 60, (60, 220, 160), -1)
        self.assertGreater(green_ratio(image), cfg.GREEN_PIXEL_RATIO)

    def test_crop_around_uses_requested_center(self) -> None:
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        region = crop_around(frame, (150, 70), (40, 20))
        self.assertEqual(region.image.shape, (20, 40, 3))
        self.assertEqual(region.center, (150, 70))

    def test_crop_local_ratio(self) -> None:
        image = np.zeros((100, 200, 3), dtype=np.uint8)
        cropped = crop_local_ratio(image, (0.0, 0.0, 0.5, 0.8))
        self.assertEqual(cropped.shape, (80, 100, 3))

    def test_crop_cast_template_removes_outer_background(self) -> None:
        template = np.zeros((100, 200, 3), dtype=np.uint8)
        cropped = crop_cast_template(template)
        self.assertEqual(cropped.shape, (53, 100, 3))

    def test_gray_circle_does_not_cross_green_threshold(self) -> None:
        image = np.full((200, 200, 3), 150, dtype=np.uint8)
        self.assertLess(green_ratio(image), cfg.GREEN_PIXEL_RATIO)

    def test_locate_green_button_returns_circle_center(self) -> None:
        frame = np.zeros((200, 300, 3), dtype=np.uint8)
        cv2.circle(frame, (240, 150), 35, (60, 220, 160), -1)
        match = locate_green_button(frame, (0.5, 0.4, 1.0, 1.0))
        self.assertIsNotNone(match)
        assert match is not None
        self.assertLess(abs(match.center[0] - 240), 3)
        self.assertLess(abs(match.center[1] - 150), 3)

    def test_identical_images_have_high_similarity(self) -> None:
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        cv2.circle(image, (80, 60), 35, (255, 255, 255), 4)
        cv2.line(image, (30, 90), (130, 25), (180, 180, 180), 5)
        self.assertGreater(image_similarity(image, image.copy()), 0.99)

    def test_locate_template_returns_dynamic_center(self) -> None:
        template = np.zeros((30, 40, 3), dtype=np.uint8)
        cv2.circle(template, (20, 15), 10, (255, 255, 255), 2)
        cv2.line(template, (5, 25), (35, 4), (160, 160, 160), 3)
        frame = np.zeros((160, 240, 3), dtype=np.uint8)
        frame[90:120, 150:190] = template

        match = locate_template(frame, template, (0.4, 0.4, 1.0, 1.0), (1.0,))

        self.assertIsNotNone(match)
        assert match is not None
        self.assertGreater(match.score, 0.99)
        self.assertEqual(match.center, (170, 105))


if __name__ == "__main__":
    unittest.main()
