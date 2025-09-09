import time
import numpy as np


def ultra_fast_capture(self):
    """Fast screen capture using `self.sct` and `self.monitor`.

    Updates FPS counters stored on `self`.
    """
    img = self.sct.grab(self.monitor)
    frame = np.frombuffer(img.rgb, dtype=np.uint8).reshape(img.height, img.width, 3)

    # Update FPS
    self.fps_counter += 1
    current_time = time.time()
    if current_time - self.fps_start_time >= 1.0:
        self.current_fps = self.fps_counter
        self.fps_counter = 0
        self.fps_start_time = current_time

    return frame

