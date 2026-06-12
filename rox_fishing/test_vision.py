import unittest

import cv2
import numpy as np

import config as cfg
from vision import (
    bait_foreground_mask,
    bait_foreground_similarity,
    bite_change_ratio,
    classify_bait_scores,
    crop_around,
    crop_local_ratio,
    crop_ratio,
    green_ratio,
    image_similarity,
    infinity_hole_geometry,
    infinity_symbol_similarity,
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

    def test_gray_circle_does_not_cross_green_threshold(self) -> None:
        image = np.full((200, 200, 3), 150, dtype=np.uint8)
        self.assertLess(green_ratio(image), cfg.GREEN_PIXEL_RATIO)

    def test_bite_change_ignores_static_green_background(self) -> None:
        baseline = np.full((160, 160, 3), (40, 110, 45), dtype=np.uint8)
        cv2.circle(baseline, (80, 80), 55, (135, 135, 135), -1)
        self.assertEqual(bite_change_ratio(baseline.copy(), baseline), 0.0)

    def test_bite_change_detects_green_button_on_green_background(self) -> None:
        baseline = np.full((160, 160, 3), (40, 110, 45), dtype=np.uint8)
        cv2.circle(baseline, (80, 80), 55, (135, 135, 135), -1)
        active = baseline.copy()
        cv2.circle(active, (80, 80), 48, (65, 220, 145), -1)
        self.assertGreater(
            bite_change_ratio(active, baseline),
            cfg.BITE_CHANGE_RATIO,
        )

    def test_gray_icon_change_does_not_look_like_a_bite(self) -> None:
        baseline = np.full((160, 160, 3), 80, dtype=np.uint8)
        cv2.line(baseline, (35, 125), (125, 35), (190, 190, 190), 8)
        lift_icon = np.full((160, 160, 3), 80, dtype=np.uint8)
        cv2.circle(lift_icon, (80, 80), 40, (190, 190, 190), 8)
        self.assertEqual(bite_change_ratio(lift_icon, baseline), 0.0)

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

    def test_bait_similarity_ignores_background_change(self) -> None:
        template = np.full((120, 90, 3), (70, 45, 30), dtype=np.uint8)
        cv2.ellipse(
            template,
            (42, 58),
            (18, 34),
            -25,
            20,
            320,
            (155, 190, 225),
            9,
        )
        image = np.full((120, 90, 3), (40, 105, 45), dtype=np.uint8)
        image[bait_foreground_mask(template) > 0] = template[
            bait_foreground_mask(template) > 0
        ]
        self.assertGreater(
            bait_foreground_similarity(image, template),
            cfg.EMPTY_BAIT_WORM_THRESHOLD,
        )

    def test_different_bait_shape_has_low_similarity(self) -> None:
        template = np.zeros((120, 90, 3), dtype=np.uint8)
        cv2.ellipse(
            template,
            (42, 58),
            (18, 34),
            -25,
            20,
            320,
            (155, 190, 225),
            9,
        )
        other = np.zeros_like(template)
        cv2.line(other, (20, 95), (70, 20), (155, 190, 225), 7)
        self.assertLess(
            bait_foreground_similarity(other, template),
            cfg.EMPTY_BAIT_WORM_THRESHOLD,
        )

    def test_infinity_symbol_ignores_background_change(self) -> None:
        template = np.full((120, 90, 3), (55, 35, 25), dtype=np.uint8)
        image = np.full((120, 90, 3), (35, 90, 45), dtype=np.uint8)
        for target in (template, image):
            cv2.circle(target, (67, 98), 5, (245, 245, 245), 2)
            cv2.circle(target, (78, 98), 5, (245, 245, 245), 2)
            cv2.line(target, (70, 95), (75, 101), (245, 245, 245), 2)
            cv2.line(target, (70, 101), (75, 95), (245, 245, 245), 2)
        self.assertGreater(
            infinity_symbol_similarity(image, template),
            cfg.EMPTY_BAIT_INFINITY_THRESHOLD,
        )

    def test_missing_infinity_symbol_has_zero_similarity(self) -> None:
        template = np.zeros((120, 90, 3), dtype=np.uint8)
        cv2.circle(template, (67, 98), 5, (245, 245, 245), 2)
        cv2.circle(template, (78, 98), 5, (245, 245, 245), 2)
        image = np.zeros_like(template)
        self.assertEqual(infinity_symbol_similarity(image, template), 0.0)

    def test_finite_count_does_not_match_infinity_structure(self) -> None:
        template = np.zeros((120, 90, 3), dtype=np.uint8)
        cv2.circle(template, (67, 88), 5, (245, 245, 245), 2)
        cv2.circle(template, (76, 88), 5, (245, 245, 245), 2)
        finite = np.zeros_like(template)
        cv2.putText(
            finite,
            "169",
            (54, 96),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (245, 245, 245),
            1,
            cv2.LINE_AA,
        )
        self.assertLess(
            infinity_symbol_similarity(finite, template),
            cfg.LIMITED_BAIT_INFINITY_MAX,
        )

    def test_infinity_geometry_requires_two_loops(self) -> None:
        mask = np.zeros((30, 40), dtype=np.uint8)
        cv2.circle(mask, (14, 15), 5, 255, 2)
        cv2.circle(mask, (23, 15), 5, 255, 2)
        self.assertIsNotNone(infinity_hole_geometry(mask))

    def test_bait_score_classification_requires_clear_evidence(self) -> None:
        self.assertEqual(classify_bait_scores(0.70, 0.85), "starter")
        self.assertEqual(classify_bait_scores(0.10, 0.20), "limited")
        self.assertEqual(classify_bait_scores(0.417, 0.00), "limited")
        self.assertEqual(classify_bait_scores(0.00, 0.719), "unknown")
        self.assertEqual(classify_bait_scores(0.60, 0.40), "limited")
        self.assertEqual(classify_bait_scores(0.70, 0.40), "unknown")

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

    def test_locate_template_handles_scaled_ui(self) -> None:
        template = np.zeros((40, 80, 3), dtype=np.uint8)
        cv2.circle(template, (22, 20), 15, (210, 210, 210), 3)
        cv2.circle(template, (60, 20), 15, (210, 210, 210), 3)
        cv2.line(template, (48, 30), (70, 8), (255, 255, 255), 3)
        scaled = cv2.resize(template, (120, 60))
        frame = np.zeros((240, 360, 3), dtype=np.uint8)
        frame[165:225, 205:325] = scaled

        match = locate_template(
            frame,
            template,
            (0.4, 0.6, 1.0, 1.0),
            (1.0, 1.25, 1.5),
        )

        self.assertIsNotNone(match)
        assert match is not None
        self.assertGreater(match.score, 0.99)
        self.assertEqual(match.region.image.shape, (60, 120, 3))


if __name__ == "__main__":
    unittest.main()
