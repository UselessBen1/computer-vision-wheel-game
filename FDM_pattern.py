import time
import statistics


def record_gray_appearance(self):
    """Record timestamp when gray appears (simple)."""
    current_time = time.time()
    self.gray_timestamps.append(current_time)

    # Calculate intervals if we have enough data
    if len(self.gray_timestamps) >= 2:
        interval = current_time - self.gray_timestamps[-2]
        self.intervals.append(interval)
        print(f"Gray interval: {interval:.3f}s")

        # Establish pattern with enough samples
        if len(self.intervals) >= self.min_samples:
            calculate_pattern_v2(self)


def record_gray_appearance_safe(self):
    """Record timestamp when gray appears, filtering spurious ultra-short intervals."""
    now = time.time()
    if self.gray_timestamps:
        last = self.gray_timestamps[-1]
        interval = now - last
        too_short = interval < getattr(self, 'min_interval_abs', 0.08)
        too_small_vs_avg = False
        if self.average_interval:
            try:
                frac = getattr(self, 'min_interval_fraction_of_avg', 0.30)
                too_small_vs_avg = interval < (self.average_interval * frac)
            except Exception:
                too_small_vs_avg = False
        if too_short or too_small_vs_avg:
            try:
                print(f"Ignoring spurious interval: {interval:.3f}s (noise)")
            except Exception:
                pass
            return
        self.gray_timestamps.append(now)
        self.intervals.append(interval)
        print(f"Gray interval: {interval:.3f}s")
    else:
        self.gray_timestamps.append(now)

    if len(self.intervals) >= self.min_samples:
        calculate_pattern_v2(self)


def calculate_pattern(self):
    """Calculate the timing pattern from recorded intervals (basic)."""
    if len(self.intervals) < self.min_samples:
        return

    # Calculate average interval
    self.average_interval = statistics.mean(self.intervals)

    # Calculate standard deviation to check consistency
    std_dev = statistics.stdev(self.intervals) if len(self.intervals) > 1 else 0
    consistency = (std_dev / self.average_interval) * 100 if self.average_interval > 0 else 100

    print("PATTERN ANALYSIS:")
    print(f"   Average interval: {self.average_interval:.3f}s")
    print(f"   Std deviation: {std_dev:.3f}s")
    print(f"   Consistency: {100-consistency:.1f}%")

    # Pattern is established if consistency is good (< 10% variation)
    if consistency < 10:
        self.pattern_established = True
        print("   PATTERN ESTABLISHED! Ready for predictions.")
    else:
        print("   Pattern inconsistent, need more samples...")


