import logging
import joblib
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

from .feature_engineering import FeatureEngineer
from .alert_engine import AlertEngine
from .config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class InferenceEngine:
    """
    Orchestrates the prediction flow: Feature Engineering → RF Inference → Alerting.
    """

    def __init__(self, model_dir: str = "model"):
        self.model_dir = Path(model_dir)
        self.config_loader = ConfigLoader(model_dir)

        # Load models
        self.health_bundle = self._load_bundle("belt_rul_model_health.pkl")
        self.rul_bundle    = self._load_bundle("belt_rul_model_rul.pkl")

        # Engines
        self.feature_engineer = FeatureEngineer()
        self.alert_engine     = AlertEngine(str(self.model_dir / "thresholds.json"))

    def _load_bundle(self, filename: str) -> Dict[str, Any]:
        path = self.model_dir / filename
        if not path.exists():
            print(f"⚠ Warning: Model file {filename} not found.")
            return {"model": None, "scaler": None, "features": []}
        return joblib.load(path)

    def predict(self, raw_event: Dict[str, Any], rolling_state: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the complete inference lifecycle.
        """
        # 1. Build ordered features
        health_features = self.health_bundle.get("features", [])
        X_health = self.feature_engineer.build_ordered_vector(
            raw_event, rolling_state, state, health_features
        )

        # 2. Predict Health Score
        health_score = self._run_model(
            self.health_bundle.get("model"),
            self.health_bundle.get("scaler"),
            X_health,
            default=state.get("health_score", 100.0)
        )

        # 3. Predict RUL
        rul_features = self.rul_bundle.get("features", [])
        X_rul = self.feature_engineer.build_ordered_vector(
            raw_event, rolling_state, state, rul_features
        )
        rul_days = self._run_model(
            self.rul_bundle.get("model"),
            self.rul_bundle.get("scaler"),
            X_rul,
            default=state.get("derived_rul_days", 2190.0)
        )

        # 4. Evaluate Alerts
        alerts = self.alert_engine.evaluate(health_score, rul_days)

        return {
            "health_score": round(health_score, 2),
            "rul_days":     round(rul_days, 1),
            "risk_level":   alerts["risk_level"],
            "alerts":       alerts
        }

    def _run_model(self, model, scaler, X, default: float) -> float:
        if model is None:
            return default
        try:
            if scaler:
                X = scaler.transform(X)
            return float(model.predict(X)[0])
        except Exception as e:
            print(f"Prediction Error: {e}")
            return default
