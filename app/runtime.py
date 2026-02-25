# app/runtime.py

from datetime import datetime

from app.state_manager import StateManager
from app.feature_engineering import FeatureEngineer
from app.inference_engine import InferenceEngine


class MLRuntime:

    def __init__(self):
        self.state_manager = StateManager()
        self.feature_engineer = FeatureEngineer()
        self.engine = InferenceEngine()

    def process(self, raw_event):

        # -----------------------------
        # 1️⃣ Safe Field Extraction
        # -----------------------------
        belt_id = raw_event.get("belt_id")
        timestamp = raw_event.get("timestamp")

        if not belt_id:
            return {
                "status": "error",
                "reason": "Missing belt_id",
                "original_event": raw_event
            }

        if not timestamp:
            timestamp = datetime.utcnow().isoformat() + "Z"

        # -----------------------------
        # 2️⃣ Load State
        # -----------------------------
        state = self.state_manager.get_state(belt_id) or {}
        previous_rolling = state.get("rolling_state", {})

        # -----------------------------
        # 3️⃣ Update Rolling Features
        # -----------------------------
        updated_rolling = self.feature_engineer.update_rolling(
            raw_event,
            previous_rolling
        )

        # -----------------------------
        # 4️⃣ Predict
        # -----------------------------
        result = self.engine.predict(
            raw_event,
            updated_rolling,
            state
        )

        # -----------------------------
        # 5️⃣ Build Updated State
        # -----------------------------
        updated_state = {
            **state,
            "last_prediction_timestamp": timestamp,
            "health_score": result.get("health_score"),
            "derived_rul_days": result.get("rul_days"),
            "risk_level": result.get("risk_level"),
            "rolling_state": updated_rolling
        }

        # -----------------------------
        # 6️⃣ Persist State
        # -----------------------------
        self.state_manager.save_state(belt_id, updated_state)

        # -----------------------------
        # 7️⃣ Return Output Payload
        # -----------------------------
        return {
            "status": "success",
            "belt_id": belt_id,
            "timestamp": timestamp,
            **result
        }