def calculate_pattern_v2(self):
    """Enhanced pattern detection supporting alternating intervals (1,2,1,2)."""
    if len(self.intervals) < self.min_samples:
        return

    # Sticky single-interval refinement: once established, keep it and smooth updates
    if self.pattern_type == "single" and self.pattern_established and self.average_interval:
        last = self.intervals[-1] if self.intervals else None
        if last is not None:
            low = 0.5 * self.average_interval
            high = 1.5 * self.average_interval
            if low <= last <= high:
                alpha = 0.2
                self.average_interval = (1 - alpha) * float(self.average_interval) + alpha * float(last)
        print("PATTERN ANALYSIS:")
        print(f"   Samples: {len(self.intervals)}")
        print(f"   Average interval: {self.average_interval:.3f}s  (sticky)")
        # Compute effective single interval for fast-gap mode
        try:
            eff = _effective_single_interval(self)
            self.single_effective_interval = eff
        except Exception:
            self.single_effective_interval = getattr(self, 'average_interval', None)
        if self.auto_predict and not self.prediction_active:
            self.learning_mode = False
            self.prediction_active = True
            print("Prediction auto-activated.")
        return

    # General case
    try:
        std_all = statistics.stdev(self.intervals) if len(self.intervals) > 1 else 0.0
        cv_overall = (std_all / statistics.mean(self.intervals)) * 100 if statistics.mean(self.intervals) > 0 else 100
    except Exception:
        cv_overall = 100

    # Default to single interval
    self.pattern_type = "single"
    self.average_interval = statistics.mean(self.intervals)

    # Check for alternating pattern using even/odd intervals
    even = [self.intervals[i] for i in range(0, len(self.intervals)) if i % 2 == 0]
    odd = [self.intervals[i] for i in range(0, len(self.intervals)) if i % 2 == 1]
    alt_detected = False
    if len(even) >= 2 and len(odd) >= 2:
        def tmean(vals):
            if not vals:
                return None
            k = max(1, int(len(vals) * 0.2))
            sel = sorted(vals)
            if len(sel) > 2 * k:
                sel = sel[k:-k]
            return statistics.mean(sel) if sel else None
        mean_even = tmean(even) or statistics.mean(even)
        mean_odd = tmean(odd) or statistics.mean(odd)
        std_even = statistics.stdev(even) if len(even) > 1 else 0.0
        std_odd = statistics.stdev(odd) if len(odd) > 1 else 0.0
        cv_even = (std_even / mean_even) * 100 if mean_even > 0 else 100
        cv_odd = (std_odd / mean_odd) * 100 if mean_odd > 0 else 100
        distinct_pct = abs(mean_even - mean_odd) / max(mean_even, mean_odd) * 100 if max(mean_even, mean_odd) > 0 else 0
        # Relaxed thresholds + strong distinctness to converge on A/B
        if ((len(even) >= 2 and len(odd) >= 2 and cv_even < 22 and cv_odd < 22 and distinct_pct > 15) or
            (len(self.intervals) >= 4 and distinct_pct > 30 and max(cv_even, cv_odd) < 30)):
            alt_detected = True
            self.pattern_type = "alternating"
            self.alt_interval_a = mean_even
            self.alt_interval_b = mean_odd

    # Fallback A/B detection via threshold + flip-rate if not detected yet
    if not alt_detected and len(self.intervals) >= 6:
        vals = list(self.intervals)
        try:
            thr = statistics.median(vals)
        except Exception:
            thr = sum(vals) / len(vals)
        labels = [0 if v <= thr else 1 for v in vals]
        flips = sum(1 for i in range(1, len(labels)) if labels[i] != labels[i-1])
        flip_rate = flips / (len(labels) - 1)
        low = [v for v in vals if v <= thr]
        high = [v for v in vals if v > thr]
        if low and high:
            mean_low = statistics.mean(low)
            mean_high = statistics.mean(high)
            std_low = statistics.stdev(low) if len(low) > 1 else 0.0
            std_high = statistics.stdev(high) if len(high) > 1 else 0.0
            cv_low = (std_low / mean_low) * 100 if mean_low > 0 else 100
            cv_high = (std_high / mean_high) * 100 if mean_high > 0 else 100
            distinct2 = abs(mean_high - mean_low) / max(mean_high, mean_low) * 100 if max(mean_high, mean_low) > 0 else 0
            # Require clear alternation and bimodality
            if flip_rate > 0.65 and distinct2 > 25 and max(cv_low, cv_high) < 28 and min(len(low), len(high)) >= 3:
                alt_detected = True
                self.pattern_type = "alternating"
                # Keep alt A/B aligned to even/odd index means for parity-based scheduling
                self.alt_interval_a = statistics.mean(even) if even else mean_low
                self.alt_interval_b = statistics.mean(odd) if odd else mean_high

    # Logging (simplified)
    print("PATTERN ANALYSIS:")
    print(f"   Samples: {len(self.intervals)}")
    if alt_detected or self.pattern_type == "alternating":
        print(f"   Alternating means: A={self.alt_interval_a:.3f}s, B={self.alt_interval_b:.3f}s")
        self.pattern_established = True
        if self.auto_predict and not self.prediction_active:
            self.learning_mode = False
            self.prediction_active = True
            print("Prediction auto-activated.")
    else:
        print(f"   Average interval: {self.average_interval:.3f}s  (CV {cv_overall:.1f}%)")
        if cv_overall < 10:
            self.pattern_established = True
            print("   Single-interval pattern established.")
            try:
                eff = _effective_single_interval(self)
                self.single_effective_interval = eff
            except Exception:
                self.single_effective_interval = getattr(self, 'average_interval', None)
            if self.auto_predict and not self.prediction_active:
                self.learning_mode = False
                self.prediction_active = True
                print("Prediction auto-activated.")
        else:
            print("   Pattern inconsistent, need more samples...")


