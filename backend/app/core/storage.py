"""
NETRA Experiment Storage Engine
Persists and retrieves reproducible experiment metadata, configurations, metrics, and comparisons.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import settings

class ExperimentStorage:
    @classmethod
    def _read_data(cls) -> Dict[str, Any]:
        if not settings.EXPERIMENTS_FILE.exists():
            return {"experiments": []}
        try:
            with open(settings.EXPERIMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"experiments": []}

    @classmethod
    def _write_data(cls, data: Dict[str, Any]) -> None:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(settings.EXPERIMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def save_experiment(
        cls,
        name: str,
        network_config: Dict[str, Any],
        traffic_config: Dict[str, Any],
        results: Dict[str, Any],
        comparison: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Saves a completed simulation or optimization trial."""
        data = cls._read_data()
        exp_id = f"exp_{int(time.time() * 1000)}"

        record = {
            "id": exp_id,
            "name": name or f"Experiment {len(data['experiments']) + 1}",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "network_config": network_config,
            "traffic_config": traffic_config,
            "results": results,
            "comparison": comparison,
            "notes": notes,
            "status": "completed",
            "evaluation_version": 2
        }

        # Keep latest at head
        data["experiments"].insert(0, record)
        # Limit stored experiments to 100
        if len(data["experiments"]) > 100:
            data["experiments"] = data["experiments"][:100]

        cls._write_data(data)
        return record

    @classmethod
    def list_experiments(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns list of saved experiments sorted by newest first."""
        data = cls._read_data()
        return data.get("experiments", [])[:limit]

    @classmethod
    def get_experiment(cls, exp_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single experiment by its unique ID."""
        data = cls._read_data()
        for exp in data.get("experiments", []):
            if exp["id"] == exp_id:
                return exp
        return None

    @classmethod
    def delete_experiment(cls, exp_id: str) -> bool:
        """Removes an experiment by ID."""
        data = cls._read_data()
        initial_len = len(data.get("experiments", []))
        data["experiments"] = [e for e in data.get("experiments", []) if e["id"] != exp_id]
        if len(data["experiments"]) < initial_len:
            cls._write_data(data)
            return True
        return False
