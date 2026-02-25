import logging
import numpy as np
import json
from pathlib import Path
from collections import deque
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Constants matching training logic
WINDOW_1H = 60
WINDOW_1D = 1440

class FeatureEngineer:
    """
    Handles all streaming feature transformations:
    1. Threshold-based flag derivation (warning/critical)
    2. Incremental rolling window averages (deques)
    3. Final ordered vector assembly
    """

    def __init__(self, thresholds_path: str = "model/thresholds.json", config_path: str = "model/model_config.json"):
        self.thresholds = self._load_thresholds(thresholds_path)
        self.sensor_warn_crit = self.thresholds.get("sensor_warning_critical", {})
        self.max_idle_current = self.thresholds.get("idle_detection", {}).get("max_idle_current", 4.5)
        
        # Load features from model_config to drive the rolling logic (Fix 2)
        model_config = self._load_json(config_path)
        all_features = model_config.get("features", [])
        
        # We roll any feature that the model actually expects as an engineered key
        self.rolling_targets = set(all_features)

    def _load_thresholds(self, path: str) -> Dict[str, Any]:
        return self._load_json(path)

    def _load_json(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {}
        try:
            with open(p, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def derive_flags(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute warning_flag / critical_flag columns from raw sensor values.
        Matches training logic exactly.
        """
        for sensor_key, thresholds in self.sensor_warn_crit.items():
            # Find value in event (exact or containing match)
            val = None
            if sensor_key in event:
                val = event[sensor_key]
            else:
                for k, v in event.items():
                    if sensor_key in k and isinstance(v, (int, float)):
                        val = float(v)
                        break
            
            if val is None:
                continue

            warn = thresholds.get("warning")
            crit = thresholds.get("critical")

            if warn is not None:
                event[f"{sensor_key}_warning_flag"] = int(val == 0 if warn == 0 else val >= warn)
            if crit is not None:
                event[f"{sensor_key}_critical_flag"] = int(val == 0 if crit == 0 else val >= crit)

        # Idle override for underspeed
        zs_flag = "zero_speed_switch_boot/underspeed_critical_flag"
        if event.get(zs_flag) == 1:
            cur_val = next((v for k, v in event.items() if "current_transducer" in k), None)
            if cur_val is not None and float(cur_val) < self.max_idle_current:
                event[zs_flag] = 0

        return event

    def update_rolling(self, event: Dict[str, Any], state_rolling: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update rolling averages using Exponential Moving Average (EMA).
        Alpha = 0.1 (fixed per user request).
        Matches user's hardened production logic.
        """
        alpha = 0.1
        event = self.derive_flags(event)
        new_rolling = state_rolling.copy()

        for feature_name in event:
            if not isinstance(event[feature_name], (int, float)):
                continue

            # Only roll raw numeric sensor values (not already flags)
            if not feature_name.endswith("_flag"):
                avg_key = f"{feature_name}_avg_value"

                prev_val = state_rolling.get(avg_key, event[feature_name])
                new_rolling[avg_key] = ((1 - alpha) * prev_val) + (alpha * event[feature_name])

        return new_rolling

    def build_vector_dict(self, event: Dict[str, Any], rolling_state: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, float]:
        """
        Merge all sources and use EMA values from the rolling_state.
        """
        merged = {
            "operating_hours": float(state.get("operating_hours", 0.0)),
            "runtime_hours": float(state.get("operating_hours", 0.0))
        }

        # 1. Start with the EMA values (Now match full path model keys perfectly)
        merged.update({k: float(v) for k, v in rolling_state.items() if isinstance(v, (int, float))})

        # 2. Add raw event values (includes derived flags)
        merged.update({k: float(v) for k, v in event.items() if isinstance(v, (int, float))})
        
        return merged

    def build_ordered_vector(self, event: Dict[str, Any], rolling_state: Dict[str, Any], state: Dict[str, Any], required_features: List[str]) -> np.ndarray:
        """Enforce column order matching training model_config.json."""
        merged = self.build_vector_dict(event, rolling_state, state)
        vector = [merged.get(feat, 0.0) for feat in required_features]
        return np.array(vector, dtype=np.float64).reshape(1, -1)
