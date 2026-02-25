import json
import os
from pathlib import Path
from typing import Dict, Any

class ConfigLoader:
    def __init__(self, model_dir: str = "model"):
        self.model_dir = Path(model_dir)

    def load_thresholds(self) -> Dict[str, Any]:
        return self._load_json("thresholds.json")

    def load_model_config(self) -> Dict[str, Any]:
        return self._load_json("model_config.json")

    def load_belts_metadata(self) -> Dict[str, Any]:
        return self._load_json("belts_metadata.json")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = self.model_dir / filename
        if not path.exists():
            print(f"⚠ Warning: Config file {filename} not found in {self.model_dir}")
            return {}
        with open(path, "r") as f:
            return json.load(f)
