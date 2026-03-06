import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# How often (seconds) to check whether thresholds.json has changed on disk.
# Set to 0 to disable hot-reload (useful in unit tests).
_RELOAD_INTERVAL_SECONDS = int(os.getenv("THRESHOLDS_RELOAD_INTERVAL", "60"))


class AlertEngine:
    """
    Evaluates predictions and features to trigger alerts.

    Thresholds are loaded from the path specified by the THRESHOLDS_PATH
    environment variable (default: model/thresholds.json).  When the file is
    mounted as a Kubernetes ConfigMap the engine will hot-reload it within
    _RELOAD_INTERVAL_SECONDS seconds of any change — no pod restart needed.
    """

    def __init__(self, thresholds_path: str = "model/thresholds.json"):
        # Env var wins so the pipeline YAML's THRESHOLDS_PATH is honoured.
        self._path = Path(os.getenv("THRESHOLDS_PATH", thresholds_path))
        self._last_mtime: float = 0.0
        self._last_check: float = 0.0
        self.thresholds: Dict[str, Any] = {}
        self._reload()   # Initial load

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _reload(self) -> None:
        """Read thresholds from disk and re-compute boundary values."""
        if not self._path.exists():
            logger.warning("Thresholds file not found at %s — using defaults.", self._path)
            self.thresholds = {}
        else:
            try:
                with open(self._path, "r") as f:
                    self.thresholds = json.load(f)
                self._last_mtime = self._path.stat().st_mtime
                logger.info("[AlertEngine] Thresholds loaded from %s", self._path)
            except Exception as e:
                logger.error("[AlertEngine] Failed to load thresholds: %s", e)

        hs  = self.thresholds.get("health_score_thresholds", {})
        rul = self.thresholds.get("rul_thresholds", {})

        self.hs_critical   = float(hs.get("critical",              55.0))
        self.hs_warning    = float(hs.get("warning",               65.0))
        self.hs_maint_due  = float(hs.get("maintenance_due",       75.0))
        self.rul_critical  = float(rul.get("critical_days",        180))
        self.rul_warning   = float(rul.get("warning_days",         540))
        self.rul_maint_due = float(rul.get("maintenance_due_days", 1080))

    def _maybe_hot_reload(self) -> None:
        """
        Check file mtime at most once per _RELOAD_INTERVAL_SECONDS.
        Re-reads from disk only when the file has actually changed.
        Cost on the hot path when nothing changed: one time.time() call.
        """
        if _RELOAD_INTERVAL_SECONDS <= 0:
            return
        now = time.monotonic()
        if now - self._last_check < _RELOAD_INTERVAL_SECONDS:
            return
        self._last_check = now
        try:
            current_mtime = self._path.stat().st_mtime
            if current_mtime != self._last_mtime:
                logger.info("[AlertEngine] thresholds.json changed — hot-reloading.")
                self._reload()
        except Exception:
            pass   # File temporarily unavailable during a ConfigMap rotation

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate(self, health: float, rul: float) -> Dict[str, Any]:
        """
        Evaluate health score and RUL against config-driven thresholds.
        Thresholds are refreshed from disk if the file has changed since the
        last check (bounded by _RELOAD_INTERVAL_SECONDS).
        """
        self._maybe_hot_reload()

        is_critical  = (health < self.hs_critical)  or (rul < self.rul_critical)
        is_warning   = (health < self.hs_warning)   or (rul < self.rul_warning)
        is_maint_due = (health < self.hs_maint_due) or (rul < self.rul_maint_due)

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
            "warning":              is_warning   and not is_critical,
            "maintenance_required": is_maint_due and not is_critical and not is_warning,
            "risk_level":           risk_level,
        }
