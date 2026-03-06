from elasticsearch import Elasticsearch, ConflictError
import os
import json
import time
from datetime import datetime, timezone
from app.config_loader import ConfigLoader

ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elasticsearch.elastic.svc.cluster.local:9200")
INDEX_NAME = os.getenv("STATE_INDEX_NAME", "belt-runtime-state")

# Max attempts when an optimistic-concurrency conflict is detected
_MAX_SAVE_RETRIES = 3


class StateManager:

    def __init__(self):
        self.client = Elasticsearch(ELASTIC_URL)
        self.config_loader = ConfigLoader()
        # Per-instance cache of the last seq_no / primary_term we read for each belt.
        # This lets save_state() pass the version tokens back to ES so it can
        # reject writes that would silently overwrite another pod's update.
        self._version_cache: dict = {}

    def get_state(self, belt_id: str) -> dict:
        """
        Load belt runtime state from Elasticsearch.
        Also caches the document version tokens (_seq_no / _primary_term) that
        are required for optimistic-concurrency writes in save_state().
        If not found → initialise from metadata.
        """
        try:
            response = self.client.get(index=INDEX_NAME, id=str(belt_id))
            # Cache version info for the subsequent save_state() call
            self._version_cache[str(belt_id)] = {
                "seq_no":       response["_seq_no"],
                "primary_term": response["_primary_term"],
            }
            return response["_source"]
        except Exception:
            print(f"[StateManager] No existing state for {belt_id}. Initialising.")
            self._version_cache.pop(str(belt_id), None)
            return self.initialize_state(belt_id)

    def initialize_state(self, belt_id) -> dict:
        """
        Create initial state with realistic health based on installation date.
        """
        metadata = self.config_loader.load_belts_metadata()

        health_score = 100.0
        operating_hours = 0.0

        metadata_id = metadata.get("belt_id")
        if str(metadata_id) == str(belt_id) or not metadata_id:
            install_date_str = metadata.get("install_date")
            if install_date_str:
                try:
                    install_date = datetime.fromisoformat(install_date_str).replace(tzinfo=timezone.utc)
                    days_since_install = (datetime.now(timezone.utc) - install_date).days
                    degradation = max(0, days_since_install / 10.0)
                    health_score = max(50.0, 100.0 - degradation)
                    operating_hours = float(days_since_install * 24.0)
                    print(f"[StateManager] Smart init for {belt_id}: age={days_since_install}d, health={health_score:.2f}")
                except Exception as e:
                    print(f"[StateManager] Error parsing install_date for {belt_id}: {e}")

        default_state = {
            "belt_id":                    belt_id,
            "model_version":              "rf_v2.1",
            "last_prediction_timestamp":  datetime.now(timezone.utc).isoformat(),
            "health_score":               health_score,
            "derived_rul_days":           health_score * 3.65,
            "risk_level":                 "HEALTHY" if health_score > 90 else "MAINTENANCE_DUE",
            "degradation_budget":         health_score / 100.0,
            "operating_hours":            operating_hours,
            "rolling_state":              {},
        }

        self.save_state(belt_id, default_state)
        return default_state

    def save_state(self, belt_id, updated_state: dict, _retry: int = 0) -> None:
        """
        Persist belt state to Elasticsearch using optimistic concurrency control.

        If we have a cached _seq_no / _primary_term from the last get_state() call,
        we pass them to ES.  If another pod has written a newer version in the
        meantime, ES responds with HTTP 409 (ConflictError).  We then re-fetch
        fresh state, merge only the rolling_state we computed, and retry — up to
        _MAX_SAVE_RETRIES times.
        """
        bid = str(belt_id)
        version = self._version_cache.get(bid)

        try:
            index_kwargs: dict = {
                "index":    INDEX_NAME,
                "id":       bid,
                "document": updated_state,
            }
            if version:
                index_kwargs["if_seq_no"]       = version["seq_no"]
                index_kwargs["if_primary_term"]  = version["primary_term"]

            resp = self.client.index(**index_kwargs)

            # Update the cached version tokens so the next save in this pod
            # uses the newly written sequence number.
            self._version_cache[bid] = {
                "seq_no":       resp["_seq_no"],
                "primary_term": resp["_primary_term"],
            }
            print(f"[StateManager] State persisted for {bid} (seq_no={resp['_seq_no']})")

        except ConflictError:
            # Another pod wrote a newer version; our tokens are stale.
            if _retry >= _MAX_SAVE_RETRIES:
                print(f"[StateManager] ⚠ Gave up saving state for {bid} after {_retry} conflict retries.")
                return

            print(f"[StateManager] Conflict on {bid} — re-fetching state and retrying ({_retry + 1}/{_MAX_SAVE_RETRIES})")
            time.sleep(0.05 * (2 ** _retry))          # tiny exponential back-off

            # Re-read the winning state, keep the rolling_state we computed.
            fresh_state = self.get_state(bid)
            merged = {**fresh_state, "rolling_state": updated_state.get("rolling_state", {})}
            self.save_state(bid, merged, _retry=_retry + 1)

        except Exception as e:
            print(f"[StateManager] Error persisting state for {bid}: {e}")
