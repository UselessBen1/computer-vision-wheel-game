import cv2
import numpy as np


def classify_region_state(self, region):
    """Classify region as GRAY, WHITE or OTHER with high sensitivity.

    In fast_gray_mode, GRAY is triggered by the presence of as little as
    one qualifying pixel (configurable). This makes transitions fire on
    first appearance of gray, reducing timing latency on fast patterns.
    """
    if region.size == 0:
        return "UNKNOWN"

    hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # Compute gray/white masks
    gray_mask = (s <= self.gray_s_thresh) & (v >= self.gray_v_min) & (v <= self.gray_v_max)
    white_mask = (s <= self.white_s_thresh) & (v >= self.white_v_min)

    total_px = int(region.shape[0] * region.shape[1])
    gray_count = int(np.count_nonzero(gray_mask))
    white_count = int(np.count_nonzero(white_mask))

    # High-sensitivity GRAY: any gray pixel (or minimal threshold)
    if getattr(self, 'fast_gray_mode', True):
        min_gray_by_frac = int(total_px * max(0.0, float(getattr(self, 'gray_min_fraction', 0.0))))
        min_gray = max(int(getattr(self, 'gray_min_pixels', 1)), min_gray_by_frac)
        if gray_count >= max(1, min_gray):
            return "GRAY"
    else:
        # Fallback (not in use by default): require gray to be dominant
        if gray_count > white_count and gray_count > total_px * 0.05:
            return "GRAY"

    # Otherwise classify WHITE if sufficiently present
    if white_count >= max(int(total_px * 0.05), 1):
        return "WHITE"

    return "OTHER"

