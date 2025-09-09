import time
import threading
import pyautogui


def _dynamic_press_offset(self, interval_len: float | None) -> float:
    """Dynamic press offset tuned to the target interval length.

    Returns seconds to subtract from predicted time before pressing.
    """
    if interval_len is None:
        return 0.020
    if interval_len < 0.20:
        return 0.010
    if interval_len < 0.35:
        return 0.012
    if interval_len < 0.55:
        return 0.014
    # default for slower-paced patterns
    return 0.015


def invalidate_predictions(self):
    with self._token_lock:
        self._prediction_token += 1


def check_prediction_accuracy(self):
    """Check if the prediction was accurate (guarded against zero totals)."""
    try:
        total = int(getattr(self, 'total_predictions', 0))
        if total > 0:
            self.successful_predictions = int(getattr(self, 'successful_predictions', 0)) + 1
            success = self.successful_predictions
            accuracy = (success / total) * 100.0
        else:
            success = int(getattr(self, 'successful_predictions', 0))
            accuracy = 0.0
        print(f"Prediction accuracy: {accuracy:.1f}% ({success}/{total})")
    except Exception:
        pass


def _one_shot_exit_watcher(self):
    """Background watcher: exit after the first SPACE press."""
    if not getattr(self, 'exit_on_first_space', False):
        return
    # Poll until a press is recorded
    while True:
        try:
            if self.exit_on_first_space and self.total_predictions > 0:
                # Ensure it runs only once
                if not getattr(self, '_has_pressed_space', False):
                    self._has_pressed_space = True
                    self.prediction_active = False
                    self.monitoring = False
                    self._restart_after_press = True
                    try:
                        print("First SPACE press detected. Returning to area selection...")
                    except Exception:
                        pass
                break
        except Exception:
            break
        time.sleep(0.05)


def schedule_predictive_press(self, predicted_time):
    # Legacy wrapper: delegate to safe scheduler to avoid duplicates.
    return schedule_predictive_press_safe(self, predicted_time)


