from elasticsearch import Elasticsearch
import os
import json
from datetime import datetime, timezone
from app.config_loader import ConfigLoader

ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elasticsearch.elastic.svc.cluster.local:9200")
INDEX_NAME = "belt-runtime-state"

class StateManager:

    def __init__(self):
        self.client = Elasticsearch(ELASTIC_URL)
        self.config_loader = ConfigLoader()

    def get_state(self, belt_id):
        """
        Load belt runtime state from Elasticsearch.
        If missing → initialize smart state from metadata.
        """
        try:
            response = self.client.get(index=INDEX_NAME, id=str(belt_id))
            return response["_source"]
        except Exception:
            print(f"No existing state found for {belt_id}. Running smart initialization.")
            return self.initialize_state(belt_id)

    def initialize_state(self, belt_id):
        """
        Create state with realistic health based on installation date.
        """
        metadata = self.config_loader.load_belts_metadata()
        
        # Default starting values
        health_score = 100.0
        operating_hours = 0.0
        
        # Smart initialization logic
        # metadata format: {"belt_id": 1, "install_date": "2025-11-12", ...}
        # Note: In production metadata would likely be a list or dict keyed by ID.
        # Here we check if the single metadata matches or just use it as a template.
        metadata_id = metadata.get("belt_id")
        
        if str(metadata_id) == str(belt_id) or not metadata_id:
            install_date_str = metadata.get("install_date")
            if install_date_str:
                try:
                    install_date = datetime.fromisoformat(install_date_str).replace(tzinfo=timezone.utc)
                    days_since_install = (datetime.now(timezone.utc) - install_date).days
                    
                    # Estimate degradation: 1% per 10 days of aging (placeholder logic)
                    degradation = max(0, days_since_install / 10.0)
                    health_score = max(50.0, 100.0 - degradation)
                    operating_hours = float(days_since_install * 24.0) # Assume 24/7 for estimation
                    
                    print(f"Smart init for {belt_id}: Age={days_since_install} days, Estimated Health={health_score:.2f}")
                except Exception as e:
                    print(f"Error parsing install_date for {belt_id}: {e}")

        default_state = {
            "belt_id": belt_id,
            "model_version": "rf_v2.1",
            "last_prediction_timestamp": datetime.now(timezone.utc).isoformat(),
            "health_score": health_score,
            "derived_rul_days": health_score * 3.65, # Simplified projection
            "risk_level": "HEALTHY" if health_score > 90 else "MAINTENANCE_DUE",
            "degradation_budget": health_score / 100.0,
            "operating_hours": operating_hours,
            "rolling_state": {}
        }

        self.save_state(belt_id, default_state)
        return default_state

    def save_state(self, belt_id, updated_state):
        try:
            self.client.index(
                index=INDEX_NAME,
                id=str(belt_id),
                document=updated_state
            )
            print(f"State persisted for {belt_id}")
        except Exception as e:
            print(f"Error persisting state: {e}")
