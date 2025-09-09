import time
import cv2
import numpy as np


def select_area(self):
    """Area selection UI."""
    print("\n=== AREA SELECTION ===")
    print("1. Click and drag DIRECTLY on your game screen")
    print("2. Press ENTER anywhere to confirm")
    print("3. Press ESC anywhere to cancel")

    self.reset_key_flags()

    cv2.namedWindow("Selection Display", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Selection Display", 600, 400)

    self.selecting = True
    # Prefill with last saved area if available
    try:
        self.selected_area = (
            tuple(self._saved_areas[self._saved_area_idx])
            if getattr(self, '_saved_areas', None) and self._saved_areas else None
        )
    except Exception:
        self.selected_area = None

    # Start mouse listener
    import threading
    mouse_thread = threading.Thread(target=self.mouse_listener, daemon=True)
    mouse_thread.start()

    while self.selecting:
        frame = self.ultra_fast_capture()
        display_frame = frame.copy()

        # Draw selection
        if self.selection_start and self.selection_end:
            x1 = min(self.selection_start[0], self.selection_end[0])
            y1 = min(self.selection_start[1], self.selection_end[1])
            x2 = max(self.selection_start[0], self.selection_end[0])
            y2 = max(self.selection_start[1], self.selection_end[1])

            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                self.selected_area = (x1, y1, x2, y2)
        elif self.selected_area:
            try:
                x1, y1, x2, y2 = self.selected_area
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
                cv2.putText(display_frame, "ENTER to confirm last area, or drag new", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            except Exception:
                pass

        cv2.putText(display_frame, "Click and drag on GAME SCREEN", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if self.selected_area:
            cv2.putText(display_frame, "ENTER to confirm", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("Selection Display", display_frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (13, 10):
            self.enter_pressed = True
        elif key == 27:
            self.escape_pressed = True
        cv2.waitKey(1)

        if self.enter_pressed:
            if not self.selected_area and self.selection_start and self.selection_end:
                x1 = min(self.selection_start[0], self.selection_end[0])
                y1 = min(self.selection_start[1], self.selection_end[1])
                x2 = max(self.selection_start[0], self.selection_end[0])
                y2 = max(self.selection_start[1], self.selection_end[1])
                x1 = max(0, x1); y1 = max(0, y1)
                x2 = max(x1+1, x2); y2 = max(y1+1, y2)
                self.selected_area = (x1, y1, x2, y2)
            if self.selected_area:
                try:
                    if isinstance(self.selected_area, tuple) and len(self.selected_area) == 4:
                        self._saved_areas.append(tuple(self.selected_area))
                        try:
                            self._persist_saved_areas()
                        except Exception:
                            pass
                except Exception:
                    pass
                break
            break
        if self.escape_pressed:
            self.selected_area = None
            break

    self.selecting = False
    cv2.destroyWindow("Selection Display")
    return self.selected_area


def monitor_area(self, area):
    """Monitor selected area with predictive timing."""
    print(f"\nPREDICTIVE TIMING SYSTEM")
    print(f"Area: {area}")
    print("Learning Mode: Watch for patterns")
    print("Prediction Mode: AI-powered timing")
    print("'p' = Prediction mode (AI timing)")
    print("'r' = Reset pattern   's' = New area   'q' = Quit")

    self.reset_key_flags()
    self.monitoring = True
    x1, y1, x2, y2 = area

    cv2.namedWindow("PREDICTIVE AI", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("PREDICTIVE AI", 700, 600)

    try:
        while self.monitoring:
            frame = self.ultra_fast_capture()
            region = frame[y1:y2, x1:x2]

            if region.size == 0:
                continue

            # Classify current state
            self.current_state = self.classify_region_state(region)

            # Learning mode: Record gray appearances
            if self.learning_mode and self.current_state == "GRAY" and self.last_state == "WHITE":
                self.record_gray_appearance_safe()

            # Prediction mode: Schedule predictive presses
            if self.prediction_active and self.pattern_established:
                if self.current_state == "GRAY" and self.last_state == "WHITE":
                    # Update pattern with new data
                    self.record_gray_appearance_safe()
                    # Cancel any previously scheduled presses; new event boundary
                    try:
                        self.invalidate_predictions()
                    except Exception:
                        pass
                    # Optional: adaptive phase correction for A/B slow arrival timing
                    # IMPORTANT: adjust phase before clearing the expectation flag
                    try:
                        if getattr(self, '_ab_expect_slow_next', False) and hasattr(self, '_ab_slow_start_time'):
                            now_ts = self.gray_timestamps[-1]
                            delta_ms = (now_ts - float(self._ab_slow_start_time)) * 1000.0
                            target_ms = float(getattr(self, 'ab_target_after_ms', 6))
                            error_ms = delta_ms - target_ms
                            alpha = float(getattr(self, 'ab_phase_alpha', 0.4))
                            phase_ms = float(getattr(self, 'ab_phase_ms', 0.0))
                            phase_ms = phase_ms + alpha * error_ms
                            pmin = float(getattr(self, 'ab_phase_min', -60))
                            pmax = float(getattr(self, 'ab_phase_max', 60))
                            phase_ms = max(pmin, min(pmax, phase_ms))
                            self.ab_phase_ms = phase_ms
                            if getattr(self, 'debug_ab', False):
                                print(f"AB debug: phase adjust error={error_ms:.0f}ms -> phase={phase_ms:.0f}ms")
                    except Exception:
                        pass
                    # Clear expectation after processing phase adjustment logic
                    try:
                        self._ab_expect_slow_next = False
                    except Exception:
                        pass
                    # Schedule next prediction (guard against double-scheduling for same event)
                    next_time = self.predict_next_target_time()
                    if next_time:
                        from_ts = self.gray_timestamps[-1] if self.gray_timestamps else None
                        # Store ETA for UI/logging
                        self._next_predicted_at = next_time
                        self._next_predicted_from = from_ts
                        # Only schedule once per event
                        if getattr(self, '_last_schedule_from_ts', None) != from_ts:
                            self._last_schedule_from_ts = from_ts
                            self.schedule_predictive_press_safe(next_time)

            # Update last state
            self.last_state = self.current_state

            # Display status
            display_region = cv2.resize(region, (240, 180))
            status_image = np.zeros((520, 700, 3), dtype=np.uint8)
            status_image[:180, :240] = display_region

            # Current state
            cv2.putText(status_image, f"STATE: {self.current_state}", (270, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(status_image, f"FPS: {self.current_fps}", (270, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            # Mode status
            if self.learning_mode: 
                cv2.putText(status_image, "MODE: LEARNING", (270, 220), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(status_image, "Recording gray patterns...", (270, 260), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            elif self.prediction_active:
                cv2.putText(status_image, "MODE: PREDICTION", (270, 220), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                if self.pattern_established:
                    cv2.putText(status_image, "AI predicting timing!", (270, 260), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    accuracy = (self.successful_predictions / max(1, self.total_predictions)) * 100
                    cv2.putText(status_image, f"Accuracy: {accuracy:.1f}%", (270, 290), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    cv2.putText(status_image, "Need pattern first!", (270, 260), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            else:
                cv2.putText(status_image, "MODE: STANDBY", (270, 220), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)

            # Controls
            y_start = 400
            cv2.putText(status_image, "CONTROLS:", (10, y_start), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(status_image, "'l' = Learning mode", (10, y_start + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(status_image, "'p' = Prediction mode", (10, y_start + 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(status_image, "'r' = Reset pattern", (10, y_start + 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(status_image, "'s' = New area", (10, y_start + 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(status_image, "'q' = Quit", (10, y_start + 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow("PREDICTIVE AI", status_image)
            cv2.waitKey(1)

            # Handle controls
            if self.l_pressed:
                self.learning_mode = True
                self.prediction_active = False
                print("LEARNING MODE activated - recording patterns")
                self.reset_key_flags()

            if self.p_pressed:
                if self.pattern_established:
                    self.learning_mode = False
                    self.prediction_active = True
                    print("PREDICTION MODE activated - AI timing enabled")
                else:
                    print("Need to learn pattern first! Press 'l' to start learning.")
                self.reset_key_flags()

            if self.r_pressed:
                self.reset_pattern_learning()
                self.learning_mode = True
                self.prediction_active = False
                self.reset_key_flags()

            if self.s_pressed:
                cv2.destroyWindow("PREDICTIVE AI")
                new_area = self.select_area()
                if new_area:
                    # Track new area in this session
                    try:
                        if isinstance(new_area, tuple) and len(new_area) == 4:
                            self._saved_areas.append(tuple(new_area))
                            try:
                                self._persist_saved_areas()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    area = new_area
                    x1, y1, x2, y2 = area
                    self.reset_pattern_learning()
                    cv2.namedWindow("PREDICTIVE AI", cv2.WINDOW_NORMAL)
                    cv2.resizeWindow("PREDICTIVE AI", 700, 600)
                else:
                    cv2.namedWindow("PREDICTIVE AI", cv2.WINDOW_NORMAL)
                    cv2.resizeWindow("PREDICTIVE AI", 700, 600)
                self.reset_key_flags()

            if self.q_pressed:
                break

            # Keep last state for edge detection
            self.last_state = self.current_state

    except KeyboardInterrupt:
        print("\nPredictive system stopped.")

    cv2.destroyWindow("PREDICTIVE AI")
    self.monitoring = False
