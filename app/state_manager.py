from elasticsearch import Elasticsearch
import os
import json
from datetime import datetime

ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elasticsearch.elastic.svc.cluster.local:9200")
INDEX_NAME = "belt-runtime-state"

class StateManager:

    def __init__(self):
        self.client = Elasticsearch(ELASTIC_URL)

    def get_state(self, belt_id):
        """
        Load belt runtime state from Elasticsearch.
        If missing → initialize default state.
        """

        try:
            response = self.client.get(index=INDEX_NAME, id=belt_id)
            return response["_source"]

        except Exception:
            print(f"⚠ No existing state found for {belt_id}. Initializing default state.")
            return self.initialize_state(belt_id)

    def initialize_state(self, belt_id):
        """
        Create default commissioning state.
        """

        default_state = {
            "belt_id": belt_id,
            "model_version": "rf_v2.1",
            "last_prediction_timestamp": datetime.utcnow().isoformat(),
            "health_score": 100.0,
            "derived_rul_days": 365.0,
            "risk_level": "HEALTHY",
            "degradation_budget": 1.0,
            "operating_hours": 0.0,
            "rolling_state": {}
        }

        # Persist initial state
        self.save_state(belt_id, default_state)

        return default_state

    def save_state(self, belt_id, updated_state):
        """
        Overwrite belt runtime state deterministically.
        """

        self.client.index(
            index=INDEX_NAME,
            id=belt_id,
            document=updated_state
        )

        print(f"✅ State persisted for {belt_id}")
