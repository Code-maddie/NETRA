"""Paired conventional-routing comparison endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from app.core.traditional_routing import TraditionalRouter
from app.core.validator import NetworkValidator

router = APIRouter(prefix="/routing", tags=["Routing"])


class RoutingCompareRequest(BaseModel):
    topology_data: Dict[str, Any]
    source: int
    destination: int


@router.post("/compare")
def compare_routing_methods(req: RoutingCompareRequest):
    validation = NetworkValidator.validate_network_and_endpoints(
        req.topology_data, req.source, req.destination
    )
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

    algorithms = [
        "dijkstra_static",
        "dijkstra_dynamic",
        "least_loaded",
        "capacity_aware",
        "ecmp",
        "cadj",
    ]
    results = {}
    for algorithm in algorithms:
        results[algorithm] = TraditionalRouter.compute_route(
            req.topology_data["nodes"],
            req.topology_data["links"],
            req.source,
            req.destination,
            algorithm=algorithm,
        )
    return {"success": True, "source": req.source, "destination": req.destination, "results": results}
