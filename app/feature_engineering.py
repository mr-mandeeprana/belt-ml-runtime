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
        Compute warning_flag / critical_flag columns from statistical values.
        Prioritizes 'avg_value' or 'max_value' if available.
        """
        for sensor_base, thresholds in self.sensor_warn_crit.items():
            # Support hierarchical keys and flat statistical input
            val = event.get("avg_value") if event.get("sensorid") == sensor_base else None
            
            # Fallback to direct key if it's already mapped
            if val is None:
                val = event.get(f"{sensor_base}_avg_value") or event.get(sensor_base)

            if val is None:
                continue

            # Check thresholds (using max_value for critical if available, otherwise avg)
            check_val = event.get("max_value", val)
            
            warn = thresholds.get("warning")
            crit = thresholds.get("critical")

            if warn is not None:
                event[f"{sensor_base}_warning_flag"] = int(check_val == 0 if warn == 0 else check_val >= warn)
            if crit is not None:
                event[f"{sensor_base}_critical_flag"] = int(check_val == 0 if crit == 0 else check_val >= crit)

        # Idle override for underspeed
        zs_flag = "zero_speed_switch_boot/underspeed_critical_flag"
        if event.get(zs_flag) == 1:
            cur_val = event.get("avg_value") if event.get("sensorid") == "current_transducer" else None
            if cur_val is not None and float(cur_val) < self.max_idle_current:
                event[zs_flag] = 0

        return event

    def update_rolling(self, event: Dict[str, Any], state_rolling: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update rolling state: Prioritizes incoming 'avg_value'.
        If 'avg_value' is present, we skip the EMA calculation as the source is already aggregated.
        """
        event = self.derive_flags(event)
        new_rolling = state_rolling.copy()

        sensor_id = event.get("sensorid")
        if sensor_id and "avg_value" in event:
            avg_key = f"{sensor_id}_avg_value"
            new_rolling[avg_key] = event["avg_value"]
        
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
