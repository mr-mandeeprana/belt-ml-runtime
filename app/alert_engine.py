import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AlertEngine:
    """
    Evaluates predictions and features to trigger alerts.
    Thresholds are loaded dynamically from model/thresholds.json.
    """

    def __init__(self, thresholds_path: str = "model/thresholds.json"):
        self.thresholds = self._load_thresholds(thresholds_path)

        hs = self.thresholds.get("health_score_thresholds", {})
        rul = self.thresholds.get("rul_thresholds", {})

        # Health score boundaries
        self.hs_critical   = hs.get("critical",         55.0)
        self.hs_warning    = hs.get("warning",          65.0)
        self.hs_maint_due  = hs.get("maintenance_due",  75.0)

        # RUL day boundaries
        self.rul_critical  = rul.get("critical_days",   180)
        self.rul_warning   = rul.get("warning_days",    540)
        self.rul_maint_due = rul.get("maintenance_due_days", 1080)

    def _load_thresholds(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            print(f"⚠ Warning: Thresholds file not found at {path}. Using default values.")
            return {}
        try:
            with open(p, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error: Failed to load thresholds: {e}")
            return {}

    def evaluate(
        self,
        health: float,
        rul: float,
    ) -> Dict[str, Any]:
        """
        Evaluate health score and RUL against config-driven thresholds.
        """
        is_critical    = (health < self.hs_critical)   or (rul < self.rul_critical)
        is_warning     = (health < self.hs_warning)    or (rul < self.rul_warning)
        is_maint_due   = (health < self.hs_maint_due)  or (rul < self.rul_maint_due)

        if is_critical:
            risk_level = "CRITICAL"
        elif is_warning:
            risk_level = "WARNING"
        elif is_maint_due:
            risk_level = "MAINTENANCE_DUE"
        else:
            risk_level = "HEALTHY"

        return {
            "critical":             is_critical,
            "warning":              is_warning and not is_critical,
            "maintenance_required": is_maint_due and not is_critical and not is_warning,
            "risk_level":           risk_level
        }
