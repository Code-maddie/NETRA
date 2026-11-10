"""
NETRA Experiment Management API
CRUD endpoints for inspecting historical runs, retrieving metrics, and cross-comparing experiments.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.storage import ExperimentStorage

router = APIRouter(prefix="/experiments", tags=["Experiments"])

class CompareRunsRequest(BaseModel):
    experiment_id_a: str
    experiment_id_b: str

@router.get("")
def api_list_experiments(limit: int = 50):
    """Lists saved experiments with metadata and summary metrics."""
    return {"experiments": ExperimentStorage.list_experiments(limit=limit)}

@router.get("/{exp_id}")
def api_get_experiment(exp_id: str):
    """Retrieves full telemetry, event stream, and metrics for a specific experiment."""
    exp = ExperimentStorage.get_experiment(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found.")
    return exp

@router.delete("/{exp_id}")
def api_delete_experiment(exp_id: str):
    """Deletes an experiment record from disk."""
    success = ExperimentStorage.delete_experiment(exp_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found.")
    return {"success": True, "deleted_id": exp_id}

@router.post("/compare")
def api_cross_compare_experiments(req: CompareRunsRequest):
    """Compares two historical experiments side-by-side."""
    exp_a = ExperimentStorage.get_experiment(req.experiment_id_a)
    exp_b = ExperimentStorage.get_experiment(req.experiment_id_b)

    if not exp_a or not exp_b:
        raise HTTPException(status_code=404, detail="One or both experiments could not be found.")

    return {
        "experiment_a": exp_a,
        "experiment_b": exp_b
    }