def schedule_predictive_press_safe(self, predicted_time):
    """Schedule SPACE press before predicted gray appearance (with safety checks).

    In A/B mode, if ab_event_driven_press is True and we expect the slow interval next,
    wait for the actual GRAY onset at the ROI to press, rather than a strict timer.
    """
    # Event-driven path for A/B
    if (self.pattern_type == "alternating" and getattr(self, 'ab_event_driven_press', True)
            and getattr(self, '_ab_expect_slow_next', False)):
        with self._token_lock:
            self._prediction_token += 1
            token = self._prediction_token

        def wait_for_gray_and_press():
            # Wait until early guard time
            nb = float(getattr(self, '_not_before_time', time.time()))
            while time.time() < nb:
                time.sleep(0.0005)

            # Race: press at earlier of (predicted_time - race_early) or GRAY onset
            try:
                race_early = max(0.0, float(getattr(self, 'ab_race_early_ms', 3)) / 1000.0)
            except Exception:
                race_early = 0.003
            race_deadline = max(nb, predicted_time - race_early)

            # Wait for GRAY onset or race deadline (with overall timeout as safety)
            timeout_s = max(0.2, float(getattr(self, '_last_target_interval', 0.4)))
            deadline = time.time() + timeout_s
            if getattr(self, 'debug_ab', False):
                try:
                    print(f"AB debug: event-driven race (race_early={race_early*1000:.0f}ms)")
                except Exception:
                    pass
            while time.time() < deadline:
                with self._token_lock:
                    if token != self._prediction_token:
                        return
                if not self.prediction_active or not self.pattern_established:
                    return
                if time.time() < self.press_lock_until or self.pressed_this_event:
                    return
                # Detect GRAY onset (allow immediate GRAY without requiring explicit WHITE->GRAY edge)
                if self.current_state == "GRAY":
                    break
                # Race deadline reached
                if time.time() >= race_deadline:
                    break
                time.sleep(0.0005)

            # Final press
            try:
                pyautogui.press('space')
            except Exception:
                pass
            self.total_predictions += 1
            print(f"PREDICTIVE SPACE PRESS! (#{self.total_predictions})")
            if getattr(self, 'debug_ab', False):
                try:
                    now2 = time.time()
                    slow_start = getattr(self, '_ab_slow_start_time', None)
                    if slow_start:
                        delta_ms = (now2 - slow_start) * 1000.0
                        print(f"AB debug: pressed {delta_ms:.0f}ms after slow-start (target ~0 to +10ms)")
                except Exception:
                    pass
            self.pressed_this_event = True
            try:
                self.press_lock_until = time.time() + float(getattr(self, 'press_cooldown_s', 0.75))
            except Exception:
                pass
            self.invalidate_predictions()
            threading.Timer(0.1, self.check_prediction_accuracy).start()
            # Restart to area selection after each SPACE press
            self._restart_after_press = True
            self.monitoring = False

        threading.Thread(target=wait_for_gray_and_press, daemon=True).start()
        return

    # Timed path (default)
    # Choose offset dynamically based on the targeted interval length
    dyn_offset = _dynamic_press_offset(self, getattr(self, '_last_target_interval', None))
    press_time = predicted_time - dyn_offset
    # Ensure we never press before a required point in time (e.g., after fast interval)
    try:
        guard = float(getattr(self, '_not_before_time', 0.0)) + 0.001
        if press_time < guard:
            press_time = guard
    except Exception:
        pass
    if press_time <= time.time():
        return
    with self._token_lock:
        self._prediction_token += 1
        token = self._prediction_token

    def delayed_press():
        # High-precision wait: coarse sleep, then spin to reduce overshoot
        try:
            pre_spin = max(0.0, float(getattr(self, 'ab_pre_spin_ms', 6)) / 1000.0)
        except Exception:
            pre_spin = 0.0
        now0 = time.time()
        sleep_until = press_time - pre_spin
        if sleep_until > now0:
            time.sleep(sleep_until - now0)
        while time.time() < press_time:
            time.sleep(0.0005)

        # Re-check validity and gating
        with self._token_lock:
            if token != self._prediction_token:
                return
        now = time.time()
        if not self.prediction_active or not self.pattern_established:
            return
        if now < self.press_lock_until:
            return
        if self.pressed_this_event:
            return

        # If we arrived a tad early, wait briefly for GRAY to appear (A/B slow-start alignment)
        try:
            spin_budget = max(0.0, float(getattr(self, 'ab_spin_wait_ms', 18)) / 1000.0)
        except Exception:
            spin_budget = 0.0
        if spin_budget > 0:
            t0 = time.time()
            while (time.time() - t0) < spin_budget:
                if self.current_state == "GRAY":
                    break
                # short sleep to yield
                time.sleep(0.0005)

        try:
            pyautogui.press('space')
        except Exception:
            pass
        self.total_predictions += 1
        print(f"PREDICTIVE SPACE PRESS! (#{self.total_predictions})")
        if getattr(self, 'debug_ab', False):
            try:
                now2 = time.time()
                slow_start = getattr(self, '_ab_slow_start_time', None)
                if slow_start:
                    delta_ms = (now2 - slow_start) * 1000.0
                    print(f"AB debug: pressed {delta_ms:.0f}ms after slow-start (target ~0 to +10ms)")
            except Exception:
                pass
        self.pressed_this_event = True
        try:
            self.press_lock_until = time.time() + float(getattr(self, 'press_cooldown_s', 0.75))
        except Exception:
            pass

        # Invalidate any other pending predictions and schedule accuracy check
        self.invalidate_predictions()
        threading.Timer(0.1, self.check_prediction_accuracy).start()
        # Restart to area selection after each SPACE press
        self._restart_after_press = True
        self.monitoring = False

    threading.Thread(target=delayed_press, daemon=True).start()