def _effective_single_interval(self):
    """Return the interval to use for single-pattern prediction.

    If the average interval is below fast_gap_threshold and fast-gap mode is enabled,
    use the minimum of the last `fast_min_window_n` intervals (above noise floor).
    Otherwise, use the average interval.
    """
    avg = getattr(self, 'average_interval', None)
    if not avg:
        return None
    use_min = bool(getattr(self, 'fast_gap_use_min', True))
    thresh = float(getattr(self, 'fast_gap_threshold', 0.5))
    if use_min and avg < thresh and self.intervals:
        n = max(1, int(getattr(self, 'fast_min_window_n', 6)))
        window = self.intervals[-n:] if len(self.intervals) >= n else self.intervals[:]
        # Filter by noise threshold
        floor = float(getattr(self, 'min_interval_abs', 0.08))
        candidates = [x for x in window if x >= floor]
        if candidates:
            return min(candidates)
    return avg


def predict_next_gray(self):
    """Predict when the next gray will appear."""
    if not self.pattern_established or not self.gray_timestamps:
        return None

    last_gray_time = self.gray_timestamps[-1]
    # Use alternating pattern if detected (default behavior: next interval)
    if self.pattern_type == "alternating" and self.alt_interval_a and self.alt_interval_b:
        next_index = len(self.intervals)  # zero-based index of the next interval
        next_delta = self.alt_interval_a if (next_index % 2 == 0) else self.alt_interval_b
        return last_gray_time + next_delta
    else:
        return last_gray_time + self.average_interval


