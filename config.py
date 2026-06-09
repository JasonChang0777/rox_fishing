from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = PROJECT_DIR / "templates"
DEBUG_DIR = PROJECT_DIR / "debug"
LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "fishing_bot.log"
CAST_POINT_FILE = PROJECT_DIR / "cast_point.json"

# The game title may use either a plain O or an umlaut depending on the client.
WINDOW_TITLE_KEYWORDS = ("ROX", "RÖX")

# Regions are (left, top, right, bottom) ratios of the game client area.
# The fishing button moves when the game changes its UI layout, so search a
# broad lower-right area instead of clicking the center of a fixed ROI.
LIFT_BUTTON_ROI = (0.42, 0.42, 1.00, 1.00)
BAIT_ICON_ROI = (0.65, 0.84, 0.75, 0.99)

EMPTY_BAIT_TEMPLATE = TEMPLATE_DIR / "empty_bait.png"

# OpenCV HSV ranges. Hue is 0-179.
GREEN_HSV_LOWER = (20, 55, 80)
GREEN_HSV_UPPER = (92, 255, 255)
GREEN_PIXEL_RATIO = 0.075
GREEN_REQUIRED_FRAMES = 1
GREEN_BUTTON_SIZE_RATIO = 0.20

EMPTY_BAIT_THRESHOLD = 0.76
EMPTY_BAIT_REQUIRED_FRAMES = 5
BAIT_PRESENT_REQUIRED_FRAMES = 5
# The calibrated bait image contains the starter bait on the left and the
# fishing rod on the right. Compare only the starter bait icon.
EMPTY_BAIT_ICON_CROP = (0.00, 0.00, 0.56, 0.95)

POLL_INTERVAL_SECONDS = 0.010
DIAGNOSTIC_INTERVAL_SECONDS = 1.0
CAST_COOLDOWN_SECONDS = 2.0
LIFT_COOLDOWN_SECONDS = 1.5
RESULT_WAIT_SECONDS = 4.0

LIFT_CLICK_COUNT = 3
CLICK_INTERVAL_SECONDS = 0.010
FOREGROUND_SETTLE_SECONDS = 0.020
MOUSE_MOVE_SETTLE_SECONDS = 0.010
MOUSE_PRESS_SECONDS = 0.020

# Reliable mode: use Windows SendInput. This briefly uses the real cursor and
# requires ROX and this process to run at the same privilege level.
CLICK_MODE = "sendinput"
FOCUS_MESSAGE_SETTLE_SECONDS = 0.050

# ROX uses DirectX and commonly returns a black frame through PrintWindow.
# Screen capture requires the game to remain visible and not be minimized.
CAPTURE_MODE = "screen"

# Screen capture must not be covered by the OpenCV preview window.
SHOW_PREVIEW = False
SAVE_DEBUG_FRAMES = True
