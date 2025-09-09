import time
import threading
import pyautogui
import mss

# Grouped feature modules
import FDM_capture as fdm_capture
import FDM_detection as fdm_detection
import FDM_pattern as fdm_pattern
import FDM_scheduler as fdm_scheduler
import FDM_input as fdm_input
import FDM_ui as fdm_ui
import FDM_persist as fdm_persist


class PredictiveTimingDetector:
    """Thin orchestrator that wires grouped FDM_* modules together.

    All domain logic lives in small focused modules:
      - FDM_capture: ultra-fast screen capture and FPS
      - FDM_detection: gray/white classification
      - FDM_pattern: pattern learning and prediction logic
      - FDM_scheduler: predictive press scheduling & accuracy tracking
      - FDM_input: keyboard/mouse listeners and key flags
      - FDM_ui: area selection and monitor UI loop
      - FDM_persist: saved areas persistence helpers
    """

    def __init__(self, x1=527, y1=196, x2=1374, y2=916):
        # Region bounds
        self.screen_x1 = x1
        self.screen_y1 = y1
        self.screen_x2 = x2
        self.screen_y2 = y2

        # UI/monitoring state
        self.selected_area = None
        self.monitoring = False
        self.selecting = False

        # Timing pattern variables
        self.gray_timestamps = []
        self.intervals = []
        self.average_interval = None
        self.pattern_established = False
        self.min_samples = 3

        # Advanced pattern support
        self.pattern_type = "single"  # 'single' or 'alternating'
        self.alt_interval_a = None
        self.alt_interval_b = None
        self.auto_predict = True
        self.small_gap_threshold = 0.4
        self._last_target_interval = None

        # A/B timing and scheduling knobs
        self.ab_lead_ms = 22
        self.ab_pre_guard_ms = 5
        self.ab_spin_wait_ms = 6
        self.ab_phase_ms = 0
        self.ab_phase_alpha = 0.4
        self.ab_phase_min = -60
        self.ab_phase_max = 60
        self.ab_target_after_ms = 6
        self._ab_expect_slow_next = False
        self.ab_window_n = 8
        self.ab_trim_frac = 0.2
        self.ab_min_pairs = 5
        self.ab_event_driven_press = True
        self.ab_race_early_ms = 3
        # Classification tolerance between fast/slow (A/B)
        self.ab_classify_margin_frac = 0.10   # 10% of separation
        self.ab_classify_margin_ms_min = 8    # at least 8 ms

        # Fast-gap handling for single patterns
        self.fast_gap_threshold = 0.5
        self.fast_min_window_n = 6
        self.fast_gap_use_min = True

        # Interval noise filtering
        self.min_interval_abs = 0.08
        self.min_interval_fraction_of_avg = 0.30

        # Fast gray detection thresholds
        self.fast_gray_mode = True
        self.gray_min_pixels = 1
        self.gray_min_fraction = 0.0
        self.gray_s_thresh = 80
        self.gray_v_min = 50
        self.gray_v_max = 210
        self.white_s_thresh = 40
        self.white_v_min = 190

        # Prediction state
        self.next_predicted_time = None
        self.prediction_active = False
        self.early_press_offset = 0.05

        # Detection state
        self.detection_active = False
        self.learning_mode = True
        self.current_state = "UNKNOWN"
        self.last_state = "UNKNOWN"

        # Selection variables
        self.selection_start = None
        self.selection_end = None

        # Global input flags
        self.enter_pressed = False
        self.escape_pressed = False
        self.r_pressed = False
        self.q_pressed = False
        self.s_pressed = False
        self.l_pressed = False
        self.p_pressed = False

        # Performance tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        self.successful_predictions = 0
        self.total_predictions = 0

        # Exit behavior: stop after first SPACE press
        self.exit_on_first_space = True
        self._has_pressed_space = False

        # Press gating
        self.press_cooldown_s = 0.75
        self.press_lock_until = 0.0
        self.pressed_this_event = False
        self.clear_required_frames = 8
        self.present_required_frames = 3
        self.white_streak = 0
        self.gray_streak = 0

        # Prediction invalidation token
        self._token_lock = threading.Lock()
        self._prediction_token = 0
        self._not_before_time = 0.0
        self._last_schedule_from_ts = None

        # Debug controls
        self.debug_ab = True

        # Saved areas for this session
        self._saved_areas = []
        self._saved_area_idx = 0
        self.auto_cycle_saved_areas = True
        try:
            fdm_persist._load_saved_areas(self)
        except Exception:
            pass

        # Initialize screen capture region
        self.sct = mss.mss()
        self.monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}

        # Safety off for high-speed presses
        pyautogui.FAILSAFE = False

        # Start input listener and exit watcher
        self.start_keyboard_listener()
        threading.Thread(target=self._one_shot_exit_watcher, daemon=True).start()

        print("PREDICTIVE TIMING DETECTOR")
        print(f"AI Pattern Learning System - Screen region: ({x1}, {y1}) to ({x2}, {y2})")

    # -------- Persistence wrappers --------
    def _areas_file_path(self):
        return fdm_persist._areas_file_path(self)

    def _persist_saved_areas(self):
        return fdm_persist._persist_saved_areas(self)

    def _load_saved_areas(self):
        return fdm_persist._load_saved_areas(self)

    # -------- Input wrappers --------
    def start_keyboard_listener(self):
        return fdm_input.start_keyboard_listener(self)

    def reset_key_flags(self):
        return fdm_input.reset_key_flags(self)

    def mouse_listener(self):
        return fdm_input.mouse_listener(self)

    # -------- Capture wrapper --------
    def ultra_fast_capture(self):
        return fdm_capture.ultra_fast_capture(self)

    # -------- Detection wrapper --------
    def classify_region_state(self, region):
        return fdm_detection.classify_region_state(self, region)

    # -------- Pattern wrappers --------
    def record_gray_appearance(self):
        return fdm_pattern.record_gray_appearance(self)

    def record_gray_appearance_safe(self):
        return fdm_pattern.record_gray_appearance_safe(self)

    def calculate_pattern(self):
        return fdm_pattern.calculate_pattern(self)

    def calculate_pattern_v2(self):
        return fdm_pattern.calculate_pattern_v2(self)

    def predict_next_gray(self):
        return fdm_pattern.predict_next_gray(self)

    def predict_next_target_time(self):
        return fdm_pattern.predict_next_target_time(self)

    def reset_pattern_learning(self):
        return fdm_pattern.reset_pattern_learning(self)

    # -------- Scheduler wrappers --------
    def _dynamic_press_offset(self, interval_len):
        return fdm_scheduler._dynamic_press_offset(self, interval_len)

    def schedule_predictive_press(self, predicted_time):
        return fdm_scheduler.schedule_predictive_press(self, predicted_time)

    def schedule_predictive_press_safe(self, predicted_time):
        return fdm_scheduler.schedule_predictive_press_safe(self, predicted_time)

    def invalidate_predictions(self):
        return fdm_scheduler.invalidate_predictions(self)

    def check_prediction_accuracy(self):
        return fdm_scheduler.check_prediction_accuracy(self)

    def _one_shot_exit_watcher(self):
        return fdm_scheduler._one_shot_exit_watcher(self)

    # -------- UI wrappers --------
    def select_area(self):
        return fdm_ui.select_area(self)

    def monitor_area(self, area):
        return fdm_ui.monitor_area(self, area)

    # -------- Orchestration --------
    def run(self):
        """Main run loop."""
        print("PREDICTIVE TIMING DETECTOR")
        print("AI-powered pattern learning system!")
        print("Learns timing patterns and predicts future events!")
        print("More accurate than reactive detection!")
        try:
            first_iter = True
            while True:
                area = None
                # Auto-cycle through saved areas in order without UI
                if getattr(self, "auto_cycle_saved_areas", False) and getattr(self, "_saved_areas", None):
                    try:
                        total = len(self._saved_areas)
                        if total > 0:
                            if self._saved_area_idx >= total:
                                print("All saved areas have been used. Open selection UI...")
                                area = None
                            else:
                                area = tuple(self._saved_areas[self._saved_area_idx])
                                print(f"Auto using saved area [{self._saved_area_idx+1}/{total}]: {area}")
                    except Exception:
                        area = None
                if area is None:
                    area = self.select_area()
                    if not area:
                        try:
                            if getattr(self, "_saved_areas", None):
                                if self._saved_area_idx < len(self._saved_areas):
                                    area = tuple(self._saved_areas[self._saved_area_idx])
                                    print(f"Using saved area: {area}")
                        except Exception:
                            area = None
                    if not area:
                        print("No area selected, exiting...")
                        if getattr(self, "_saved_areas", None) and self._saved_areas:
                            break
                        else:
                            print("No saved areas; please select an area.")
                            continue
                try:
                    self.reset_pattern_learning()
                except Exception:
                    pass
                self._restart_after_press = False
                self._has_pressed_space = False
                self.monitor_area(area)
                first_iter = False
                # Advance to next saved area if restarting
                try:
                    if getattr(self, "_restart_after_press", False) and getattr(self, "_saved_areas", None):
                        if self._saved_areas:
                            self._saved_area_idx += 1
                except Exception:
                    pass
                if not getattr(self, "_restart_after_press", False):
                    break
        except Exception as e:
            print(f"Error: {e}")
        # Print saved areas for this session
        try:
            if getattr(self, '_saved_areas', None):
                print("\nSaved areas this session:")
                for idx, ar in enumerate(self._saved_areas, 1):
                    print(f"  {idx}. {ar}")
        except Exception:
            pass
        print("Predictive detector ended.")