def predict_next_target_time(self):
    """Predict preferred next target time.

    For alternating patterns, prefer the slower interval and ensure the
    press happens after the faster one has scanned if it comes first.
    """
    if not self.pattern_established or not self.gray_timestamps:
        return None
    last_gray_time = self.gray_timestamps[-1]

    if self.pattern_type == "alternating" and self.alt_interval_a and self.alt_interval_b:
        # Gate: require enough pairs before scheduling in fast/unstable cases
        min_pairs = int(getattr(self, 'ab_min_pairs', 5))
        if len(self.intervals) < 2 * min_pairs:
            if getattr(self, 'debug_ab', False):
                try:
                    print(f"AB debug: gating schedule until {min_pairs} pairs collected (have {len(self.intervals)//2})")
                except Exception:
                    pass
            return None
        a = float(self.alt_interval_a)
        b = float(self.alt_interval_b)
        fast = min(a, b)
        slow = max(a, b)
        # Schedule only when the last completed interval is the fast one.
        # Prefer value-based classification; fall back to parity if ambiguous.
        last_idx = len(self.intervals) - 1
        if last_idx >= 0:
            last_iv = float(self.intervals[-1])
            # Value-based decision with margin (tunable)
            diff = abs(slow - fast)
            frac = float(getattr(self, 'ab_classify_margin_frac', 0.10))
            min_ms = float(getattr(self, 'ab_classify_margin_ms_min', 8)) / 1000.0
            margin = max(min_ms, frac * diff)  # e.g., 10% of separation or >=8ms
            by_value_fast = (abs(last_iv - fast) + 1e-6) < (abs(last_iv - slow) - margin)
            # Parity-based fallback
            fast_is_even = (a <= b)
            last_is_even = (last_idx % 2 == 0)
            by_parity_fast = (last_is_even == fast_is_even)
            last_was_fast = by_value_fast or (not by_value_fast and by_parity_fast)
            if getattr(self, 'debug_ab', False):
                try:
                    print(f"AB debug: classify last={last_iv:.3f}s as fast? value={by_value_fast} parity={by_parity_fast} (fast={fast:.3f}, slow={slow:.3f})")
                except Exception:
                    pass
            if last_was_fast:
                # Aggressive lead for fast pairs; adaptive: larger lead for smaller slow intervals
                base_lead = max(0.0, float(getattr(self, 'ab_lead_ms', 22)) / 1000.0)
                adaptive = 0.0
                try:
                    # Add up to +10ms extra lead when slow < 0.35s
                    if slow < 0.35:
                        adaptive = min(0.010, (0.35 - slow) * 0.08)
                except Exception:
                    adaptive = 0.0
                phase = 0.001 * float(getattr(self, 'ab_phase_ms', 0))
                lead_s = base_lead + adaptive + max(-0.050, min(0.050, phase))
                slow_start = last_gray_time + slow
                # Store slow-start for accurate debug later
                self._ab_slow_start_time = slow_start
                predicted_time = last_gray_time + max(0.0, slow - lead_s)
                pre_guard = max(0.0, float(getattr(self, 'ab_pre_guard_ms', 6)) / 1000.0)
                # Allow early window before predicted_time; scheduler will clamp to +guard later
                self._not_before_time = max(0.0, predicted_time - pre_guard)
                self._last_target_interval = slow
                self._ab_expect_slow_next = True
                # Debug: confirm countdown starts at smaller value (fast)
                if getattr(self, 'debug_ab', False):
                    try:
                        now = time.time()
                        eta_ms = max(0.0, (predicted_time - now)) * 1000.0
                        slow_eta_ms = max(0.0, (slow_start - now)) * 1000.0
                        print(f"AB debug: countdown started at fast; ETA={eta_ms:.0f}ms (to slow-start {slow_eta_ms:.0f}ms) slow={slow:.3f}s lead={lead_s*1000:.0f}ms phase={phase*1000:.0f}ms")
                    except Exception:
                        pass
                return predicted_time
        return None
    else:
        # Single pattern
        try:
            eff = getattr(self, 'single_effective_interval', None)
            next_delta = float(eff) if eff is not None else float(self.average_interval)
        except Exception:
            next_delta = float(self.average_interval)
        self._last_target_interval = next_delta
        return last_gray_time + next_delta


def reset_pattern_learning(self):
    """Reset all learned patterns and gating state."""
    # Core buffers
    self.gray_timestamps = []
    self.intervals = []
    self.average_interval = None
    self.single_effective_interval = None
    # Pattern flags
    self.pattern_established = False
    self.pattern_type = "single"
    self.alt_interval_a = None
    self.alt_interval_b = None
    # Mode flags
    self.learning_mode = True
    self.prediction_active = False
    # Performance counters (per-area)
    self.successful_predictions = 0
    self.total_predictions = 0
    # Gating/state
    self.pressed_this_event = False
    self.white_streak = 0
    self.gray_streak = 0
    self.press_lock_until = 0.0
    # Prediction helpers
    self._not_before_time = 0.0
    self._next_predicted_at = None
    self._next_predicted_from = None
    self._last_schedule_from_ts = None
    # A/B helpers
    self._ab_slow_start_time = None
    self._ab_expect_slow_next = False
    try:
        # keep phase setting sticky but safe
        if getattr(self, 'ab_phase_ms', None) is None:
            self.ab_phase_ms = 0
    except Exception:
        pass
    # Invalidate any pending scheduled actions
    try:
        self.invalidate_predictions()
    except Exception:
        pass
    try:
        print("Pattern learning reset!")
    except Exception:
        pass
